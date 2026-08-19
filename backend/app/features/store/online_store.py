from __future__ import annotations

import time
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class FeatureStore:
    """Online feature store for real-time feature serving.

    Architecture inspired by Feast (https://feast.dev/):
    - Online store: fast reads (<10ms) for real-time serving
    - Offline store: batch features for training
    - Feature registry: metadata about available features

    In production, this would use Redis Cluster or DynamoDB.
    For this demo, we use in-memory dict with TTL support.
    """

    def __init__(self):
        self._store: dict[str, tuple[float, Any]] = {}
        self._feature_registry: dict[str, dict] = {}

    def register_feature(
        self,
        name: str,
        dtype: str,
        description: str = "",
        ttl: int = 3600,
    ) -> None:
        """Register a feature in the feature store."""
        self._feature_registry[name] = {
            "dtype": dtype,
            "description": description,
            "ttl": ttl,
        }

    def get_online_features(
        self,
        entity_key: str,
        feature_names: list[str],
    ) -> dict[str, Any]:
        """Get features from online store.

        Args:
            entity_key: e.g., "user:123" or "item:456"
            feature_names: list of feature names to retrieve

        Returns:
            Dict mapping feature names to values
        """
        result = {}
        for name in feature_names:
            full_key = f"{entity_key}:{name}"
            if full_key in self._store:
                timestamp, value = self._store[full_key]
                ttl = self._feature_registry.get(name, {}).get("ttl", settings.FEATURE_STORE_ONLINE_TTL)
                if time.time() - timestamp < ttl:
                    result[name] = value
                else:
                    del self._store[full_key]
            else:
                result[name] = None
        return result

    def set_online_features(
        self,
        entity_key: str,
        features: dict[str, Any],
    ) -> None:
        """Write features to online store."""
        timestamp = time.time()
        for name, value in features.items():
            full_key = f"{entity_key}:{name}"
            self._store[full_key] = (timestamp, value)

    def get_user_features(self, user_id: str) -> dict[str, Any]:
        """Get all features for a user."""
        return self.get_online_features(f"user:{user_id}", [
            "avg_rating", "rating_count", "favorite_genres",
            "recent_activity", "engagement_score", "segment",
        ])

    def set_user_features(self, user_id: str, features: dict[str, Any]) -> None:
        """Write user features."""
        self.set_online_features(f"user:{user_id}", features)

    def get_item_features(self, item_id: str) -> dict[str, Any]:
        """Get all features for an item."""
        return self.get_online_features(f"item:{item_id}", [
            "avg_rating", "rating_count", "popularity_score",
            "genre_vector", "freshness_score", "content_embedding",
        ])

    def set_item_features(self, item_id: str, features: dict[str, Any]) -> None:
        """Write item features."""
        self.set_online_features(f"item:{item_id}", features)

    def get_context_features(self, context_key: str) -> dict[str, Any]:
        """Get context features (time of day, device, etc.)."""
        return self.get_online_features(f"context:{context_key}", [
            "hour_of_day", "day_of_week", "device_type",
            "session_length", "is_returning_user",
        ])

    def set_context_features(self, context_key: str, features: dict[str, Any]) -> None:
        """Write context features."""
        self.set_online_features(f"context:{context_key}", features)

    def bulk_get(
        self, entity_keys: list[str], feature_names: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Bulk feature retrieval for efficient batch serving."""
        return {
            key: self.get_online_features(key, feature_names) for key in entity_keys
        }

    def compute_user_features_from_history(
        self, user_id: str, ratings: list[dict]
    ) -> dict[str, Any]:
        """Compute user features from their rating history."""
        if not ratings:
            return {
                "avg_rating": 0.0,
                "rating_count": 0,
                "favorite_genres": [],
                "engagement_score": 0.0,
                "segment": "new",
            }

        avg_rating = sum(r["rating"] for r in ratings) / len(ratings)
        rating_count = len(ratings)

        genre_counts: dict[str, int] = {}
        for r in ratings:
            for genre in r.get("genres", "").split("|"):
                if genre:
                    genre_counts[genre] = genre_counts.get(genre, 0) + 1

        favorite_genres = sorted(genre_counts.keys(), key=lambda g: genre_counts[g], reverse=True)[:5]

        engagement_score = min(rating_count / 100.0, 1.0)

        if rating_count >= 50:
            segment = "power_user"
        elif rating_count >= 10:
            segment = "active"
        elif rating_count >= 1:
            segment = "casual"
        else:
            segment = "new"

        return {
            "avg_rating": avg_rating,
            "rating_count": rating_count,
            "favorite_genres": favorite_genres,
            "engagement_score": engagement_score,
            "segment": segment,
        }

    def cleanup_expired(self) -> int:
        """Remove expired features from store."""
        now = time.time()
        expired_keys = []
        for key, (timestamp, _) in self._store.items():
            if now - timestamp > settings.FEATURE_STORE_ONLINE_TTL:
                expired_keys.append(key)
        for key in expired_keys:
            del self._store[key]
        return len(expired_keys)

    @property
    def stats(self) -> dict:
        return {
            "total_features": len(self._store),
            "registered_features": len(self._feature_registry),
        }


feature_store = FeatureStore()
