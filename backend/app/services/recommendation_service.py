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
        logger.info(
            "Models initialized",
            cf_loaded=self.cf_model.is_loaded,
            content_loaded=self.content_model.is_loaded,
            trending_loaded=self.trending_model.is_loaded,
        )

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

        cache_key = f"{user_id}:{session_id}:{num_recommendations}:{algorithm}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        exclude_ids = set()
        liked_movies = []

        if user_id and exclude_seen:
            exclude_ids = await self._get_user_history(db, user_id)
            liked_movies = await self._get_liked_movies(db, user_id)

        if algorithm == "collaborative":
            raw_recs = self.cf_model.predict(user_id or "", top_k=num_recommendations * 3)
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
        elif algorithm == "content_based":
            raw_recs = self.content_model.predict_from_history(
                liked_movies, top_k=num_recommendations * 3
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
        elif algorithm == "trending":
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
            raw_recs = self.hybrid.predict_with_explanations(
                user_id=user_id,
                liked_movies=liked_movies,
                top_k=num_recommendations,
                exclude_ids=exclude_ids,
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

        latency_ms = (time.time() - start_time) * 1000

        response = RecommendationResponse(
            user_id=user_id,
            session_id=session_id,
            recommendations=items,
            algorithm_used=algo_used,
            latency_ms=round(latency_ms, 2),
        )

        self._set_cache(cache_key, response)

        await self._log_recommendation(db, user_id, session_id, items, latency_ms, algo_used)

        return response

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

        cache_key = f"{user_id}:*"
        self._invalidate_cache_pattern(user_id)

    async def get_user_profile(self, db: AsyncSession, user_id: str) -> dict:
        """Build user preference profile from interaction history."""
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

        return {
            "user_id": user_id,
            "total_ratings": len(ratings),
            "avg_rating": sum(r.rating for r in ratings) / len(ratings) if ratings else 0,
            "genre_preferences": dict(sorted(genre_preferences.items(), key=lambda x: x[1], reverse=True)[:10]),
            "recent_movies": [r.movie_id for r in ratings[:20]],
        }

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

        result = await db.execute(select(Movie).where(Movie.id == movie_id))
        movie = result.scalar_one_or_none()
        if movie:
            return MovieResponse.model_validate(movie)
        return None

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

    def _get_from_cache(self, key: str) -> RecommendationResponse | None:
        """Get recommendation from in-memory cache."""
        if key in self._cache:
            cached_time, data = self._cache[key]
            if time.time() - cached_time < settings.REDIS_CACHE_TTL:
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
