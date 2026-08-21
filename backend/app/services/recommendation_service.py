from __future__ import annotations

import json
import time

import structlog
from ml.models import (
    CollaborativeFilteringModel,
    ContentBasedModel,
    HybridEnsemble,
    TrendingModel,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Movie, Rating, RecommendationLog, UserInteraction
from app.schemas.recommendation import (
    RecommendationItem,
    RecommendationResponse,
)

logger = structlog.get_logger("services.recommendation")
settings = get_settings()


class RecommendationService:
    """Core recommendation service implementing the two-stage pipeline.

    Stage 1: Candidate Generation - Fast retrieval of ~500 candidates
    Stage 2: Ranking - Precise scoring and re-ranking of candidates

    Uses late fusion hybrid ensemble combining collaborative filtering,
    content-based filtering, and trending signals.
    """

    def __init__(self):
        self.cf_model = CollaborativeFilteringModel()
        self.content_model = ContentBasedModel()
        self.trending_model = TrendingModel()
        self.hybrid = HybridEnsemble(self.cf_model, self.content_model, self.trending_model)
        self._cache: dict[str, tuple[float, list]] = {}

        # Wire in advanced infrastructure (Category A)
        self._multi_level_cache = None
        self._feature_store = None
        self._session_recommender = None
        self._bandit = None
        self._streaming_pipeline = None
        self._model_monitor = None
        self._ltr_model = None
        self._cb_cf = None
        self._cb_content = None
        self._cb_hybrid = None

    async def initialize(self, db: AsyncSession) -> None:
        """Load or train all models."""
        logger.info("Initializing recommendation models")

        loaded_cf = self.cf_model.load()
        loaded_content = self.content_model.load()

        if not loaded_cf:
            logger.info("Training collaborative filtering model")
            await self.cf_model.train(db)

        if not loaded_content:
            logger.info("Building content-based index")
            await self.content_model.build_index(db)

        await self.trending_model.compute_trending(db)

        # Wire in advanced infrastructure
        self._wire_infrastructure()
        self._wire_circuit_breakers()

        logger.info(
            "Models initialized",
            cf_loaded=self.cf_model.is_loaded,
            content_loaded=self.content_model.is_loaded,
            trending_loaded=self.trending_model.is_loaded,
            cache_wired=self._multi_level_cache is not None,
            feature_store_wired=self._feature_store is not None,
            bandit_wired=self._bandit is not None,
            streaming_wired=self._streaming_pipeline is not None,
            monitoring_wired=self._model_monitor is not None,
        )

    def _wire_infrastructure(self) -> None:
        """Wire in advanced infrastructure modules."""
        try:
            from app.serving.cache.multi_level import recommendation_cache, feature_cache
            self._multi_level_cache = recommendation_cache
            self._feature_cache = feature_cache
            logger.info("Multi-level cache wired")
        except Exception as e:
            logger.warning("Failed to wire cache", error=str(e))

        try:
            from app.features.store.online_store import feature_store
            self._feature_store = feature_store
            logger.info("Feature store wired")
        except Exception as e:
            logger.warning("Failed to wire feature store", error=str(e))

        try:
            from ml.models.session_based import get_session_recommender
            self._session_recommender = get_session_recommender()
            logger.info("Session recommender wired")
        except Exception as e:
            logger.warning("Failed to wire session recommender", error=str(e))

        try:
            from ml.models.mab import get_recommendation_bandit
            self._bandit = get_recommendation_bandit()
            logger.info("Multi-armed bandit wired")
        except Exception as e:
            logger.warning("Failed to wire bandit", error=str(e))

        try:
            from app.serving.streaming.pipeline import streaming_pipeline
            self._streaming_pipeline = streaming_pipeline
            logger.info("Streaming pipeline wired")
        except Exception as e:
            logger.warning("Failed to wire streaming pipeline", error=str(e))

        try:
            from app.core.monitoring import get_model_monitor
            self._model_monitor = get_model_monitor()
            logger.info("Model monitor wired")
        except Exception as e:
            logger.warning("Failed to wire model monitor", error=str(e))

        try:
            from ml.models.ltr_ranker import LearningToRankModel
            self._ltr_model = LearningToRankModel()
            if self._ltr_model.load():
                logger.info("LTR ranker loaded from disk")
            else:
                logger.info("LTR ranker initialized (not trained yet)")
        except Exception as e:
            logger.warning("Failed to wire LTR ranker", error=str(e))

    def _wire_circuit_breakers(self) -> None:
        """Wire circuit breakers for critical operations."""
        try:
            from app.serving.circuit_breaker import circuit_breaker_registry
            self._cb_cf = circuit_breaker_registry.get_or_create(
                "collaborative_filtering",
                failure_threshold=5,
                recovery_timeout=60,
            )
            self._cb_content = circuit_breaker_registry.get_or_create(
                "content_based",
                failure_threshold=5,
                recovery_timeout=60,
            )
            self._cb_hybrid = circuit_breaker_registry.get_or_create(
                "hybrid_ensemble",
                failure_threshold=3,
                recovery_timeout=30,
            )
            logger.info("Circuit breakers wired for all models")
        except Exception as e:
            logger.warning("Failed to wire circuit breakers", error=str(e))
            self._cb_cf = None
            self._cb_content = None
            self._cb_hybrid = None

    async def get_recommendations(
        self,
        db: AsyncSession,
        user_id: str | None = None,
        session_id: str | None = None,
        num_recommendations: int = 10,
        algorithm: str | None = None,
        exclude_seen: bool = True,
    ) -> RecommendationResponse:
        """Generate personalized recommendations."""
        start_time = time.time()

        # Check multi-level cache first
        cache_key = f"recommendations:{user_id}:{session_id}:{num_recommendations}:{algorithm}"
        cached = self._get_from_multi_level_cache(cache_key)
        if cached:
            return cached

        # Fallback to in-memory cache
        cache_key_simple = f"{user_id}:{session_id}:{num_recommendations}:{algorithm}"
        cached = self._get_from_cache(cache_key_simple)
        if cached:
            return cached

        exclude_ids = set()
        liked_movies = []

        if user_id and exclude_seen:
            exclude_ids = await self._get_user_history(db, user_id)
            liked_movies = await self._get_liked_movies(db, user_id)

        # Use bandit to potentially select algorithm if none specified
        selected_algorithm = algorithm
        if not selected_algorithm and self._bandit and user_id:
            try:
                selected_algorithm = self._bandit.select_strategy()
                if selected_algorithm not in ("collaborative", "content_based", "trending", "hybrid"):
                    selected_algorithm = None
            except Exception:
                pass

        if selected_algorithm == "collaborative":
            raw_recs = self._call_with_circuit_breaker(
                self._cb_cf,
                lambda: self.cf_model.predict(user_id or "", top_k=num_recommendations * 3),
                fallback=[],
            )
            items = [
                RecommendationItem(
                    movie=await self._get_movie_info(db, mid),
                    score=min(s, 1.0),
                    algorithm="collaborative",
                    explanation="Users with similar taste enjoyed this",
                    confidence=min(s * 1.2, 1.0),
                )
                for mid, s in raw_recs
                if mid not in exclude_ids
            ][:num_recommendations]
            algo_used = "collaborative"
        elif selected_algorithm == "content_based":
            raw_recs = self._call_with_circuit_breaker(
                self._cb_content,
                lambda: self.content_model.predict_from_history(
                    liked_movies, top_k=num_recommendations * 3
                ),
                fallback=[],
            )
            items = [
                RecommendationItem(
                    movie=await self._get_movie_info(db, mid),
                    score=min(s, 1.0),
                    algorithm="content_based",
                    explanation="Matches your preferred genres and themes",
                    confidence=min(s * 1.1, 1.0),
                )
                for mid, s in raw_recs
                if mid not in exclude_ids
            ][:num_recommendations]
            algo_used = "content_based"
        elif selected_algorithm == "trending":
            raw_recs = self.trending_model.predict(top_k=num_recommendations * 2)
            items = [
                RecommendationItem(
                    movie=await self._get_movie_info(db, mid),
                    score=min(s, 1.0),
                    algorithm="trending",
                    explanation="Currently trending in the community",
                    confidence=min(s * 0.9, 1.0),
                )
                for mid, s in raw_recs
                if mid not in exclude_ids
            ][:num_recommendations]
            algo_used = "trending"
        else:
            raw_recs = self._call_with_circuit_breaker(
                self._cb_hybrid,
                lambda: self.hybrid.predict_with_explanations(
                    user_id=user_id,
                    liked_movies=liked_movies,
                    top_k=num_recommendations,
                    exclude_ids=exclude_ids,
                ),
                fallback=[],
            )
            items = []
            for rec in raw_recs:
                movie = await self._get_movie_info(db, rec["movie_id"])
                if movie:
                    items.append(
                        RecommendationItem(
                            movie=movie,
                            score=rec["score"],
                            algorithm=rec["algorithm"],
                            explanation=rec["explanation"],
                            confidence=rec["confidence"],
                        )
                    )
            algo_used = "hybrid"

        # Re-rank with LTR if available
        if self._ltr_model and self._ltr_model.is_trained and len(items) > 5:
            try:
                items = self._rerank_with_ltr(items, user_id)
            except Exception as e:
                logger.warning("LTR reranking failed, using original order", error=str(e))

        latency_ms = (time.time() - start_time) * 1000

        response = RecommendationResponse(
            user_id=user_id,
            session_id=session_id,
            recommendations=items,
            algorithm_used=algo_used,
            latency_ms=round(latency_ms, 2),
        )

        # Cache in both layers
        self._set_in_multi_level_cache(cache_key, response)
        self._set_cache(cache_key_simple, response)

        await self._log_recommendation(db, user_id, session_id, items, latency_ms, algo_used)

        # Record prediction for monitoring
        if self._model_monitor and items:
            try:
                import numpy as np
                avg_score = np.mean([i.score for i in items])
                self._model_monitor.record_prediction(
                    float(avg_score),
                    {"algorithm": algo_used, "num_items": len(items)},
                )
            except Exception:
                pass

        # Record Prometheus metrics
        try:
            from app.middleware.monitoring import RECOMMENDATION_LATENCY, RECOMMENDATION_COUNT
            RECOMMENDATION_LATENCY.labels(algorithm=algo_used).observe(latency_ms / 1000)
            RECOMMENDATION_COUNT.labels(algorithm=algo_used).inc()
        except Exception:
            pass

        return response

    def _rerank_with_ltr(
        self, items: list[RecommendationItem], user_id: str | None
    ) -> list[RecommendationItem]:
        """Re-rank items using the Learning-to-Rank model."""
        if not self._ltr_model or not self._ltr_model.is_trained:
            return items

        candidates = []
        for item in items:
            candidates.append({
                "item_id": item.movie.id,
                "item_features": {
                    "rating": item.movie.vote_average or 0,
                    "popularity": item.movie.popularity or 0,
                    "year": item.movie.year or 2000,
                    "vote_count": item.movie.vote_count or 0,
                },
                "original_score": item.score,
            })

        user_features = {
            "user_id_hash": hash(user_id or "anonymous") % 1000 / 1000,
            "num_candidates": len(candidates),
        }

        ranked = self._ltr_model.rank_candidates(candidates, user_features)

        # Merge LTR scores with original scores
        ltr_scores = {item_id: score for item_id, score in ranked}
        for item in items:
            if item.movie.id in ltr_scores:
                # Blend LTR score with original score
                ltr_score = ltr_scores[item.movie.id]
                item.score = min(0.7 * ltr_score + 0.3 * item.score, 1.0)
                item.confidence = min(item.confidence * 1.1, 1.0)

        items.sort(key=lambda x: x.score, reverse=True)
        return items

    async def get_similar_items(
        self, db: AsyncSession, movie_id: int, top_k: int = 10
    ) -> list[dict]:
        """Get items similar to a given movie."""
        results = []

        if self.cf_model.is_loaded:
            cf_similar = self.cf_model.similar_items(str(movie_id), top_k=top_k)
            for mid, score in cf_similar:
                movie = await self._get_movie_info(db, mid)
                if movie:
                    results.append(
                        {
                            "movie": movie,
                            "score": score,
                            "algorithm": "collaborative",
                            "explanation": "Similar users also enjoyed this",
                        }
                    )

        if self.content_model.is_loaded:
            cb_similar = self.content_model.similar_items(movie_id, top_k=top_k)
            for mid, score in cb_similar:
                if not any(r["movie"].id == mid for r in results):
                    movie = await self._get_movie_info(db, mid)
                    if movie:
                        results.append(
                            {
                                "movie": movie,
                                "score": score,
                                "algorithm": "content_based",
                                "explanation": "Similar content and themes",
                            }
                        )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    async def record_interaction(
        self,
        db: AsyncSession,
        user_id: str,
        movie_id: int,
        interaction_type: str,
        intensity: float = 1.0,
    ) -> None:
        """Record a user interaction for real-time personalization."""
        interaction = UserInteraction(
            user_id=user_id,
            movie_id=movie_id,
            interaction_type=interaction_type,
            intensity=intensity,
        )
        db.add(interaction)
        await db.flush()

        # Update feature store
        if self._feature_store:
            try:
                # Get user's rating history for feature computation
                result = await db.execute(
                    select(Rating).where(Rating.user_id == user_id)
                )
                ratings = result.scalars().all()
                rating_dicts = []
                for r in ratings:
                    movie_result = await db.execute(select(Movie).where(Movie.id == r.movie_id))
                    movie = movie_result.scalar_one_or_none()
                    rating_dicts.append({
                        "rating": r.rating,
                        "genres": movie.genres if movie else "",
                    })
                features = self._feature_store.compute_user_features_from_history(
                    user_id, rating_dicts
                )
                self._feature_store.set_user_features(user_id, features)
            except Exception as e:
                logger.warning("Failed to update feature store", error=str(e))

        # Publish to streaming pipeline
        if self._streaming_pipeline:
            try:
                import asyncio
                asyncio.create_task(
                    self._streaming_pipeline.publish_interaction(
                        user_id, movie_id, interaction_type, intensity
                    )
                )
            except Exception:
                pass

        # Update bandit with implicit reward
        if self._bandit:
            try:
                reward = intensity if interaction_type in ("like", "bookmark", "share") else 0.5
                self._bandit.update("hybrid", reward)
            except Exception:
                pass

        # Update session recommender
        if self._session_recommender:
            try:
                self._session_recommender.update_session(user_id, movie_id)
            except Exception:
                pass

        self._invalidate_cache_pattern(user_id)

    async def get_user_profile(self, db: AsyncSession, user_id: str) -> dict:
        """Build user preference profile from interaction history."""
        # Check feature store first
        if self._feature_store:
            try:
                fs_features = self._feature_store.get_user_features(user_id)
                if fs_features and fs_features.get("rating_count", 0) > 0:
                    return {
                        "user_id": user_id,
                        "total_ratings": fs_features.get("rating_count", 0),
                        "avg_rating": fs_features.get("avg_rating", 0),
                        "genre_preferences": fs_features.get("favorite_genres", {}),
                        "recent_movies": [],
                        "segment": fs_features.get("segment", "unknown"),
                        "engagement_score": fs_features.get("engagement_score", 0),
                    }
            except Exception:
                pass

        ratings_result = await db.execute(
            select(Rating).where(Rating.user_id == user_id).order_by(Rating.timestamp.desc())
        )
        ratings = ratings_result.scalars().all()

        genre_preferences: dict[str, float] = {}
        for r in ratings:
            movie_result = await db.execute(select(Movie).where(Movie.id == r.movie_id))
            movie = movie_result.scalar_one_or_none()
            if movie and movie.genres:
                for genre in movie.genres.split("|"):
                    genre_preferences[genre] = genre_preferences.get(genre, 0) + r.rating

        total = sum(genre_preferences.values()) or 1
        genre_preferences = {k: v / total for k, v in genre_preferences.items()}

        profile = {
            "user_id": user_id,
            "total_ratings": len(ratings),
            "avg_rating": sum(r.rating for r in ratings) / len(ratings) if ratings else 0,
            "genre_preferences": dict(sorted(genre_preferences.items(), key=lambda x: x[1], reverse=True)[:10]),
            "recent_movies": [r.movie_id for r in ratings[:20]],
        }

        # Update feature store with computed features
        if self._feature_store and ratings:
            try:
                rating_dicts = []
                for r in ratings:
                    movie_result = await db.execute(select(Movie).where(Movie.id == r.movie_id))
                    movie = movie_result.scalar_one_or_none()
                    rating_dicts.append({
                        "rating": r.rating,
                        "genres": movie.genres if movie else "",
                    })
                features = self._feature_store.compute_user_features_from_history(
                    user_id, rating_dicts
                )
                self._feature_store.set_user_features(user_id, features)
                profile["segment"] = features.get("segment", "unknown")
                profile["engagement_score"] = features.get("engagement_score", 0)
            except Exception:
                pass

        return profile

    async def record_rating(
        self,
        db: AsyncSession,
        user_id: str,
        movie_id: int,
        rating: float,
    ) -> None:
        """Record a user rating and update all connected systems."""
        # Record in database
        existing = await db.execute(
            select(Rating).where(Rating.user_id == user_id, Rating.movie_id == movie_id)
        )
        existing_rating = existing.scalar_one_or_none()

        if existing_rating:
            existing_rating.rating = rating
        else:
            new_rating = Rating(user_id=user_id, movie_id=movie_id, rating=rating)
            db.add(new_rating)

        await db.flush()

        # Update feature store
        if self._feature_store:
            try:
                result = await db.execute(
                    select(Rating).where(Rating.user_id == user_id)
                )
                all_ratings = result.scalars().all()
                rating_dicts = []
                for r in all_ratings:
                    movie_result = await db.execute(select(Movie).where(Movie.id == r.movie_id))
                    movie = movie_result.scalar_one_or_none()
                    rating_dicts.append({
                        "rating": r.rating,
                        "genres": movie.genres if movie else "",
                    })
                features = self._feature_store.compute_user_features_from_history(
                    user_id, rating_dicts
                )
                self._feature_store.set_user_features(user_id, features)
            except Exception:
                pass

        # Publish to streaming
        if self._streaming_pipeline:
            try:
                import asyncio
                asyncio.create_task(
                    self._streaming_pipeline.publish_rating(user_id, movie_id, rating)
                )
            except Exception:
                pass

        # Update bandit
        if self._bandit:
            try:
                reward = rating / 5.0  # Normalize to [0, 1]
                self._bandit.update("hybrid", reward)
            except Exception:
                pass

        # Invalidate cache
        self._invalidate_cache_pattern(user_id)

    async def get_trending(self, db: AsyncSession, period: str = "30d", top_k: int = 20) -> list[dict]:
        """Get trending movies with additional metadata."""
        raw_recs = self.trending_model.predict(top_k=top_k)
        results = []
        for movie_id, score in raw_recs:
            movie = await self._get_movie_info(db, movie_id)
            if movie:
                results.append({
                    "movie": movie,
                    "score": score,
                    "algorithm": "trending",
                    "explanation": f"Trending in the last {period}",
                })
        return results

    async def get_debug_status(self, db: AsyncSession) -> dict:
        """Get comprehensive debug status of all systems."""
        status = {
            "models": {
                "collaborative_filtering": self.cf_model.is_loaded,
                "content_based": self.content_model.is_loaded,
                "trending": self.trending_model.is_loaded,
                "hybrid_ensemble": self.hybrid.is_loaded,
                "ltr_ranker": self._ltr_model.is_trained if self._ltr_model else False,
            },
            "infrastructure": {
                "multi_level_cache": self._multi_level_cache is not None,
                "feature_store": self._feature_store is not None,
                "session_recommender": self._session_recommender is not None,
                "bandit": self._bandit is not None,
                "streaming_pipeline": self._streaming_pipeline is not None,
                "model_monitor": self._model_monitor is not None,
            },
            "config": {
                "candidate_pool_size": settings.CANDIDATE_POOL_SIZE,
                "ranking_top_k": settings.RANKING_TOP_K,
                "embedding_model": settings.EMBEDDING_MODEL,
            },
        }

        # Add cache stats
        if self._multi_level_cache:
            try:
                status["cache_stats"] = self._multi_level_cache.stats
            except Exception:
                pass

        # Add feature store stats
        if self._feature_store:
            try:
                status["feature_store_stats"] = self._feature_store.stats
            except Exception:
                pass

        # Add bandit stats
        if self._bandit:
            try:
                status["bandit_stats"] = self._bandit.get_strategy_stats()
            except Exception:
                pass

        # Add streaming stats
        if self._streaming_pipeline:
            try:
                status["streaming_stats"] = self._streaming_pipeline.stats
            except Exception:
                pass

        # Add monitoring report
        if self._model_monitor:
            try:
                status["monitoring_report"] = self._model_monitor.generate_report()
            except Exception:
                pass

        # Add circuit breaker stats
        try:
            from app.serving.circuit_breaker import circuit_breaker_registry
            status["circuit_breakers"] = circuit_breaker_registry.get_all_stats()
        except Exception:
            pass

        return status

    def _call_with_circuit_breaker(self, cb, func, fallback):
        """Call a function with circuit breaker protection."""
        if cb is None:
            try:
                return func()
            except Exception:
                return fallback
        try:
            return cb.call(func, fallback=fallback)
        except Exception:
            return fallback

    def _get_from_multi_level_cache(self, key: str) -> RecommendationResponse | None:
        """Get recommendation from multi-level cache."""
        if not self._multi_level_cache:
            return None
        try:
            cached = self._multi_level_cache.get(key)
            if cached and isinstance(cached, RecommendationResponse):
                # Record cache hit
                try:
                    from app.middleware.monitoring import CACHE_HITS
                    CACHE_HITS.labels(level="l1_l2").inc()
                except Exception:
                    pass
                return cached
        except Exception:
            pass
        return None

    def _set_in_multi_level_cache(self, key: str, data: RecommendationResponse) -> None:
        """Set recommendation in multi-level cache."""
        if not self._multi_level_cache:
            return
        try:
            self._multi_level_cache.set(key, data, level=2)
        except Exception:
            pass

    async def _log_recommendation(
        self,
        db: AsyncSession,
        user_id: str | None,
        session_id: str | None,
        items: list[RecommendationItem],
        latency_ms: float,
        algorithm: str,
    ) -> None:
        """Log recommendation for monitoring and A/B test analysis."""
        log = RecommendationLog(
            user_id=user_id,
            session_id=session_id,
            algorithm=algorithm,
            recommended_movie_ids=json.dumps([i.movie.id for i in items]),
            latency_ms=latency_ms,
        )
        db.add(log)

    async def _get_user_history(self, db: AsyncSession, user_id: str) -> set[int]:
        """Get set of movie IDs the user has already interacted with."""
        result = await db.execute(select(Rating.movie_id).where(Rating.user_id == user_id))
        return set(result.scalars().all())

    async def _get_liked_movies(self, db: AsyncSession, user_id: str) -> list[int]:
        """Get movie IDs with high ratings (>= 3.5)."""
        result = await db.execute(
            select(Rating.movie_id)
            .where(Rating.user_id == user_id, Rating.rating >= 3.5)
            .order_by(Rating.rating.desc())
        )
        return list(result.scalars().all())

    async def _get_movie_info(self, db: AsyncSession, movie_id: int):
        """Get movie schema from database."""
        from app.schemas.recommendation import MovieResponse

        # Check feature cache
        if self._feature_cache:
            try:
                cached = self._feature_cache.get(f"movie:{movie_id}")
                if cached:
                    return cached
            except Exception:
                pass

        result = await db.execute(select(Movie).where(Movie.id == movie_id))
        movie = result.scalar_one_or_none()
        if movie:
            response = MovieResponse.model_validate(movie)
            # Cache in feature store
            if self._feature_cache:
                try:
                    self._feature_cache.set(f"movie:{movie_id}", response)
                except Exception:
                    pass
            return response
        return None

    def _get_from_cache(self, key: str) -> RecommendationResponse | None:
        """Get recommendation from in-memory cache."""
        if key in self._cache:
            cached_time, data = self._cache[key]
            if time.time() - cached_time < settings.REDIS_CACHE_TTL:
                try:
                    from app.middleware.monitoring import CACHE_HITS
                    CACHE_HITS.labels(level="memory").inc()
                except Exception:
                    pass
                return data
            del self._cache[key]
        return None

    def _set_cache(self, key: str, data: RecommendationResponse) -> None:
        """Set recommendation in in-memory cache."""
        self._cache[key] = (time.time(), data)
        if len(self._cache) > 10000:
            oldest_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][0])[:1000]
            for k in oldest_keys:
                del self._cache[k]

    def _invalidate_cache_pattern(self, user_id: str) -> None:
        """Invalidate cache entries for a user."""
        keys_to_delete = [k for k in self._cache if k.startswith(f"{user_id}:")]
        for k in keys_to_delete:
            del self._cache[k]

        # Also invalidate multi-level cache
        if self._multi_level_cache:
            try:
                self._multi_level_cache.invalidate_user(user_id)
            except Exception:
                pass
