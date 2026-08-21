"""Multi-objective hybrid recommendation.

Optimizes relevance, diversity and novelty simultaneously via greedy
weighted selection over a Pareto-aware candidate set.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable

logger = logging.getLogger(__name__)

DEFAULT_OBJECTIVES = ["relevance", "diversity", "novelty"]


def _normalize_predictions(predictions) -> dict:
    """Accept dicts, (item_id, score) tuples or bare ids."""
    out: dict = {}
    for pred in predictions or []:
        if isinstance(pred, dict):
            out[pred.get("item_id")] = float(pred.get("score", 0.0))
        elif isinstance(pred, (tuple, list)) and len(pred) >= 2:
            out[pred[0]] = float(pred[1])
        else:
            out[pred] = 0.0
    return out


class MultiObjectiveHybrid:
    """Hybrid recommender balancing multiple objectives at once."""

    def __init__(
        self,
        models: list[Callable] | None = None,
        objectives: list[str] | None = None,
    ):
        self.models = list(models or [])
        self.objectives = list(objectives or DEFAULT_OBJECTIVES)
        for obj in self.objectives:
            if obj not in DEFAULT_OBJECTIVES:
                raise ValueError(f"Unsupported objective: {obj!r}")

    @staticmethod
    def _genre(item: dict) -> str:
        return str(item.get("genre") or item.get("category") or item.get("item_id"))

    def _objective_vector(
        self,
        item_id,
        model_scores: dict,
        popularity: dict,
        selected_genres: list[str],
    ) -> dict[str, float]:
        """Compute the objective values for one candidate."""
        relevance = model_scores.get(item_id, 0.0)

        if selected_genres:
            same_genre_ratio = selected_genres.count(self._genre(popularity.get(item_id, {}))) / len(
                selected_genres
            )
            diversity = 1.0 - same_genre_ratio
        else:
            diversity = 1.0

        pop = popularity.get(item_id, {})
        pop_count = float(pop.get("popularity", 0.0))
        novelty = 1.0 / (1.0 + math.log1p(max(pop_count, 0.0)))

        return {"relevance": relevance, "diversity": diversity, "novelty": novelty}

    def predict(
        self,
        user_id: str,
        top_k: int = 20,
        objective_weights: dict[str, float] | None = None,
    ) -> list[tuple]:
        """Greedy multi-objective selection of the top-K items."""
        weights = {obj: 1.0 for obj in self.objectives}
        if objective_weights:
            weights.update(objective_weights)
        total_w = sum(weights.values()) or 1.0

        per_model: list[dict] = []
        for model in self.models:
            try:
                per_model.append(_normalize_predictions(model.predict(user_id, top_k * 3)))
            except AttributeError:
                per_model.append({})
            except Exception:
                logger.exception("Model %r failed", model)
                per_model.append({})

        candidates: set = set()
        for scores in per_model:
            candidates.update(scores.keys())
        if not candidates:
            return []

        # Aggregate relevance across models; use max frequency as popularity proxy.
        model_scores: dict = {}
        freq: dict = {}
        for scores in per_model:
            for item, score in scores.items():
                model_scores[item] = max(model_scores.get(item, 0.0), score)
                freq[item] = freq.get(item, 0) + 1
        popularity = {
            item: {"popularity": count, "item_id": item} for item, count in freq.items()
        }

        remaining = set(candidates)
        selected: list[tuple] = []
        selected_genres: list[str] = []
        while remaining and len(selected) < top_k:
            best_item, best_value = None, -math.inf
            for item in remaining:
                vec = self._objective_vector(
                    item, model_scores, popularity, selected_genres
                )
                value = sum(weights[obj] * vec[obj] for obj in self.objectives) / total_w
                if value > best_value:
                    best_item, best_value = item, value
            selected.append((best_item, round(best_value, 6)))
            selected_genres.append(str(best_item))
            remaining.discard(best_item)
        return selected

    @staticmethod
    def pareto_front(candidates: list[dict]) -> list[dict]:
        """Return the non-dominated candidates.

        Each candidate must expose its objective values either as a
        ``scores``/``objectives`` dict or directly as objective keys.
        A candidate dominates another when it is >= on every objective
        and strictly > on at least one (maximization).
        """

        def vector(cand: dict) -> tuple[float, ...]:
            src = cand.get("scores") or cand.get("objectives") or cand
            return tuple(float(src.get(obj, 0.0)) for obj in DEFAULT_OBJECTIVES)

        front: list[dict] = []
        for cand in candidates:
            v = vector(cand)
            dominated = False
            for other in candidates:
                if other is cand:
                    continue
                w = vector(other)
                if all(wi >= vi for wi, vi in zip(w, v)) and any(
                    wi > vi for wi, vi in zip(w, v)
                ):
                    dominated = True
                    break
            if not dominated:
                front.append(cand)
        return front


__all__ = ["MultiObjectiveHybrid"]
