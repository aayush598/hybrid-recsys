"""SVD-based collaborative filtering.

Uses Truncated SVD (from scikit-learn) for latent factor decomposition,
complementing the ALS-based model with a different factorization approach.
"""

from __future__ import annotations

import logging
import pickle

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SVDCollaborativeFiltering:
    """SVD-based collaborative filtering model.

    Uses Truncated SVD to decompose the user-item interaction matrix
    into latent factors. Good as a complementary approach to ALS.
    """

    def __init__(self):
        self.svd: TruncatedSVD | None = None
        self.user_factors: np.ndarray | None = None
        self.item_factors: np.ndarray | None = None
        self.user_id_map: dict[str, int] = {}
        self.item_id_map: dict[int, int] = {}
        self.reverse_item_map: dict[int, int] = {}
        self.mean_rating: float = 0.0
        self.is_trained = False

    def train(
        self,
        interaction_matrix: csr_matrix,
        user_id_map: dict[str, int],
        item_id_map: dict[int, int],
        reverse_item_map: dict[int, int],
        n_factors: int = 50,
    ) -> dict:
        """Train SVD model.

        Args:
            interaction_matrix: Sparse user-item matrix
            user_id_map: User ID mapping
            item_id_map: Item ID mapping
            reverse_item_map: Reverse item ID mapping
            n_factors: Number of latent factors

        Returns:
            Training metrics
        """
        logger.info(f"Training SVD model with {n_factors} factors")

        self.user_id_map = user_id_map
        self.item_id_map = item_id_map
        self.reverse_item_map = reverse_item_map

        # Compute mean rating for bias
        self.mean_rating = interaction_matrix.data.mean() if interaction_matrix.nnz > 0 else 0.0

        # Fit Truncated SVD
        self.svd = TruncatedSVD(n_components=n_factors, random_state=42, algorithm="randomized")
        self.user_factors = self.svd.fit_transform(interaction_matrix).astype(np.float32)

        # Item factors from the right singular vectors
        self.item_factors = self.svd.components_.T.astype(np.float32)

        explained_var = self.svd.explained_variance_ratio_.sum()
        self.is_trained = True
        self._save()

        logger.info(f"SVD model trained, explained variance: {explained_var:.4f}")
        return {"explained_variance": float(explained_var), "n_factors": n_factors}

    def predict(self, user_id: str, top_k: int = 50) -> list[tuple[int, float]]:
        """Predict top-K items for a user."""
        if not self.is_trained or user_id not in self.user_id_map:
            return []

        u_idx = self.user_id_map[user_id]
        scores = self.user_factors[u_idx] @ self.item_factors.T + self.mean_rating

        top_indices = np.argpartition(scores, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        return [
            (self.reverse_item_map[int(i)], float(scores[i]))
            for i in top_indices
            if int(i) in self.reverse_item_map
        ]

    def similar_items(self, movie_id: str, top_k: int = 20) -> list[tuple[int, float]]:
        """Find similar items using item factor similarity."""
        if not self.is_trained:
            return []

        int_id = int(movie_id)
        if int_id not in self.item_id_map:
            return []

        idx = self.item_id_map[int_id]
        target = self.item_factors[idx]
        norm = np.linalg.norm(target)
        if norm < 1e-10:
            return []

        target_normalized = target / norm
        item_norms = np.linalg.norm(self.item_factors, axis=1, keepdims=True)
        item_norms = np.maximum(item_norms, 1e-10)
        normalized_items = self.item_factors / item_norms
        similarities = normalized_items @ target_normalized

        similarities[idx] = -np.inf
        top_indices = np.argpartition(similarities, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]

        return [
            (self.reverse_item_map[int(i)], float(similarities[i]))
            for i in top_indices
            if int(i) in self.reverse_item_map
        ]

    def _save(self) -> None:
        """Save SVD model to disk."""
        settings.MODEL_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "svd": self.svd,
            "user_factors": self.user_factors,
            "item_factors": self.item_factors,
            "user_id_map": self.user_id_map,
            "item_id_map": self.item_id_map,
            "reverse_item_map": self.reverse_item_map,
            "mean_rating": self.mean_rating,
        }
        with open(settings.MODEL_DIR / "svd_model.pkl", "wb") as f:
            pickle.dump(data, f)

    def load(self) -> bool:
        """Load SVD model from disk."""
        try:
            with open(settings.MODEL_DIR / "svd_model.pkl", "rb") as f:
                data = pickle.load(f)
            self.svd = data["svd"]
            self.user_factors = data["user_factors"]
            self.item_factors = data["item_factors"]
            self.user_id_map = data["user_id_map"]
            self.item_id_map = data["item_id_map"]
            self.reverse_item_map = data["reverse_item_map"]
            self.mean_rating = data["mean_rating"]
            self.is_trained = True
            logger.info("SVD model loaded")
            return True
        except Exception as e:
            logger.warning(f"Failed to load SVD model: {e}")
            return False
