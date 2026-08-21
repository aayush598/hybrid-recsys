"""Dynamic hybrid weighting.

Combines collaborative-filtering, content-based and trending scores
with weights that adapt at prediction time to each signal's confidence
(catalogue coverage + score dispersion).
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

Scores = dict[int, float] | list[tuple[int, float]]


def _as_dict(scores: Scores | None) -> dict[int, float]:
    if not scores:
        return {}
    if isinstance(scores, dict):
        return {item: float(s) for item, s in scores.items()}
    return {int(item): float(s) for item, s in scores}


class DynamicHybrid:
    """Late-fusion hybrid whose weights adapt per request."""

    def __init__(self, cf_weight: float = 0.5, content_weight: float = 0.3,
                 trending_weight: float = 0.2):
        total = cf_weight + content_weight + trending_weight
        if total <= 0:
            raise ValueError("At least one weight must be positive")
        self.cf_weight = cf_weight / total
        self.content_weight = content_weight / total
        self.trending_weight = trending_weight / total

    @staticmethod
    def _confidence(scores: dict[int, float], max_size: int) -> float:
        """Confidence in [0, 1]: 50% catalogue coverage, 50% score dispersion."""
        if not scores or max_size == 0:
            return 0.0
        values = np.asarray(list(scores.values()), dtype=np.float64)
        coverage = len(values) / max_size
        spread = float(np.std(values)) if len(values) > 1 else 0.0
        dispersion = min(spread, 1.0)
        return float(0.5 * coverage + 0.5 * dispersion)

    def adjust_weights(self, cf_confidence: float, content_confidence: float) -> None:
        """Redistribute cf/content weight toward the more confident signal.

        The combined cf+content mass is kept constant, so the trending
        share is unaffected.
        """
        total_conf = cf_confidence + content_confidence
        pair_mass = self.cf_weight + self.content_weight
        if total_conf <= 0 or pair_mass <= 0:
            return
        self.cf_weight = pair_mass * (cf_confidence / total_conf)
        self.content_weight = pair_mass * (content_confidence / total_conf)
        logger.debug(
            "Adjusted weights: cf=%.3f content=%.3f trending=%.3f",
            self.cf_weight, self.content_weight, self.trending_weight,
        )

    def predict(
        self,
        cf_scores: Scores | None,
        content_scores: Scores | None,
        trending_scores: Scores | None,
        top_k: int = 20,
    ) -> list[tuple[int, float]]:
        """Fuse the three signals and return the top-K items."""
        cf = _as_dict(cf_scores)
        content = _as_dict(content_scores)
        trending = _as_dict(trending_scores)

        max_size = max(len(cf), len(content), len(trending))
        self.adjust_weights(
            self._confidence(cf, max_size),
            self._confidence(content, max_size),
        )

        combined: dict[int, float] = {}
        for item in set(cf) | set(content) | set(trending):
            combined[item] = (
                self.cf_weight * cf.get(item, 0.0)
                + self.content_weight * content.get(item, 0.0)
                + self.trending_weight * trending.get(item, 0.0)
            )
        ranked = sorted(combined.items(), key=lambda kv: kv[1], reverse=True)
        return ranked[:top_k]


__all__ = ["DynamicHybrid"]
