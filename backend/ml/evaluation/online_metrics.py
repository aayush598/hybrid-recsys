"""Online (post-deployment) metrics: CTR, conversion, session depth,
retention, and revenue tracking."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class OnlineMetricsState:
    """Accumulated counters for streaming metric computation."""
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue: float = 0.0
    events: list[dict[str, Any]] = field(default_factory=list)


class OnlineMetrics:
    """Track business/product metrics for a live recommendation system.

    All ``track_*`` methods are pure functions over the provided data;
    the class additionally maintains running counters via :meth:`record`
    for streaming-style aggregation.
    """

    def __init__(self) -> None:
        self.state = OnlineMetricsState()
        self._revenue_by_user: dict[Any, float] = defaultdict(float)
        self._orders_by_user: dict[Any, int] = defaultdict(int)

    # ------------------------------------------------------------------ #
    # Engagement
    # ------------------------------------------------------------------ #
    @staticmethod
    def track_ctr(impressions: int | Sequence[int], clicks: int | Sequence[int]) -> float:
        """Click-through rate = clicks / impressions (safe against div-by-zero)."""
        if isinstance(impressions, Sequence):
            imp_total = float(np.sum(impressions))
            click_total = float(np.sum(clicks))
        else:
            imp_total, click_total = float(impressions), float(clicks)
        if imp_total <= 0:
            return 0.0
        return click_total / imp_total

    @staticmethod
    def track_conversion(conversions: int | Sequence[int], total: int | Sequence[int]) -> float:
        """Conversion rate = conversions / total opportunities."""
        total_val = float(np.sum(total)) if isinstance(total, Sequence) else float(total)
        conv_val = float(np.sum(conversions)) if isinstance(conversions, Sequence) else float(conversions)
        if total_val <= 0:
            return 0.0
        return conv_val / total_val

    @staticmethod
    def track_session_depth(session_lengths: Sequence[float]) -> dict[str, float]:
        """Session depth stats: mean plus p50/p95 percentiles."""
        arr = np.asarray(list(session_lengths), dtype=float)
        if arr.size == 0:
            return {"avg": 0.0, "p50": 0.0, "p95": 0.0, "count": 0.0}
        return {
            "avg": float(arr.mean()),
            "p50": float(np.percentile(arr, 50)),
            "p95": float(np.percentile(arr, 95)),
            "count": float(arr.size),
        }

    # ------------------------------------------------------------------ #
    # Retention
    # ------------------------------------------------------------------ #
    @staticmethod
    def track_retention(
        user_activity: dict[Any, Iterable[int]],
        days: Sequence[int] = (1, 7, 30),
    ) -> dict[str, float]:
        """Classic D{1,7,30} retention.

        ``user_activity`` maps user_id -> iterable of day-offsets (int days
        since signup) on which the user was active. A user counts as
        retained on day N if they were active on or after day N.
        """
        activity = {u: set(int(d) for d in offs) for u, offs in user_activity.items()}
        n_users = len(activity)
        result: dict[str, float] = {"total_users": float(n_users)}
        for n in days:
            retained = sum(1 for offs in activity.values() if any(o >= n for o in offs))
            result[f"day_{n}"] = retained / n_users if n_users else 0.0
        return result

    # ------------------------------------------------------------------ #
    # Revenue
    # ------------------------------------------------------------------ #
    @staticmethod
    def track_revenue(revenue_data: Sequence[float] | dict[str, Any]) -> dict[str, float]:
        """Revenue health metrics.

        Accepts either a flat sequence of order values (computes CLV proxy,
        AOV) or a dict with optional keys:

        - ``orders``: per-order values -> CLV proxy + AOV
        - ``monthly_revenue``: sequence of monthly totals -> MRR + churn trend
        - ``lifespans``: per-customer active months -> CLV = AOV * freq * lifespan
        """
        if isinstance(revenue_data, dict):
            orders = np.asarray(revenue_data.get("orders", []), dtype=float)
            monthly = np.asarray(revenue_data.get("monthly_revenue", []), dtype=float)
            lifespans = np.asarray(revenue_data.get("lifespans", []), dtype=float)
        else:
            orders = np.asarray(list(revenue_data), dtype=float)
            monthly = np.asarray([], dtype=float)
            lifespans = np.asarray([], dtype=float)

        result: dict[str, float] = {}
        if orders.size:
            aov = float(orders.mean())
            result["aov"] = aov
            result["total_revenue"] = float(orders.sum())
            result["order_count"] = float(orders.size)
            # CLV proxy: average order value x observed purchase frequency
            result["clv"] = aov * max(orders.size, 1)
        if lifespans.size:
            avg_life = float(lifespans.mean())
            result["avg_lifespan_months"] = avg_life
            if orders.size:
                result["clv"] = result.get("aov", 0.0) * avg_life
        if monthly.size:
            result["mrr"] = float(monthly[-1])
            if monthly.size >= 2:
                prev = float(monthly[-2])
                result["mrr_growth"] = (
                    (result["mrr"] - prev) / prev if prev > 0 else 0.0
                )
        if not result:
            result = {"clv": 0.0, "aov": 0.0, "mrr": 0.0}
        return result

    # ------------------------------------------------------------------ #
    # Streaming-style accumulation
    # ------------------------------------------------------------------ #
    def record(
        self,
        event_type: str,
        user_id: Any = None,
        item_id: Any = None,
        value: float = 0.0,
    ) -> None:
        """Record one live event (impression/click/conversion/purchase)."""
        self.state.events.append(
            {"type": event_type, "user_id": user_id, "item_id": item_id, "value": value}
        )
        if event_type == "impression":
            self.state.impressions += 1
        elif event_type == "click":
            self.state.clicks += 1
        elif event_type in ("conversion", "purchase"):
            self.state.conversions += 1
            self.state.revenue += float(value)
            if user_id is not None:
                self._revenue_by_user[user_id] += float(value)
                self._orders_by_user[user_id] += 1

    def snapshot(self) -> dict[str, float]:
        """Current running aggregates from recorded events."""
        return {
            "ctr": self.track_ctr(self.state.impressions, self.state.clicks),
            "conversion_rate": self.track_conversion(self.state.conversions, self.state.impressions),
            "total_impressions": float(self.state.impressions),
            "total_clicks": float(self.state.clicks),
            "total_conversions": float(self.state.conversions),
            "total_revenue": self.state.revenue,
        }

    def top_users_by_revenue(self, k: int = 10) -> list[tuple[Any, float]]:
        """Highest-value users seen so far."""
        return sorted(self._revenue_by_user.items(), key=lambda kv: kv[1], reverse=True)[:k]

    def reset(self) -> None:
        """Clear all accumulated state."""
        self.state = OnlineMetricsState()
        self._revenue_by_user.clear()
        self._orders_by_user.clear()
