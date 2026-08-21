"""Bayesian Personalized Ranking (BPR) for implicit feedback.

Implements BPR-MF (Rendle et al., 2009) which learns from pairs of
observed vs unobserved interactions, optimizing AUC.
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BPRModel:
    """Bayesian Personalized Ranking for Matrix Factorization.

    Optimizes AUC by learning from (positive, negative) pairs of interactions.
    Better suited for implicit feedback than standard MF.
    """

    def __init__(self):
        self.user_factors: np.ndarray | None = None
        self.item_factors: np.ndarray | None = None
        self.user_bias: np.ndarray | None = None
        self.item_bias: np.ndarray | None = None
        self.user_id_map: dict[str, int] = {}
        self.item_id_map: dict[int, int] = {}
        self.reverse_item_map: dict[int, int] = {}
        self.is_trained = False

    def train(
        self,
        interaction_matrix: csr_matrix,
        user_id_map: dict[str, int],
        item_id_map: dict[int, int],
        reverse_item_map: dict[int, int],
        factors: int = 64,
        learning_rate: float = 0.05,
        regularization: float = 0.01,
        epochs: int = 20,
        num_samples: int = 100000,
    ) -> dict:
        """Train BPR model.

        Args:
            interaction_matrix: Sparse user-item interaction matrix
            user_id_map: Mapping from external user IDs to internal indices
            item_id_map: Mapping from external item IDs to internal indices
            reverse_item_map: Mapping from internal item indices to external IDs
            factors: Latent embedding dimension
            learning_rate: SGD learning rate
            regularization: L2 regularization strength
            epochs: Number of training epochs
            num_samples: Number of negative samples per epoch

        Returns:
            Training metrics dictionary
        """
        logger.info("Training BPR model")
        n_users, n_items = interaction_matrix.shape

        self.user_id_map = user_id_map
        self.item_id_map = item_id_map
        self.reverse_item_map = reverse_item_map

        # Initialize parameters
        rng = np.random.default_rng(42)
        self.user_factors = rng.normal(0, 0.01, (n_users, factors)).astype(np.float32)
        self.item_factors = rng.normal(0, 0.01, (n_items, factors)).astype(np.float32)
        self.user_bias = np.zeros(n_users, dtype=np.float32)
        self.item_bias = np.zeros(n_items, dtype=np.float32)

        # Build positive interaction lookup for efficient negative sampling
        interaction_csr = interaction_matrix.tocsr()
        pos_items_per_user = {}
        for u in range(n_users):
            items = interaction_csr[u].indices
            if len(items) > 0:
                pos_items_per_user[u] = set(items.tolist())

        metrics = {"epochs": [], "auc": []}

        for epoch in range(epochs):
            # Sample positive and negative pairs
            pos_users, pos_items, neg_items = [], [], []
            for _ in range(num_samples):
                u = rng.integers(0, n_users)
                if u not in pos_items_per_user or len(pos_items_per_user[u]) == 0:
                    continue
                pos = rng.choice(list(pos_items_per_user[u]))
                neg = rng.integers(0, n_items)
                while neg in pos_items_per_user[u]:
                    neg = rng.integers(0, n_items)
                pos_users.append(u)
                pos_items.append(pos)
                neg_items.append(neg)

            if not pos_users:
                continue

            # SGD update
            for i in range(len(pos_users)):
                u, pos_i, neg_i = pos_users[i], pos_items[i], neg_items[i]

                # Score difference
                x_ui = (
                    np.dot(self.user_factors[u], self.item_factors[pos_i])
                    + self.user_bias[u]
                    + self.item_bias[pos_i]
                )
                x_uj = (
                    np.dot(self.user_factors[u], self.item_factors[neg_i])
                    + self.user_bias[u]
                    + self.item_bias[neg_i]
                )

                # Sigmoid derivative
                sig = 1.0 / (1.0 + np.exp(min(x_ui - x_uj, 20)))

                # Gradient updates
                grad_u = sig * (self.item_factors[pos_i] - self.item_factors[neg_i]) - regularization * self.user_factors[u]
                grad_pos = sig * self.user_factors[u] - regularization * self.item_factors[pos_i]
                grad_neg = -sig * self.user_factors[u] - regularization * self.item_factors[neg_i]

                self.user_factors[u] += learning_rate * grad_u
                self.item_factors[pos_i] += learning_rate * grad_pos
                self.item_factors[neg_i] += learning_rate * grad_neg

                # Bias updates
                self.user_bias[u] += learning_rate * (sig - regularization * self.user_bias[u])
                self.item_bias[pos_i] += learning_rate * (sig - regularization * self.item_bias[pos_i])
                self.item_bias[neg_i] += learning_rate * (-sig - regularization * self.item_bias[neg_i])

            # Compute approximate AUC
            if (epoch + 1) % 5 == 0:
                auc = self._compute_auc(interaction_csr, n_users, rng, sample_count=1000)
                metrics["epochs"].append(epoch + 1)
                metrics["auc"].append(auc)
                logger.info(f"BPR epoch {epoch + 1}/{epochs}, AUC: {auc:.4f}")

        self.is_trained = True
        self._save()
        logger.info("BPR training complete")
        return metrics

    def predict(self, user_id: str, top_k: int = 50) -> list[tuple[int, float]]:
        """Predict top-K items for a user."""
        if not self.is_trained or user_id not in self.user_id_map:
            return []

        u_idx = self.user_id_map[user_id]
        scores = (
            self.user_factors[u_idx] @ self.item_factors.T
            + self.item_bias
            + self.user_bias[u_idx]
        )

        # Get top-K indices (descending)
        top_indices = np.argpartition(scores, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        return [
            (self.reverse_item_map[int(i)], float(scores[i]))
            for i in top_indices
            if int(i) in self.reverse_item_map
        ]

    def similar_items(self, movie_id: str, top_k: int = 20) -> list[tuple[int, float]]:
        """Find similar items using item factor cosine similarity."""
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

        similarities[idx] = -np.inf  # Exclude self
        top_indices = np.argpartition(similarities, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]

        return [
            (self.reverse_item_map[int(i)], float(similarities[i]))
            for i in top_indices
            if int(i) in self.reverse_item_map
        ]

    def _compute_auc(self, interaction_csr, n_users, rng, sample_count=1000):
        """Compute approximate AUC."""
        hits = 0
        total = 0
        for _ in range(sample_count):
            u = rng.integers(0, n_users)
            pos_items = set(interaction_csr[u].indices.tolist())
            if not pos_items:
                continue
            pos = rng.choice(list(pos_items))
            neg = rng.integers(0, interaction_csr.shape[1])
            while neg in pos_items:
                neg = rng.integers(0, interaction_csr.shape[1])

            pos_score = self.user_factors[u] @ self.item_factors[pos] + self.item_bias[pos]
            neg_score = self.user_factors[u] @ self.item_factors[neg] + self.item_bias[neg]

            if pos_score > neg_score:
                hits += 1
            total += 1

        return hits / total if total > 0 else 0.5

    def _save(self) -> None:
        """Save BPR model to disk."""
        settings.MODEL_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "user_factors": self.user_factors,
            "item_factors": self.item_factors,
            "user_bias": self.user_bias,
            "item_bias": self.item_bias,
            "user_id_map": self.user_id_map,
            "item_id_map": self.item_id_map,
            "reverse_item_map": self.reverse_item_map,
        }
        path = settings.MODEL_DIR / "bpr_model.pkl"
        with open(path, "wb") as f:
            pickle.dump(data, f)
        logger.info(f"BPR model saved to {path}")

    def load(self) -> bool:
        """Load BPR model from disk."""
        path = settings.MODEL_DIR / "bpr_model.pkl"
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            self.user_factors = data["user_factors"]
            self.item_factors = data["item_factors"]
            self.user_bias = data["user_bias"]
            self.item_bias = data["item_bias"]
            self.user_id_map = data["user_id_map"]
            self.item_id_map = data["item_id_map"]
            self.reverse_item_map = data["reverse_item_map"]
            self.is_trained = True
            logger.info("BPR model loaded")
            return True
        except Exception as e:
            logger.warning(f"Failed to load BPR model: {e}")
            return False
