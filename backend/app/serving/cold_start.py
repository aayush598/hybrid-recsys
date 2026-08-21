"""Cold start handling for new users and items."""

from __future__ import annotations

import random
from typing import Any

import numpy as np


class ColdStartHandler:
    """Handle cold start problems for new users and items."""

    def new_user_recommendations(
        self, popular_items: list[tuple[int, float]] | None = None, num_recs: int = 10
    ) -> list[tuple[int, float]]:
        """Return popular items as recommendations for new users."""
        if not popular_items:
            return []
        return popular_items[:num_recs]

    def onboarding_survey(
        self, genres: list[str], sample_size: int = 10
    ) -> dict[str, Any]:
        """Generate onboarding survey questions for new users."""
        if not genres:
            return {"questions": []}

        selected = random.sample(genres, min(sample_size, len(genres)))
        questions = []
        for i, genre in enumerate(selected):
            questions.append({
                "question_id": i,
                "question": f"Do you enjoy {genre} movies?",
                "genre": genre,
                "options": [
                    {"label": "Love it", "value": "love", "weight": 1.0},
                    {"label": "Like it", "value": "like", "weight": 0.7},
                    {"label": "Neutral", "value": "neutral", "weight": 0.3},
                    {"label": "Not for me", "value": "dislike", "weight": 0.0},
                ],
            })

        return {"questions": questions, "total_questions": len(questions)}

    def process_onboarding_responses(
        self, responses: list[dict], genre_mapping: dict[str, float] | None = None
    ) -> dict[str, Any]:
        """Process onboarding survey responses into a user profile."""
        if genre_mapping is None:
            genre_mapping = {
                "love": 1.0, "like": 0.7, "neutral": 0.3, "dislike": 0.0
            }

        genre_preferences = {}
        for resp in responses:
            genre = resp.get("genre", "unknown")
            value = resp.get("value", "neutral")
            weight = genre_mapping.get(value, 0.3)
            genre_preferences[genre] = weight

        total_weight = sum(genre_preferences.values()) or 1.0
        normalized = {k: v / total_weight for k, v in genre_preferences.items()}

        return {
            "genre_preferences": normalized,
            "favorite_genres": [g for g, w in sorted(normalized.items(), key=lambda x: -x[1])[:3]],
            "profile_completeness": len(responses) / 10.0,
        }

    def content_based_fallback(
        self,
        new_item_features: dict[str, float],
        existing_item_features: list[dict[str, float]],
        top_k: int = 10,
    ) -> list[tuple[int, float]]:
        """Find similar items to a new item using content features."""
        if not existing_item_features:
            return []

        new_vec = np.array(list(new_item_features.values()), dtype=float)
        new_norm = np.linalg.norm(new_vec)

        similarities = []
        for i, item_features in enumerate(existing_item_features):
            item_vec = np.array(list(item_features.values()), dtype=float)
            item_norm = np.linalg.norm(item_vec)
            if new_norm > 0 and item_norm > 0:
                sim = float(np.dot(new_vec, item_vec) / (new_norm * item_norm))
            else:
                sim = 0.0
            similarities.append((i, sim))

        similarities.sort(key=lambda x: -x[1])
        return similarities[:top_k]

    def epsilon_greedy_explore(
        self,
        user_id: str | int,
        known_items: set[int],
        all_items: list[int],
        epsilon: float = 0.1,
    ) -> list[tuple[int, float]]:
        """Epsilon-greedy exploration: mostly exploit known preferences, occasionally explore."""
        if not all_items:
            return []

        if random.random() < epsilon:
            unseen = [item for item in all_items if item not in known_items]
            if unseen:
                explore_items = random.sample(unseen, min(5, len(unseen)))
                return [(item, 1.0) for item in explore_items]
            return [(random.choice(all_items), 1.0)]

        return [(item, 0.5) for item in list(known_items)[:5]] if known_items else []
