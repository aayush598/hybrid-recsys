from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Movie, Rating

logger = logging.getLogger(__name__)


class RecommendationEvaluator:
    """Comprehensive evaluation framework for recommendation quality.

    Computes standard IR metrics plus beyond-accuracy metrics
    (diversity, novelty, coverage, serendipity).

    Inspired by Netflix's evaluation methodology combining offline
    metrics with online A/B testing signals.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ratings_df: pd.DataFrame | None = None
        self.movies_df: pd.DataFrame | None = None

    async def load_data(self) -> None:
        """Load evaluation data from database."""
        ratings_result = await self.db.execute(select(Rating))
        ratings = ratings_result.scalars().all()
        self.ratings_df = pd.DataFrame(
            [{"user_id": r.user_id, "movie_id": r.movie_id, "rating": r.rating} for r in ratings]
        )

        movies_result = await self.db.execute(select(Movie))
        movies = movies_result.scalars().all()
        self.movies_df = pd.DataFrame(
            [{"movie_id": m.id, "genres": m.genres or ""} for m in movies]
        )

        logger.info(f"Loaded {len(self.ratings_df)} ratings and {len(self.movies_df)} movies")

    def precision_at_k(
        self, recommended: list[int], relevant: set[int], k: int
    ) -> float:
        """Precision@K: fraction of recommended items that are relevant."""
        recommended_k = recommended[:k]
        if not recommended_k:
            return 0.0
        relevant_in_rec = len(set(recommended_k) & relevant)
        return relevant_in_rec / len(recommended_k)

    def recall_at_k(
        self, recommended: list[int], relevant: set[int], k: int
    ) -> float:
        """Recall@K: fraction of relevant items that are recommended."""
        recommended_k = recommended[:k]
        if not relevant:
            return 0.0
        relevant_in_rec = len(set(recommended_k) & relevant)
        return relevant_in_rec / len(relevant)

    def ndcg_at_k(
        self, recommended: list[int], relevant: set[int], k: int
    ) -> float:
        """Normalized Discounted Cumulative Gain@K."""
        dcg = 0.0
        for i, item in enumerate(recommended[:k]):
            if item in relevant:
                dcg += 1.0 / np.log2(i + 2)

        ideal_dcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(relevant), k)))

        if ideal_dcg == 0:
            return 0.0
        return dcg / ideal_dcg

    def map_at_k(
        self, recommended: list[int], relevant: set[int], k: int
    ) -> float:
        """Mean Average Precision@K."""
        recommended_k = recommended[:k]
        if not relevant:
            return 0.0

        score = 0.0
        hits = 0
        for i, item in enumerate(recommended_k):
            if item in relevant:
                hits += 1
                score += hits / (i + 1)

        return score / min(len(relevant), k)

    def hit_rate_at_k(
        self, recommended: list[int], relevant: set[int], k: int
    ) -> float:
        """Hit Rate@K: 1 if any relevant item is in top-K, else 0."""
        return 1.0 if len(set(recommended[:k]) & relevant) > 0 else 0.0

    def coverage(
        self, all_recommendations: list[list[int]], total_items: int
    ) -> float:
        """Catalog coverage: fraction of items ever recommended."""
        recommended_items = set()
        for recs in all_recommendations:
            recommended_items.update(recs)
        return len(recommended_items) / total_items if total_items > 0 else 0.0

    def diversity(
        self, recommended: list[int], movies_df: pd.DataFrame
    ) -> float:
        """Intra-list diversity based on genre dissimilarity."""
        if len(recommended) < 2:
            return 0.0

        genre_sets = []
        for movie_id in recommended:
            row = movies_df[movies_df["movie_id"] == movie_id]
            if not row.empty:
                genres = set(row.iloc[0]["genres"].split("|"))
                genre_sets.append(genres)
            else:
                genre_sets.append(set())

        dissimilarities = []
        for i in range(len(genre_sets)):
            for j in range(i + 1, len(genre_sets)):
                union = genre_sets[i] | genre_sets[j]
                intersection = genre_sets[i] & genre_sets[j]
                jaccard = 1.0 - (len(intersection) / len(union)) if union else 0.0
                dissimilarities.append(jaccard)

        return np.mean(dissimilarities) if dissimilarities else 0.0

    def novelty(
        self, recommended: list[int], movies_df: pd.DataFrame, ratings_df: pd.DataFrame
    ) -> float:
        """Novelty: inverse popularity of recommended items."""
        popularity = ratings_df.groupby("movie_id").size()
        max_pop = popularity.max()

        novelties = []
        for movie_id in recommended:
            pop = popularity.get(movie_id, 0)
            nov = 1.0 - (pop / max_pop) if max_pop > 0 else 1.0
            novelties.append(nov)

        return np.mean(novelties) if novelties else 0.0

    async def evaluate_model(
        self,
        recommendations: dict[str, list[int]],
        k_values: list[int] = [5, 10, 20],
    ) -> dict:
        """Full evaluation of a recommendation model."""
        if self.ratings_df is None or self.movies_df is None:
            await self.load_data()

        user_threshold = self.ratings_df.groupby("user_id").size()
        test_users = user_threshold[user_threshold >= 10].index.tolist()

        metrics = {
            "precision_at_k": {},
            "recall_at_k": {},
            "ndcg_at_k": {},
            "map_at_k": {},
            "hit_rate_at_k": {},
        }

        all_recs = []

        for user_id in test_users:
            user_ratings = self.ratings_df[self.ratings_df["user_id"] == user_id]
            high_rated = set(
                user_ratings[user_ratings["rating"] >= 3.5]["movie_id"].tolist()
            )
            recommended = recommendations.get(user_id, [])
            all_recs.append(recommended)

            for k in k_values:
                metrics["precision_at_k"][f"k={k}"] = metrics["precision_at_k"].get(f"k={k}", [])
                metrics["recall_at_k"][f"k={k}"] = metrics["recall_at_k"].get(f"k={k}", [])
                metrics["ndcg_at_k"][f"k={k}"] = metrics["ndcg_at_k"].get(f"k={k}", [])
                metrics["map_at_k"][f"k={k}"] = metrics["map_at_k"].get(f"k={k}", [])
                metrics["hit_rate_at_k"][f"k={k}"] = metrics["hit_rate_at_k"].get(f"k={k}", [])

                metrics["precision_at_k"][f"k={k}"].append(
                    self.precision_at_k(recommended, high_rated, k)
                )
                metrics["recall_at_k"][f"k={k}"].append(
                    self.recall_at_k(recommended, high_rated, k)
                )
                metrics["ndcg_at_k"][f"k={k}"].append(
                    self.ndcg_at_k(recommended, high_rated, k)
                )
                metrics["map_at_k"][f"k={k}"].append(
                    self.map_at_k(recommended, high_rated, k)
                )
                metrics["hit_rate_at_k"][f"k={k}"].append(
                    self.hit_rate_at_k(recommended, high_rated, k)
                )

        averaged_metrics = {}
        for metric_name, k_scores in metrics.items():
            averaged_metrics[metric_name] = {}
            for k_key, values in k_scores.items():
                averaged_metrics[metric_name][k_key] = round(float(np.mean(values)), 4)

        total_items = len(self.movies_df)
        averaged_metrics["coverage"] = round(self.coverage(all_recs, total_items), 4)

        sample_recs = all_recs[:100]
        averaged_metrics["diversity"] = round(
            np.mean([self.diversity(recs, self.movies_df) for recs in sample_recs]), 4
        )
        averaged_metrics["novelty"] = round(
            np.mean([self.novelty(recs, self.movies_df, self.ratings_df) for recs in sample_recs]), 4
        )

        averaged_metrics["test_users"] = len(test_users)
        averaged_metrics["total_items"] = total_items

        return averaged_metrics
