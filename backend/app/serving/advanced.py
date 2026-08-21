"""Advanced serving components: batch processing, A/B analysis,
cold-start handling, and feedback loops.

Extends :mod:`app.serving.batch` and :mod:`app.serving.ab_testing` with:

- :class:`AdvancedBatchProcessor`: concurrent, retrying batch execution.
- :class:`ABTestAnalyzer`: statistical significance testing for experiments.
- :class:`ColdStartHandler`: fallback strategies for new users/items.
- :class:`FeedbackLoop`: feedback aggregation with retraining triggers.
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from scipy import stats

logger = logging.getLogger(__name__)


class AdvancedBatchProcessor:
    """Concurrent batch execution with retries and progress reporting."""

    def __init__(
        self,
        max_concurrency: int = 4,
        batch_size: int = 10,
        max_retries: int = 2,
        retry_delay: float = 0.01,
    ):
        if max_concurrency < 1 or batch_size < 1 or max_retries < 0:
            raise ValueError("max_concurrency/batch_size must be >= 1, max_retries >= 0")
        self.max_concurrency = max_concurrency
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.stats: dict[str, int] = {
            "total": 0,
            "succeeded": 0,
            "failed": 0,
            "retries": 0,
        }

    async def _run_one(self, fn: Callable, item: Any) -> Any:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                result = fn(item)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            except Exception as exc:  # noqa: BLE001 - retry any failure
                last_error = exc
                if attempt < self.max_retries:
                    self.stats["retries"] += 1
                    await asyncio.sleep(self.retry_delay)
        logger.error("Item failed after %d attempts: %r", self.max_retries + 1, last_error)
        raise last_error  # type: ignore[misc]

    async def process(
        self,
        items: Sequence[Any],
        fn: Callable,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[Any]:
        """Process all items concurrently in batches, preserving order.

        Failed items produce ``None`` at their position instead of raising.
        """
        semaphore = asyncio.Semaphore(self.max_concurrency)
        self.stats = {"total": len(items), "succeeded": 0, "failed": 0, "retries": 0}

        async def worker(item: Any) -> Any:
            async with semaphore:
                try:
                    return await self._run_one(fn, item)
                except Exception:  # noqa: BLE001
                    return None

        results: list[Any] = []
        completed = 0
        for start in range(0, len(items), self.batch_size):
            chunk = list(items[start : start + self.batch_size])
            results.extend(await asyncio.gather(*(worker(item) for item in chunk)))
            completed += len(chunk)
            if on_progress is not None:
                on_progress(completed, len(items))
        self.stats["succeeded"] = sum(1 for r in results if r is not None)
        self.stats["failed"] = self.stats["total"] - self.stats["succeeded"]
        return results


@dataclass
class VariantResult:
    """Aggregated outcome for one experiment variant."""

    name: str
    conversions: int
    exposures: int

    @property
    def rate(self) -> float:
        return self.conversions / self.exposures if self.exposures else 0.0


class ABTestAnalyzer:
    """Statistical analysis of A/B test outcomes (frequentist)."""

    @staticmethod
    def two_proportion_z_test(
        conversions_a: int, exposures_a: int,
        conversions_b: int, exposures_b: int,
    ) -> dict[str, float]:
        """Two-sided z-test comparing two conversion rates."""
        if min(exposures_a, exposures_b) <= 0:
            raise ValueError("Exposure counts must be positive")
        p_a = conversions_a / exposures_a
        p_b = conversions_b / exposures_b
        pooled = (conversions_a + conversions_b) / (exposures_a + exposures_b)
        se = math.sqrt(pooled * (1 - pooled) * (1 / exposures_a + 1 / exposures_b))
        z_score = (p_b - p_a) / se if se > 0 else 0.0
        p_value = float(2 * stats.norm.sf(abs(z_score)))
        return {
            "rate_a": p_a,
            "rate_b": p_b,
            "difference": p_b - p_a,
            "z_score": z_score,
            "p_value": p_value,
        }

    @staticmethod
    def proportion_confidence_interval(
        successes: int, n: int, confidence: float = 0.95
    ) -> tuple[float, float]:
        """Wald confidence interval for a binomial proportion."""
        if n <= 0:
            return (0.0, 0.0)
        p = successes / n
        z = float(stats.norm.ppf(1 - (1 - confidence) / 2))
        half_width = z * math.sqrt(p * (1 - p) / n)
        return (max(0.0, p - half_width), min(1.0, p + half_width))

    def analyze(
        self,
        variant_results: dict[str, tuple[int, int]],
        control: str = "control",
        alpha: float = 0.05,
    ) -> dict[str, Any]:
        """Compare every variant against the control arm.

        ``variant_results`` maps variant name -> (conversions, exposures).
        Returns per-variant rates, lift, p-values, and an overall winner
        (best rate among variants significantly better than control).
        """
        if control not in variant_results:
            raise KeyError(f"Control arm {control!r} missing from results")
        control_conv, control_exp = variant_results[control]
        report: dict[str, Any] = {"control": control, "alpha": alpha, "variants": {}}
        winner: str | None = None
        best_rate = -1.0
        for name, (conversions, exposures) in variant_results.items():
            entry: dict[str, Any] = {
                "conversions": conversions,
                "exposures": exposures,
                "rate": conversions / exposures if exposures else 0.0,
            }
            entry["ci_95"] = self.proportion_confidence_interval(conversions, exposures)
            if name != control:
                test = self.two_proportion_z_test(
                    control_conv, control_exp, conversions, exposures
                )
                entry["p_value"] = test["p_value"]
                entry["significant"] = bool(test["p_value"] < alpha)
                entry["lift_pct"] = (
                    (entry["rate"] - test["rate_a"]) / test["rate_a"] * 100
                    if test["rate_a"] > 0 else 0.0
                )
                if entry["significant"] and entry["rate"] > best_rate:
                    best_rate, winner = entry["rate"], name
            report["variants"][name] = entry
        report["winner"] = winner
        return report


@dataclass
class FeedbackEvent:
    """A single user feedback signal."""

    user_id: str
    item_id: Any
    event_type: str  # click | like | dislike | skip | purchase
    value: float = 0.0
    timestamp: float = field(default_factory=time.time)


class ColdStartHandler:
    """Recommendation strategies for new users and new items."""

    POSITIVE_EVENTS = {"click", "like", "purchase"}

    def __init__(self, epsilon: float = 0.2, seed: int = 42):
        if not 0.0 <= epsilon <= 1.0:
            raise ValueError("epsilon must be in [0, 1]")
        self.epsilon = epsilon
        self.rng = random.Random(seed)

    def recommend_for_new_user(
        self,
        popularity: list[tuple[Any, float]],
        genre_preferences: dict[str, float] | None = None,
        item_genres: dict[Any, str] | None = None,
        top_k: int = 10,
    ) -> list[tuple[Any, float]]:
        """Popularity prior blended with optional onboarding genre affinities."""
        scored: list[tuple[Any, float]] = []
        max_pop = max((score for _, score in popularity), default=0.0) or 1.0
        for item_id, pop_score in popularity:
            score = 0.5 * pop_score / max_pop
            if genre_preferences and item_genres:
                genres = str(item_genres.get(item_id, "")).split("|")
                affinity = max(
                    (genre_preferences.get(g, 0.0) for g in genres), default=0.0
                )
                score += 0.5 * affinity
            scored.append((item_id, round(score, 6)))
        scored.sort(key=lambda kv: kv[1], reverse=True)
        return scored[:top_k]

    def recommend_for_new_item(
        self,
        item_genres: str,
        catalog_genres: dict[Any, str],
        top_k: int = 10,
    ) -> list[tuple[Any, float]]:
        """Content-similar neighbors for a brand-new item (genre overlap)."""
        wanted = set(filter(None, item_genres.split("|")))
        scored: list[tuple[Any, float]] = []
        for other_id, other_genres in catalog_genres.items():
            overlap = len(wanted & set(filter(None, str(other_genres).split("|"))))
            if overlap:
                scored.append((other_id, overlap))
        scored.sort(key=lambda kv: kv[1], reverse=True)
        return scored[:top_k]

    def select_action(self, scores: dict[str, float]) -> str:
        """Epsilon-greedy exploration over candidate scores."""
        if not scores:
            raise ValueError("scores must not be empty")
        if self.rng.random() < self.epsilon:
            return self.rng.choice(list(scores.keys()))
        return max(scores, key=scores.get)  # type: ignore[arg-type]


class FeedbackLoop:
    """Aggregates feedback events and signals when retraining is due."""

    NEGATIVE_EVENTS = {"dislike", "skip"}
    POSITIVE_EVENTS = {"click", "like", "purchase"}

    def __init__(
        self,
        min_events: int = 20,
        negative_rate_threshold: float = 0.5,
        absolute_event_threshold: int = 10_000,
    ):
        self.min_events = min_events
        self.negative_rate_threshold = negative_rate_threshold
        self.absolute_event_threshold = absolute_event_threshold
        self.events: list[FeedbackEvent] = []

    def record(
        self,
        event_type: str,
        user_id: str = "anonymous",
        item_id: Any = None,
        value: float = 0.0,
    ) -> FeedbackEvent:
        """Append one feedback event to the loop buffer."""
        event = FeedbackEvent(
            user_id=user_id, item_id=item_id, event_type=event_type, value=value
        )
        self.events.append(event)
        return event

    def stats(self) -> dict[str, Any]:
        """Aggregate counts plus positive/negative/CTR-style rates."""
        counts = Counter(e.event_type for e in self.events)
        total = len(self.events)
        negatives = sum(counts[e] for e in self.NEGATIVE_EVENTS)
        positives = sum(counts[e] for e in self.POSITIVE_EVENTS)
        impressions = counts.get("impression", total) or 1
        return {
            "total": total,
            "counts": dict(counts),
            "positive_rate": positives / total if total else 0.0,
            "negative_rate": negatives / total if total else 0.0,
            "ctr": counts.get("click", 0) / impressions,
        }

    def should_retrain(self) -> bool:
        """True when enough events accumulated or negativity exceeds budget."""
        stats = self.stats()
        if stats["total"] >= self.absolute_event_threshold:
            return True
        if stats["total"] < self.min_events:
            return False
        return stats["negative_rate"] > self.negative_rate_threshold

    def drain(self) -> list[FeedbackEvent]:
        """Return buffered events and clear the buffer."""
        drained, self.events = self.events, []
        return drained


__all__ = [
    "ABTestAnalyzer",
    "AdvancedBatchProcessor",
    "ColdStartHandler",
    "FeedbackEvent",
    "FeedbackLoop",
]
