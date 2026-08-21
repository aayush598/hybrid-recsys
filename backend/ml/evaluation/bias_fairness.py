"""Bias and fairness detection for recommender systems.

Covers popularity bias (Gini), position bias, demographic parity, and an
aggregate fairness report across protected user groups.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from typing import Any, Sequence

import numpy as np

logger = logging.getLogger(__name__)


class BiasDetector:
    """Detect and quantify bias in recommendation outputs."""

    # ------------------------------------------------------------------ #
    # Popularity bias
    # ------------------------------------------------------------------ #
    @staticmethod
    def gini_coefficient(values: Sequence[float]) -> float:
        """Gini coefficient in [0, 1]; 0 = perfectly equal, 1 = maximally concentrated."""
        arr = np.sort(np.asarray(list(values), dtype=float))
        if arr.size == 0 or arr.sum() <= 0:
            return 0.0
        n = arr.size
        index = np.arange(1, n + 1)
        return float((2.0 * np.sum(index * arr)) / (n * np.sum(arr)) - (n + 1.0) / n)

    def popularity_bias(
        self,
        recommendations: Sequence[Sequence[Any]],
        item_popularity: dict[Any, float] | None = None,
    ) -> dict[str, float]:
        """Measure how concentrated recommended items are.

        ``item_popularity`` maps item_id -> popularity score. When omitted,
        popularity is estimated from the recommendations themselves.
        Returns the Gini coefficient of recommended-item popularity plus
        catalog coverage.
        """
        flat = [item for recs in recommendations for item in recs]
        if not flat:
            return {"gini_coefficient": 0.0, "coverage": 0.0, "unique_items": 0.0}

        counts: Counter[Any] = Counter(flat)
        if item_popularity:
            pop_values = [float(item_popularity.get(item, 0.0)) for item in flat]
            total_catalog = max(len(item_popularity), len(counts))
        else:
            pop_values = [float(c) for c in counts.values()]
            total_catalog = len(counts)

        gini = self.gini_coefficient(pop_values)
        coverage = len(counts) / total_catalog if total_catalog else 0.0
        result = {
            "gini_coefficient": gini,
            "coverage": float(coverage),
            "unique_items": float(len(counts)),
        }
        logger.info("Popularity bias: gini=%.3f coverage=%.3f", gini, coverage)
        return result

    # ------------------------------------------------------------------ #
    # Position bias
    # ------------------------------------------------------------------ #
    def position_bias(self, clicks_by_position: dict[int | str, int]) -> float:
        """Positional unfairness: normalized spread of CTR-like attention.

        ``clicks_by_position`` maps position -> click count. Returns a value
        in [0, 1] where 1 means clicks are maximally concentrated on early
        positions (strong position bias) and 0 means uniform distribution.
        """
        if not clicks_by_position:
            return 0.0
        positions = sorted(clicks_by_position.keys(), key=lambda p: int(p))
        values = np.asarray([float(clicks_by_position[p]) for p in positions], dtype=float)
        total = values.sum()
        if total <= 0 or len(values) < 2:
            return 0.0

        observed = values / total
        n = len(values)
        uniform = np.full(n, 1.0 / n)
        # Distance between observed attention and uniform attention,
        # normalized to [0, 1] by its theoretical maximum.
        raw = float(np.abs(observed - uniform).sum()) / 2.0
        max_raw = 1.0 - 1.0 / n
        unfairness = raw / max_raw if max_raw > 0 else 0.0

        # Monotonicity bonus: penalize when earlier positions dominate later ones.
        decay_violations = sum(
            1 for i in range(n - 1) if observed[i] < observed[i + 1]
        )
        monotonicity_penalty = decay_violations / (n - 1)
        return float(np.clip(0.5 * unfairness + 0.5 * monotonicity_penalty, 0.0, 1.0))

    # ------------------------------------------------------------------ #
    # Group fairness
    # ------------------------------------------------------------------ #
    @staticmethod
    def demographic_parity(predictions_by_group: dict[Any, Sequence[float]]) -> float:
        """Ratio of min/max positive-prediction rates across groups.

        A value of 1.0 indicates perfect parity; common thresholds treat
        >= 0.8 as acceptable (the "four-fifths rule").
        """
        rates: list[float] = []
        for preds in predictions_by_group.values():
            arr = np.asarray(list(preds), dtype=float)
            if arr.size == 0:
                continue
            rates.append(float((arr > 0).mean()))
        if len(rates) < 2:
            return 1.0
        max_rate, min_rate = max(rates), min(rates)
        if max_rate == 0:
            return 1.0
        return float(min_rate / max_rate)

    def equal_opportunity(
        self,
        predictions_by_group: dict[Any, Sequence[float]],
        labels_by_group: dict[Any, Sequence[float]],
    ) -> float:
        """Ratio of min/max true-positive rates across groups."""
        tprs: list[float] = []
        for group, preds in predictions_by_group.items():
            y_pred = np.asarray(list(preds), dtype=float) > 0
            y_true = np.asarray(list(labels_by_group.get(group, [])), dtype=float) > 0
            positives = y_true.sum()
            if positives == 0:
                continue
            tprs.append(float((y_pred & y_true).sum() / positives))
        if len(tprs) < 2:
            return 1.0
        return float(min(tprs) / max(tprs)) if max(tprs) > 0 else 1.0

    # ------------------------------------------------------------------ #
    # Aggregate report
    # ------------------------------------------------------------------ #
    def compute_fairness_metrics(
        self,
        recommendations: Sequence[Sequence[Any]],
        protected_groups: dict[Any, str],
        item_popularity: dict[Any, float] | None = None,
        relevance_by_user: dict[Any, Sequence[float]] | None = None,
    ) -> dict[str, Any]:
        """Aggregate fairness report across user groups.

        ``protected_groups`` maps user_id -> group label; positions in
        ``recommendations`` correspond to users via enumeration order.
        """
        group_recs: dict[str, list[list[Any]]] = defaultdict(list)
        for idx, recs in enumerate(recommendations):
            group = protected_groups.get(idx, "unknown")
            group_recs[group].append(list(recs))

        # Per-group exposure: share of recommendation slots each group receives.
        total_slots = sum(len(r) for r in recommendations) or 1
        exposure = {
            group: sum(len(r) for r in recs) / total_slots
            for group, recs in group_recs.items()
        }

        parity_ratio = (
            min(exposure.values()) / max(exposure.values())
            if exposure and max(exposure.values()) > 0
            else 1.0
        )

        # Per-group accuracy (precision proxy) when relevance labels supplied.
        group_precision: dict[str, float] = {}
        if relevance_by_user:
            for group, recs_list in group_recs.items():
                precisions = []
                for i, recs in enumerate(recs_list):
                    user_idx = [
                        j for j, g in enumerate(
                            [protected_groups.get(k, "unknown") for k in range(len(recommendations))]
                        ) if g == group
                    ]
                    if i < len(user_idx):
                        labels = relevance_by_user.get(user_idx[i])
                        if labels:
                            lab = np.asarray(list(labels), dtype=float)[: len(recs)]
                            if lab.size:
                                precisions.append(float((lab > 0).mean()))
                group_precision[group] = float(np.mean(precisions)) if precisions else 0.0

        pop_bias = self.popularity_bias(recommendations, item_popularity)

        report: dict[str, Any] = {
            "group_exposure": exposure,
            "exposure_parity_ratio": float(parity_ratio),
            "demographic_parity": parity_ratio,
            "popularity_bias": pop_bias,
            "n_groups": len(group_recs),
            "fair": bool(parity_ratio >= 0.8 and pop_bias["gini_coefficient"] < 0.8),
        }
        if group_precision:
            prec_values = list(group_precision.values())
            report["group_precision"] = group_precision
            report["equalized_accuracy_ratio"] = (
                min(prec_values) / max(prec_values) if max(prec_values) > 0 else 1.0
            )
        logger.info("Fairness report: parity=%.3f fair=%s", parity_ratio, report["fair"])
        return report
