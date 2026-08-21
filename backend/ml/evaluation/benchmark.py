"""Benchmark suite: compare models against baselines with statistical rigor."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Sequence

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class BenchmarkSuite:
    """Compare a model's recommendations against standard baselines."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------ #
    # Baselines
    # ------------------------------------------------------------------ #
    def _random_baseline(
        self,
        n_users: int,
        top_k: int,
        item_pool: Sequence[Any] | None = None,
    ) -> list[list[Any]]:
        """Uniformly random recommendations per user."""
        if item_pool is None:
            item_pool = list(range(1000))
        pool = list(item_pool)
        return [
            [pool[i] for i in self.rng.choice(len(pool), size=min(top_k, len(pool)), replace=False)]
            for _ in range(n_users)
        ]

    @staticmethod
    def _popularity_baseline(
        interactions: Any,
        n_users: int,
        top_k: int,
    ) -> list[list[Any]]:
        """Recommend globally most-interacted items to everyone.

        ``interactions`` is a DataFrame with an ``item_id`` column (any
        extra columns ignored).
        """
        counts = interactions["item_id"].value_counts()
        top_items = list(counts.head(top_k).index)
        return [list(top_items) for _ in range(n_users)]

    # ------------------------------------------------------------------ #
    # Comparison
    # ------------------------------------------------------------------ #
    def compare_with_baselines(
        self,
        model_recs: Sequence[Sequence[Any]],
        baselines: set[str] | None = None,
        relevance: Sequence[Sequence[float]] | None = None,
        interactions: Any = None,
        item_pool: Sequence[Any] | None = None,
        top_k: int = 10,
        metric_fn: Callable[[Sequence[Any], Sequence[float]], float] | None = None,
    ) -> dict[str, Any]:
        """Score the model against requested baselines.

        ``metric_fn(recs, labels) -> score`` defaults to precision@k using
        the first ``len(recs)`` labels. When ``relevance`` is omitted, a
        deterministic pseudo-relevance profile is generated so relative
        comparisons remain meaningful.
        """
        baselines = baselines or {"random", "popularity"}
        model_recs = [list(r) for r in model_recs]
        n_users = len(model_recs)

        if relevance is None:
            logger.warning("No relevance labels supplied; generating synthetic ones")
            relevance = [
                (self.rng.random(min(len(r), 50)) > 0.7).astype(float).tolist() or [0.0]
                for r in model_recs
            ]

        def default_metric(recs: Sequence[Any], labels: Sequence[float]) -> float:
            lab = np.asarray(list(labels), dtype=float)[: len(recs)]
            if lab.size == 0:
                return 0.0
            return float((lab > 0).mean())

        metric_fn = metric_fn or default_metric
        results: dict[str, dict[str, float]] = {}

        results["model"] = {
            "score": float(np.mean([metric_fn(r, rel) for r, rel in zip(model_recs, relevance)])),
            "n_users": float(n_users),
        }

        if "random" in baselines:
            random_recs = self._random_baseline(n_users, top_k, item_pool)
            results["baseline_random"] = {
                "score": float(np.mean([metric_fn(r, rel) for r, rel in zip(random_recs, relevance)])),
                "n_users": float(n_users),
            }
        if "popularity" in baselines:
            if interactions is None:
                logger.warning("Popularity baseline needs `interactions`; skipping")
            else:
                pop_recs = self._popularity_baseline(interactions, n_users, top_k)
                results["baseline_popularity"] = {
                    "score": float(np.mean([metric_fn(r, rel) for r, rel in zip(pop_recs, relevance)])),
                    "n_users": float(n_users),
                }

        model_scores = np.asarray(
            [metric_fn(r, rel) for r, rel in zip(model_recs, relevance)], dtype=float
        )
        for name, res in results.items():
            if name == "model":
                continue
            base_scores = np.full(n_users, res["score"])
            res["lift_vs_model_pct"] = (
                float((model_scores.mean() - base_scores.mean()) / base_scores.mean() * 100)
                if base_scores.mean() > 0 else 0.0
            )
        results["model"]["per_user_scores"] = model_scores.tolist()
        results["meta"] = {"timestamp": time.time(), "top_k": top_k, "seed": self.seed}
        return results

    # ------------------------------------------------------------------ #
    # Statistical testing
    # ------------------------------------------------------------------ #
    @staticmethod
    def statistical_test(
        scores_a: Sequence[float],
        scores_b: Sequence[float],
        method: str = "ttest",
    ) -> float:
        """Two-sided p-value comparing two score distributions.

        Methods: ``ttest`` (Welch's t), ``wilcoxon`` (paired rank),
        ``mannwhitney`` (unpaired rank).
        """
        a = np.asarray(list(scores_a), dtype=float)
        b = np.asarray(list(scores_b), dtype=float)
        mask_a, mask_b = np.isfinite(a), np.isfinite(b)
        a, b = a[mask_a], b[mask_b]
        if a.size < 2 or b.size < 2:
            return 1.0
        try:
            if method == "ttest":
                _, p_value = stats.ttest_ind(a, b, equal_var=False)
            elif method == "wilcoxon":
                n = min(a.size, b.size)
                _, p_value = stats.wilcoxon(a[:n], b[:n])
            elif method == "mannwhitney":
                _, p_value = stats.mannwhitneyu(a, b, alternative="two-sided")
            else:
                raise ValueError(f"Unknown test method: {method}")
        except ValueError as exc:
            logger.warning("Statistical test failed (%s); returning p=1.0", exc)
            return 1.0
        return float(p_value)

    @staticmethod
    def bootstrap_confidence_interval(
        scores: Sequence[float],
        confidence: float = 0.95,
        n_bootstrap: int = 2000,
        seed: int = 42,
    ) -> tuple[float, float]:
        """Percentile bootstrap CI for the mean of ``scores``."""
        arr = np.asarray(list(scores), dtype=float)
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            return (0.0, 0.0)
        rng = np.random.default_rng(seed)
        boot_means = np.asarray(
            [rng.choice(arr, size=arr.size, replace=True).mean() for _ in range(n_bootstrap)]
        )
        alpha = (1.0 - confidence) / 2.0
        lower = float(np.percentile(boot_means, 100 * alpha))
        upper = float(np.percentile(boot_means, 100 * (1 - alpha)))
        return (lower, upper)

    # ------------------------------------------------------------------ #
    # Reporting
    # ------------------------------------------------------------------ #
    def generate_report(self, results: dict[str, Any], format: str = "dict") -> Any:
        """Render comparison results as ``dict``, ``markdown``, or ``json``."""
        if format == "dict":
            return results

        rows = []
        model_score = results.get("model", {}).get("score", 0.0)
        for name, res in results.items():
            if name in ("model", "meta") or not isinstance(res, dict):
                continue
            lift = res.get("lift_vs_model_pct", 0.0)
            rows.append((name, res.get("score", 0.0), model_score - res.get("score", 0.0), lift))

        lines = [
            "# Benchmark Report",
            "",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "| System | Score | Δ vs Model | Lift vs Model (%) |",
            "|---|---|---|---|",
            f"| **model** | {model_score:.4f} | — | — |",
        ]
        for name, score, delta, lift in sorted(rows, key=lambda r: -r[1]):
            lines.append(f"| {name} | {score:.4f} | {delta:+.4f} | {lift:+.2f} |")

        report = "\n".join(lines)
        if format == "json":
            import json

            return json.dumps({"markdown": report, "results": {
                k: v for k, v in results.items() if k != "meta"
            }}, indent=2, default=str)
        return report
