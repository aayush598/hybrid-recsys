"""Session-Based Sequential Recommendations (GRU4Rec-style).

Implements session-based recommendations using recurrent neural networks
for modeling user interaction sequences within a session.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SessionConfig:
    """Configuration for session-based model."""
    n_items: int = 62000
    embedding_dim: int = 64
    hidden_dim: int = 128
    n_layers: int = 1
    dropout: float = 0.1
    learning_rate: float = 0.001
    batch_size: int = 256
    max_session_length: int = 50
    temperature: float = 1.0


class GRUCell:
    """Simple GRU cell implementation (no PyTorch dependency)."""

    def __init__(self, input_dim: int, hidden_dim: int):
        self.hidden_dim = hidden_dim

        # Xavier initialization
        scale = math.sqrt(2.0 / (input_dim + hidden_dim))
        self.W_z = np.random.randn(hidden_dim, input_dim) * scale
        self.U_z = np.random.randn(hidden_dim, hidden_dim) * scale
        self.b_z = np.zeros(hidden_dim)

        self.W_r = np.random.randn(hidden_dim, input_dim) * scale
        self.U_r = np.random.randn(hidden_dim, hidden_dim) * scale
        self.b_r = np.zeros(hidden_dim)

        self.W_h = np.random.randn(hidden_dim, input_dim) * scale
        self.U_h = np.random.randn(hidden_dim, hidden_dim) * scale
        self.b_h = np.zeros(hidden_dim)

    def forward(self, x: np.ndarray, h_prev: np.ndarray) -> np.ndarray:
        """Forward pass through GRU cell."""
        # Update gate
        z = self._sigmoid(self.W_z @ x + self.U_z @ h_prev + self.b_z)

        # Reset gate
        r = self._sigmoid(self.W_r @ x + self.U_r @ h_prev + self.b_r)

        # Candidate hidden state
        h_tilde = np.tanh(self.W_h @ x + self.U_h @ (r * h_prev) + self.b_h)

        # Hidden state
        h = (1 - z) * h_prev + z * h_tilde
        return h

    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


class SessionEncoder:
    """Encodes session sequences into fixed-size representations."""

    def __init__(self, config: SessionConfig):
        self.config = config

        # Embedding layer
        scale = math.sqrt(2.0 / config.n_items)
        self.item_embeddings = np.random.randn(config.n_items, config.embedding_dim) * scale

        # GRU
        self.gru = GRUCell(config.embedding_dim, config.hidden_dim)

        # Output projection
        self.W_out = np.random.randn(config.n_items, config.hidden_dim) * scale

    def encode_session(
        self,
        item_ids: list[int],
        mask: list[bool] | None = None,
    ) -> np.ndarray:
        """Encode a session into a fixed-size representation."""
        h = np.zeros(self.config.hidden_dim)

        for i, item_id in enumerate(item_ids):
            if mask and not mask[i]:
                continue

            if item_id < 0 or item_id >= self.config.n_items:
                continue

            x = self.item_embeddings[item_id]
            h = self.gru.forward(x, h)

        return h

    def predict_next(
        self,
        session_items: list[int],
        mask: list[bool] | None = None,
    ) -> np.ndarray:
        """Predict scores for all items given session history."""
        h = self.encode_session(session_items, mask)

        # Score all items
        scores = self.W_out @ h

        # Apply temperature
        scores = scores / self.config.temperature

        return scores

    def forward(
        self,
        sessions: list[list[int]],
        targets: list[int],
    ) -> tuple[np.ndarray, np.ndarray]:
        """Forward pass for training.

        Returns:
            scores: (batch_size, n_items) prediction scores
            loss: Cross-entropy loss
        """
        batch_size = len(sessions)
        scores = np.zeros((batch_size, self.config.n_items))

        for i, (session, target) in enumerate(zip(sessions, targets)):
            scores[i] = self.predict_next(session)

        # Cross-entropy loss
        probs = self._softmax(scores)
        loss = -np.mean([
            np.log(probs[i, target] + 1e-10)
            for i, target in enumerate(targets)
        ])

        return scores, loss

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        x_max = np.max(x, axis=1, keepdims=True)
        exp_x = np.exp(x - x_max)
        return exp_x / np.sum(exp_x, axis=1, keepdims=True)


class SessionRecommender:
    """Session-based recommendation engine."""

    def __init__(self, config: SessionConfig | None = None):
        self.config = config or SessionConfig()
        self.encoder = SessionEncoder(self.config)
        self.session_cache: dict[str, list[int]] = {}
        self.interaction_buffer: list[tuple[list[int], int]] = []

    def get_recommendations(
        self,
        session_items: list[int],
        n_recommendations: int = 10,
        exclude_items: list[int] | None = None,
    ) -> list[tuple[int, float]]:
        """Get recommendations for a session."""
        scores = self.encoder.predict_next(session_items)

        # Exclude items in current session
        exclude_set = set(exclude_items or []) | set(session_items)
        for item_id in exclude_set:
            if 0 <= item_id < self.config.n_items:
                scores[item_id] = -np.inf

        # Get top-N
        top_indices = np.argsort(scores)[::-1][:n_recommendations]
        recommendations = [
            (int(idx), float(scores[idx]))
            for idx in top_indices
            if scores[idx] > -np.inf
        ]

        return recommendations

    def update_session(self, session_id: str, item_id: int):
        """Update session with new interaction."""
        if session_id not in self.session_cache:
            self.session_cache[session_id] = []
        self.session_cache[session_id].append(item_id)

        # Keep session within max length
        if len(self.session_cache[session_id]) > self.config.max_session_length:
            self.session_cache[session_id] = self.session_cache[session_id][
                -self.config.max_session_length:
            ]

    def add_training_data(self, session: list[int], target: int):
        """Add training data for online learning."""
        self.interaction_buffer.append((session, target))

    def online_update(self):
        """Perform online update with buffered interactions."""
        if not self.interaction_buffer:
            return

        # Simple gradient update (in production, use proper optimizer)
        batch_size = min(len(self.interaction_buffer), self.config.batch_size)
        batch = self.interaction_buffer[:batch_size]
        self.interaction_buffer = self.interaction_buffer[batch_size:]

        for session, target in batch:
            scores, loss = self.encoder.forward([session], [target])
            # In production, implement backpropagation
            logger.debug(f"Online update loss: {loss:.4f}")

    def get_session_representation(self, session_id: str) -> np.ndarray | None:
        """Get the current representation of a session."""
        session_items = self.session_cache.get(session_id)
        if not session_items:
            return None
        return self.encoder.encode_session(session_items)

    def clear_session(self, session_id: str):
        """Clear a session."""
        if session_id in self.session_cache:
            del self.session_cache[session_id]

    def get_stats(self) -> dict[str, Any]:
        """Get session recommender statistics."""
        return {
            "active_sessions": len(self.session_cache),
            "buffered_interactions": len(self.interaction_buffer),
            "config": {
                "embedding_dim": self.config.embedding_dim,
                "hidden_dim": self.config.hidden_dim,
                "n_items": self.config.n_items,
                "max_session_length": self.config.max_session_length,
            },
        }


# Global session recommender
_session_recommender: SessionRecommender | None = None


def get_session_recommender() -> SessionRecommender:
    """Get the global session recommender."""
    global _session_recommender
    if _session_recommender is None:
        _session_recommender = SessionRecommender()
    return _session_recommender
