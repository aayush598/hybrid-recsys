"""User-based collaborative filtering using KNN cosine similarity.

Builds a user-item interaction matrix, computes user-user cosine
similarity, and predicts ratings for unseen items as the weighted
average of the target user's nearest neighbors' (mean-centered) ratings.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix, csr_matrix

logger = logging.getLogger(__name__)


class UserBasedCF:
    """User-based collaborative filtering with cosine-similarity KNN."""

    def __init__(self, n_neighbors: int = 50, min_similarity: float = 0.0):
        self.n_neighbors = n_neighbors
        self.min_similarity = min_similarity
        self.user_id_map: dict = {}
        self.reverse_user_map: dict = {}
        self.item_id_map: dict = {}
        self.reverse_item_map: dict = {}
        self.matrix: csr_matrix | None = None
        self.centered_matrix: csr_matrix | None = None
        self.similarity: np.ndarray | None = None
        self.user_means: np.ndarray | None = None
        self.item_popularity: np.ndarray | None = None
        self.global_mean: float = 0.0
        self.is_trained = False

    def train(self, interactions_df: pd.DataFrame) -> dict:
        """Train the model from an interactions dataframe.

        Args:
            interactions_df: DataFrame with columns user_id, item_id, rating.

        Returns:
            Training metrics.
        """
        required = {"user_id", "item_id", "rating"}
        if not required.issubset(interactions_df.columns):
            raise ValueError(f"interactions_df must contain columns {required}")

        df = interactions_df[list(required)].dropna().copy()
        df["user_id"] = df["user_id"].astype(str)
        df["item_id"] = df["item_id"].astype(str)
        df = df.groupby(["user_id", "item_id"], as_index=False)["rating"].mean()

        user_ids = df["user_id"].unique()
        item_ids = df["item_id"].unique()
        self.user_id_map = {u: i for i, u in enumerate(user_ids)}
        self.reverse_user_map = {i: u for u, i in self.user_id_map.items()}
        self.item_id_map = {i: j for j, i in enumerate(item_ids)}
        self.reverse_item_map = {j: i for i, j in self.item_id_map.items()}

        rows = df["user_id"].map(self.user_id_map).to_numpy()
        cols = df["item_id"].map(self.item_id_map).to_numpy()
        vals = df["rating"].to_numpy(dtype=np.float64)

        n_users, n_items = len(user_ids), len(item_ids)
        self.matrix = coo_matrix((vals, (rows, cols)), shape=(n_users, n_items)).tocsr()

        rating_counts = np.diff(self.matrix.indptr)
        row_sums = np.asarray(self.matrix.sum(axis=1)).ravel()
        self.global_mean = float(vals.mean())
        self.user_means = np.divide(
            row_sums,
            rating_counts,
            out=np.full(n_users, self.global_mean),
            where=rating_counts > 0,
        )

        centered_vals = vals - self.user_means[rows]
        self.centered_matrix = coo_matrix(
            (centered_vals, (rows, cols)), shape=(n_users, n_items)
        ).tocsr()

        self.item_popularity = np.asarray(self.matrix.sum(axis=0)).ravel()
        self.similarity = self._compute_similarity(self.centered_matrix)

        self.is_trained = True
        logger.info(
            "UserBasedCF trained: %d users, %d items, %d interactions",
            n_users,
            n_items,
            len(df),
        )
        return {
            "n_users": n_users,
            "n_items": n_items,
            "n_interactions": int(len(df)),
            "sparsity": float(1.0 - len(df) / (n_users * n_items)),
        }

    def predict(self, user_id, top_k: int = 20, exclude_seen: bool = True) -> list[tuple[str, float]]:
        """Predict top-K items for a user via neighbor rating aggregation.

        Unknown users fall back to globally popular items. Untrained models
        return an empty list.
        """
        if not self.is_trained or self.matrix is None or self.similarity is None:
            return []

        top_k = max(int(top_k), 1)
        u_idx = self.user_id_map.get(str(user_id))
        if u_idx is None:
            return self._popular_fallback(top_k)

        scores = self._score_user(u_idx)
        if exclude_seen:
            start, end = self.matrix.indptr[u_idx], self.matrix.indptr[u_idx + 1]
            scores[self.matrix.indices[start:end]] = -np.inf

        top_k = min(top_k, len(scores))
        top_indices = np.argpartition(scores, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        return [
            (self.reverse_item_map[int(i)], float(scores[i]))
            for i in top_indices
            if np.isfinite(scores[i])
        ]

    def similar_users(self, user_id, top_k: int = 10) -> list[tuple[str, float]]:
        """Return the most similar users to the given user."""
        if not self.is_trained or self.similarity is None:
            return []

        u_idx = self.user_id_map.get(str(user_id))
        if u_idx is None:
            return []

        sims = self.similarity[u_idx].copy()
        sims[u_idx] = -np.inf
        top_k = min(max(int(top_k), 1), len(sims) - 1)
        top_indices = np.argpartition(sims, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(sims[top_indices])[::-1]]
        return [
            (self.reverse_user_map[int(i)], float(sims[i]))
            for i in top_indices
            if np.isfinite(sims[i])
        ]

    def _score_user(self, u_idx: int) -> np.ndarray:
        """Mean-centered weighted average over the user's K nearest neighbors."""
        sims = self.similarity[u_idx].copy()
        sims[u_idx] = 0.0
        sims[sims < self.min_similarity] = 0.0

        k = min(self.n_neighbors, len(sims))
        neighbor_idx = np.argpartition(sims, -k)[-k:]
        neighbor_idx = neighbor_idx[sims[neighbor_idx] > 0]
        if neighbor_idx.size == 0:
            return np.full(self.matrix.shape[1], self.user_means[u_idx])

        weights = sims[neighbor_idx]
        rated_by_neighbors = self.matrix[neighbor_idx]
        centered = self.centered_matrix[neighbor_idx]

        numerator = weights @ centered.toarray()
        denominator = np.abs(weights) @ self._indicator(rated_by_neighbors)

        scores = self.user_means[u_idx] + np.divide(
            numerator, denominator, out=np.zeros_like(numerator), where=denominator > 1e-12
        )
        unrated_mask = denominator <= 1e-12
        scores[unrated_mask] = self.user_means[u_idx]
        return scores

    @staticmethod
    def _indicator(m: csr_matrix) -> np.ndarray:
        """Dense 0/1 matrix marking which items each neighbor rated."""
        ind = m.tocoo()
        dense = np.zeros(m.shape, dtype=np.float64)
        dense[ind.row, ind.col] = 1.0
        return dense

    def _popular_fallback(self, top_k: int) -> list[tuple[str, float]]:
        """Most popular items by cumulative rating, for cold-start users."""
        pop = self.item_popularity
        order = np.argsort(pop)[::-1][:top_k]
        return [(self.reverse_item_map[int(i)], float(pop[i])) for i in order]

    @staticmethod
    def _compute_similarity(centered: csr_matrix, chunk_size: int = 1024) -> np.ndarray:
        """Pairwise cosine similarity between users, computed in chunks."""
        n_users = centered.shape[0]
        norms = np.sqrt(np.asarray(centered.multiply(centered).sum(axis=1)).ravel())
        norms[norms == 0] = 1.0
        normalized = centered.multiply(1.0 / norms[:, None]).tocsr()

        similarity = np.empty((n_users, n_users), dtype=np.float64)
        for start in range(0, n_users, chunk_size):
            end = min(start + chunk_size, n_users)
            similarity[start:end] = (
                normalized[start:end] @ normalized.T
            ).toarray()
        np.clip(similarity, -1.0, 1.0, out=similarity)
        return similarity
