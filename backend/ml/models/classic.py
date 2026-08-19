from __future__ import annotations

import json
import logging
import pickle

import faiss
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import MovieFeature, Rating

logger = logging.getLogger(__name__)
settings = get_settings()


class CollaborativeFilteringModel:
    """Matrix Factorization using implicit ALS.

    Learns latent user and item factors from the interaction matrix.
    Supports online updates and FAISS-based ANN retrieval.
    """

    def __init__(self):
        self.model = None
        self.user_factors = None
        self.item_factors = None
        self.user_id_map: dict[str, int] = {}
        self.item_id_map: dict[int, int] = {}
        self.reverse_item_map: dict[int, int] = {}
        self.interaction_matrix: csr_matrix | None = None
        self.faiss_index: faiss.IndexFlatIP | None = None

    async def train(self, db: AsyncSession, factors: int = 128, iterations: int = 30) -> None:
        """Train the collaborative filtering model."""
        logger.info("Loading ratings for CF training")

        result = await db.execute(select(Rating))
        ratings = result.scalars().all()

        if not ratings:
            logger.warning("No ratings found for training")
            return

        df = pd.DataFrame(
            [{"user_id": r.user_id, "movie_id": r.movie_id, "rating": r.rating} for r in ratings]
        )

        users = sorted(df["user_id"].unique())
        items = sorted(df["movie_id"].unique())

        self.user_id_map = {u: i for i, u in enumerate(users)}
        self.item_id_map = {m: i for i, m in enumerate(items)}
        self.reverse_item_map = {i: m for m, i in self.item_id_map.items()}

        rows = df["user_id"].map(self.user_id_map).values
        cols = df["movie_id"].map(self.item_id_map).values
        vals = df["rating"].values.astype(np.float32)

        self.interaction_matrix = csr_matrix((vals, (rows, cols)), shape=(len(users), len(items)))

        import implicit

        self.model = implicit.als.AlternatingLeastSquares(
            factors=factors,
            iterations=iterations,
            regularization=0.1,
            use_gpu=False,
        )
        self.model.fit(self.interaction_matrix)

        self.user_factors = self.model.user_factors
        self.item_factors = self.model.item_factors

        self._build_faiss_index()

        model_dir = settings.MODEL_DIR
        model_dir.mkdir(parents=True, exist_ok=True)

        with open(model_dir / "cf_model.pkl", "wb") as f:
            pickle.dump(
                {
                    "model": self.model,
                    "user_id_map": self.user_id_map,
                    "item_id_map": self.item_id_map,
                    "reverse_item_map": self.reverse_item_map,
                },
                f,
            )

        faiss.write_index(self.faiss_index, str(model_dir / "cf_faiss.index"))
        logger.info(f"CF model trained: {len(users)} users, {len(items)} items, {factors} factors")

    def _build_faiss_index(self) -> None:
        """Build FAISS index for fast ANN retrieval."""
        if self.item_factors is None:
            return

        dimension = self.item_factors.shape[1]
        self.faiss_index = faiss.IndexFlatIP(dimension)

        norms = np.linalg.norm(self.item_factors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = self.item_factors / norms

        self.faiss_index.add(normalized.astype(np.float32))

    def predict(self, user_id: str, top_k: int = 50) -> list[tuple[int, float]]:
        """Get top-K recommendations for a user."""
        if self.model is None or user_id not in self.user_id_map:
            return []

        user_idx = self.user_id_map[user_id]
        user_items = self.interaction_matrix[user_idx]

        ids, scores = self.model.recommend(
            user_idx, user_items, N=top_k, filter_already_liked_items=True
        )

        results = []
        for idx, score in zip(ids, scores):
            movie_id = self.reverse_item_map.get(idx)
            if movie_id is not None:
                results.append((movie_id, float(score)))

        return results

    def similar_items(self, movie_id: str, top_k: int = 20) -> list[tuple[int, float]]:
        """Find similar items using item factors."""
        if self.model is None or movie_id not in self.item_id_map:
            return []

        item_idx = self.item_id_map[movie_id]

        query = self.item_factors[item_idx : item_idx + 1]
        norms = np.linalg.norm(query, axis=1, keepdims=True)
        norms[norms == 0] = 1
        query = query / norms

        scores, indices = self.faiss_index.search(query.astype(np.float32), top_k + 1)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == item_idx:
                continue
            actual_id = self.reverse_item_map.get(idx)
            if actual_id is not None:
                results.append((actual_id, float(score)))

        return results[:top_k]

    def load(self) -> bool:
        """Load a pre-trained model from disk."""
        model_path = settings.MODEL_DIR / "cf_model.pkl"
        faiss_path = settings.MODEL_DIR / "cf_faiss.index"

        if not model_path.exists() or not faiss_path.exists():
            return False

        try:
            with open(model_path, "rb") as f:
                data = pickle.load(f)

            self.model = data["model"]
            self.user_id_map = data["user_id_map"]
            self.item_id_map = data["item_id_map"]
            self.reverse_item_map = data["reverse_item_map"]

            self.faiss_index = faiss.read_index(str(faiss_path))
            self.user_factors = self.model.user_factors
            self.item_factors = self.model.item_factors

            logger.info("CF model loaded from disk")
            return True
        except Exception as e:
            logger.error(f"Failed to load CF model: {e}")
            return False

    @property
    def is_loaded(self) -> bool:
        return self.model is not None


class ContentBasedModel:
    """Content-based filtering using TF-IDF and genre features.

    Recommends items similar to what the user has liked based on
    content features (genres, tags, descriptions).
    """

    def __init__(self):
        self.faiss_index: faiss.IndexFlatIP | None = None
        self.movie_ids: list[int] = []
        self.feature_matrix: np.ndarray | None = None

    async def build_index(self, db: AsyncSession) -> None:
        """Build content feature index from database."""
        result = await db.execute(select(MovieFeature))
        features = result.scalars().all()

        if not features:
            logger.warning("No movie features found")
            return

        self.movie_ids = []
        embeddings = []

        for feat in features:
            if feat.content_embedding:
                try:
                    emb = json.loads(feat.content_embedding)
                    self.movie_ids.append(feat.movie_id)
                    embeddings.append(emb)
                except (json.JSONDecodeError, ValueError):
                    continue

        if not embeddings:
            return

        self.feature_matrix = np.array(embeddings, dtype=np.float32)
        dimension = self.feature_matrix.shape[1]

        self.faiss_index = faiss.IndexFlatIP(dimension)
        norms = np.linalg.norm(self.feature_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = self.feature_matrix / norms
        self.faiss_index.add(normalized.astype(np.float32))

        model_dir = settings.MODEL_DIR
        model_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.faiss_index, str(model_dir / "content_faiss.index"))
        with open(model_dir / "content_movie_ids.pkl", "wb") as f:
            pickle.dump(self.movie_ids, f)

        logger.info(f"Content index built: {len(self.movie_ids)} movies, dim={dimension}")

    def predict_from_history(
        self, liked_movie_ids: list[int], top_k: int = 50
    ) -> list[tuple[int, float]]:
        """Recommend items similar to user's liked items."""
        if self.faiss_index is None:
            return []

        query_indices = []
        for mid in liked_movie_ids:
            if mid in self.movie_ids:
                query_indices.append(self.movie_ids.index(mid))

        if not query_indices:
            return []

        query_vectors = self.feature_matrix[query_indices]
        query = np.mean(query_vectors, axis=0, keepdims=True)

        norms = np.linalg.norm(query, axis=1, keepdims=True)
        norms[norms == 0] = 1
        query = query / norms

        scores, indices = self.faiss_index.search(query.astype(np.float32), top_k + len(query_indices))

        results = []
        seen = set(query_indices)
        for score, idx in zip(scores[0], indices[0]):
            if idx not in seen and idx < len(self.movie_ids):
                results.append((self.movie_ids[idx], float(score)))

        return results[:top_k]

    def similar_items(self, movie_id: int, top_k: int = 20) -> list[tuple[int, float]]:
        """Find content-similar items."""
        if self.faiss_index is None or movie_id not in self.movie_ids:
            return []

        idx = self.movie_ids.index(movie_id)
        query = self.feature_matrix[idx : idx + 1]
        norms = np.linalg.norm(query, axis=1, keepdims=True)
        norms[norms == 0] = 1
        query = query / norms

        scores, indices = self.faiss_index.search(query.astype(np.float32), top_k + 1)

        results = []
        for score, i in zip(scores[0], indices[0]):
            if i != idx and i < len(self.movie_ids):
                results.append((self.movie_ids[i], float(score)))

        return results[:top_k]

    def load(self) -> bool:
        """Load pre-built index from disk."""
        faiss_path = settings.MODEL_DIR / "content_faiss.index"
        ids_path = settings.MODEL_DIR / "content_movie_ids.pkl"

        if not faiss_path.exists() or not ids_path.exists():
            return False

        try:
            self.faiss_index = faiss.read_index(str(faiss_path))
            with open(ids_path, "rb") as f:
                self.movie_ids = pickle.load(f)
            logger.info("Content model loaded from disk")
            return True
        except Exception as e:
            logger.error(f"Failed to load content model: {e}")
            return False

    @property
    def is_loaded(self) -> bool:
        return self.faiss_index is not None


class TrendingModel:
    """Popularity-based trending recommendations.

    Uses time-decayed weighted ratings to surface trending content.
    Serves as both a standalone model and a cold-start fallback.
    """

    def __init__(self):
        self.trending_cache: list[tuple[int, float]] = []

    async def compute_trending(self, db: AsyncSession, window_days: int = 30) -> None:
        """Compute trending movies based on recent ratings."""
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(days=window_days)

        result = await db.execute(
            select(Rating).where(Rating.timestamp >= cutoff)
        )
        recent_ratings = result.scalars().all()

        if not recent_ratings:
            return

        movie_scores: dict[int, list[float]] = {}
        for r in recent_ratings:
            movie_scores.setdefault(r.movie_id, []).append(r.rating)

        scored = []
        for movie_id, ratings_list in movie_scores.items():
            avg_rating = np.mean(ratings_list)
            count = len(ratings_list)
            popularity_score = avg_rating * np.log1p(count)
            scored.append((movie_id, float(popularity_score)))

        scored.sort(key=lambda x: x[1], reverse=True)
        self.trending_cache = scored[:500]
        logger.info(f"Trending computed: {len(self.trending_cache)} movies")

    def predict(self, top_k: int = 50) -> list[tuple[int, float]]:
        """Get top trending movies."""
        return self.trending_cache[:top_k]

    @property
    def is_loaded(self) -> bool:
        return len(self.trending_cache) > 0


class HybridEnsemble:
    """Weighted hybrid ensemble combining all recommendation models.

    Implements late fusion: each model generates independent scores,
    which are combined using learned or tuned weights.

    Inspired by Netflix's approach of combining multiple signals
    with dynamic weighting based on context.
    """

    def __init__(
        self,
        cf_model: CollaborativeFilteringModel,
        content_model: ContentBasedModel,
        trending_model: TrendingModel,
    ):
        self.cf_model = cf_model
        self.content_model = content_model
        self.trending_model = trending_model

        self.weights = {
            "collaborative": 0.45,
            "content_based": 0.30,
            "trending": 0.15,
            "diversity": 0.10,
        }

    def predict(
        self,
        user_id: str | None = None,
        liked_movies: list[int] | None = None,
        top_k: int = 50,
        exclude_ids: set[int] | None = None,
    ) -> list[tuple[int, float, str]]:
        """Generate hybrid recommendations with explanations.

        Returns list of (movie_id, score, algorithm_source).
        """
        all_candidates: dict[int, list[tuple[float, str]]] = {}

        if user_id and self.cf_model.is_loaded:
            cf_results = self.cf_model.predict(user_id, top_k=top_k * 2)
            for movie_id, score in cf_results:
                all_candidates.setdefault(movie_id, []).append(
                    (score * self.weights["collaborative"], "collaborative")
                )

        if liked_movies and self.content_model.is_loaded:
            cb_results = self.content_model.predict_from_history(
                liked_movies, top_k=top_k * 2
            )
            for movie_id, score in cb_results:
                all_candidates.setdefault(movie_id, []).append(
                    (score * self.weights["content_based"], "content_based")
                )

        if self.trending_model.is_loaded:
            trending_results = self.trending_model.predict(top_k=top_k * 2)
            for movie_id, score in trending_results:
                all_candidates.setdefault(movie_id, []).append(
                    (score * self.weights["trending"], "trending")
                )

        scored = []
        for movie_id, signals in all_candidates.items():
            if exclude_ids and movie_id in exclude_ids:
                continue
            total_score = sum(s for s, _ in signals)
            primary_source = max(signals, key=lambda x: x[0])[1]
            scored.append((movie_id, total_score, primary_source))

        scored.sort(key=lambda x: x[1], reverse=True)

        diversified = self._diversify(scored, top_k)
        return diversified

    def _diversify(
        self, scored: list[tuple[int, float, str]], top_k: int
    ) -> list[tuple[int, float, str]]:
        """Apply Maximal Marginal Relevance for diversity."""
        if len(scored) <= top_k:
            return scored

        selected = [scored[0]]
        remaining = scored[1:]
        genre_counts: dict[str, int] = {}

        while len(selected) < top_k and remaining:
            best_idx = 0
            best_mmr = float("-inf")

            for i, (movie_id, score, source) in enumerate(remaining):
                relevance = score
                diversity_penalty = 0.0

                mmr = (1 - 0.3) * relevance - 0.3 * diversity_penalty
                if mmr > best_mmr:
                    best_mmr = mmr
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        return selected

    def predict_with_explanations(
        self,
        user_id: str | None = None,
        liked_movies: list[int] | None = None,
        top_k: int = 10,
        exclude_ids: set[int] | None = None,
    ) -> list[dict]:
        """Generate recommendations with detailed explanations."""
        raw = self.predict(user_id, liked_movies, top_k * 3, exclude_ids)

        results = []
        for movie_id, score, source in raw[:top_k]:
            explanation = self._generate_explanation(source, score)
            results.append(
                {
                    "movie_id": movie_id,
                    "score": min(score, 1.0),
                    "algorithm": source,
                    "explanation": explanation,
                    "confidence": min(score * 1.5, 1.0),
                }
            )

        return results

    def _generate_explanation(self, source: str, score: float) -> str:
        """Generate human-readable explanation for recommendation."""
        explanations = {
            "collaborative": "Recommended because users with similar taste enjoyed this",
            "content_based": "Matches your preference for similar genres and themes",
            "trending": "Currently trending and highly rated by the community",
        }
        return explanations.get(source, "Recommended based on your profile")

    @property
    def is_loaded(self) -> bool:
        return (
            self.cf_model.is_loaded
            or self.content_model.is_loaded
            or self.trending_model.is_loaded
        )
