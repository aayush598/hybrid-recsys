"""Item-based collaborative filtering.

Builds an item-item cosine similarity matrix from the user-item
interaction matrix and predicts a user's score for unseen items as the
similarity-weighted sum of that user's observed ratings.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix, csr_matrix

logger = logging.getLogger(__name__)


class ItemBasedCF:
    """Item-based collaborative filtering with cosine item-item similarity."""

    def __init__(self, n_neighbors: int = 50):
        self.n_neighbors = n_neighbors
        self.user_id_map: dict = {}
        self.item_id_map: dict = {}
        self.reverse_item_map: dict = {}
        self.matrix: csr_matrix | None = None
        self.similarity: csr_matrix | None = None
        self.item_popularity: np.ndarray | None = None
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
        self.item_id_map = {i: j for j, i in enumerate(item_ids)}
        self.reverse_item_map = {j: i for i, j in self.item_id_map.items()}

        rows = df["user_id"].map(self.user_id_map).to_numpy()
        cols = df["item_id"].map(self.item_id_map).to_numpy()
        vals = df["rating"].to_numpy(dtype=np.float64)

        n_users, n_items = len(user_ids), len(item_ids)
        self.matrix = coo_matrix((vals, (rows, cols)), shape=(n_users, n_items)).tocsr()
        self.item_popularity = np.asarray(self.matrix.sum(axis=0)).ravel()

        self.similarity = self._compute_item_similarity(self.matrix, self.n_neighbors)

        self.is_trained = True
        logger.info(
            "ItemBasedCF trained: %d users, %d items, %d interactions",
            n_users,
            n_items,
            len(df),
        )
        return {
            "n_users": n_users,
            "n_items": n_items,
            "n_interactions": int(len(df)),
            "similarity_nnz": int(self.similarity.nnz),
        }

    def predict(self, user_id, top_k: int = 20, exclude_seen: bool = True) -> list[tuple[str, float]]:
        """Predict top-K items for a user via similarity-weighted rated items.

        Unknown users fall back to globally popular items. Untrained models
        return an empty list.
        """
        if not self.is_trained or self.matrix is None or self.similarity is None:
            return []

        top_k = max(int(top_k), 1)
        u_idx = self.user_id_map.get(str(user_id))
        if u_idx is None:
            return self._popular_fallback(top_k)

        start, end = self.matrix.indptr[u_idx], self.matrix.indptr[u_idx + 1]
        rated_cols = self.matrix.indices[start:end]
        ratings = self.matrix.data[start:end]

        if rated_cols.size == 0:
            return self._popular_fallback(top_k)

        neighbor_sims = self.similarity[:, rated_cols]
        numerator = np.asarray(neighbor_sims @ ratings).ravel()
        denominator = np.asarray(np.abs(neighbor_sims).sum(axis=1)).ravel()

        scores = np.divide(
            numerator,
            denominator,
            out=np.zeros_like(numerator),
            where=denominator > 1e-12,
        )

        if exclude_seen:
            scores[rated_cols] = -np.inf

        top_k = min(top_k, len(scores))
        top_indices = np.argpartition(scores, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        return [
            (self.reverse_item_map[int(i)], float(scores[i]))
            for i in top_indices
            if scores[i] > -np.inf
        ]

    def similar_items(self, item_id, top_k: int = 10) -> list[tuple[str, float]]:
        """Return the most similar items to the given item."""
        if not self.is_trained or self.similarity is None:
            return []

        i_idx = self.item_id_map.get(str(item_id))
        if i_idx is None:
            return []

        row_start, row_end = self.similarity.indptr[i_idx], self.similarity.indptr[i_idx + 1]
        candidates = self.similarity.indices[row_start:row_end]
        sims = self.similarity.data[row_start:row_end]

        order = np.argsort(sims)[::-1][: max(int(top_k), 1)]
        return [(self.reverse_item_map[int(candidates[j])], float(sims[j])) for j in order]

    def _popular_fallback(self, top_k: int) -> list[tuple[str, float]]:
        """Most popular items by cumulative rating, for cold-start users."""
        order = np.argsort(self.item_popularity)[::-1][:top_k]
        return [
            (self.reverse_item_map[int(i)], float(self.item_popularity[i]))
            for i in order
        ]

    @staticmethod
    def _compute_item_similarity(matrix: csr_matrix, n_neighbors: int) -> csr_matrix:
        """Sparse item-item cosine similarity keeping only the top-K neighbors."""
        item_user = matrix.T.tocsr()
        norms = np.sqrt(np.asarray(item_user.multiply(item_user).sum(axis=1)).ravel())
        norms[norms == 0] = 1.0
        normalized = item_user.multiply(1.0 / norms[:, None]).tocsr().astype(np.float64)

        similarity = (normalized @ normalized.T).tocsr()
        similarity.setdiag(0.0)
        similarity.eliminate_zeros()

        n_items = similarity.shape[0]
        keep_rows, keep_cols, keep_vals = [], [], []
        for i in range(n_items):
            row_start, row_end = similarity.indptr[i], similarity.indptr[i + 1]
            row_cols = similarity.indices[row_start:row_end]
            row_vals = similarity.data[row_start:row_end]
            if row_cols.size > n_neighbors:
                top = np.argpartition(row_vals, -n_neighbors)[-n_neighbors:]
                row_cols, row_vals = row_cols[top], row_vals[top]
            keep_rows.append(np.full(row_cols.size, i))
            keep_cols.append(row_cols)
            keep_vals.append(row_vals)

        trimmed = coo_matrix(
            (
                np.concatenate(keep_vals) if keep_vals else np.array([]),
                (
                    np.concatenate(keep_rows) if keep_rows else np.array([]),
                    np.concatenate(keep_cols) if keep_cols else np.array([]),
                ),
            ),
            shape=(n_items, n_items),
        ).tocsr()
        trimmed.eliminate_zeros()
        return trimmed
