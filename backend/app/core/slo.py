"""SLO/SLI framework with error budgets and capacity planning.

Defines service level objectives, computes service level indicators
(availability and latency), tracks error-budget consumption and burn
rate, and estimates replica capacity for expected traffic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

import structlog

logger = structlog.get_logger(__name__)


@dataclass(eq=False)
class SLO:
    """A service level objective.

    indicator: "availability" (fraction of non-5xx responses) or
    "latency" (fraction of requests under latency_threshold_seconds).
    Instances hash by identity, so they can key metric mappings.
    """

    name: str
    indicator: str
    target: float
    window_days: int = 30
    latency_threshold_seconds: float = 1.0
    description: str = ""
    labels: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.indicator not in {"availability", "latency"}:
            raise ValueError(f"Unsupported indicator: {self.indicator!r}")
        if not 0.0 < self.target <= 1.0:
            raise ValueError(f"target must be in (0, 1], got {self.target}")

    @property
    def error_budget_fraction(self) -> float:
        """Allowed bad-event fraction over the window."""
        return 1.0 - self.target

    @property
    def error_budget_requests(self) -> float:
        """Bad requests allowed per day at steady state (per 1 rps baseline)."""
        return self.error_budget_fraction * 86_400 * self.window_days / self.window_days

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "indicator": self.indicator,
            "target": self.target,
            "window_days": self.window_days,
            "latency_threshold_seconds": self.latency_threshold_seconds,
            "description": self.description,
            "labels": self.labels,
        }


class SLOCalculator:
    """Computes SLIs, error budgets, burn rates, and SLO reports."""

    BURN_OK = 1.0
    BURN_AT_RISK = 4.0

    @staticmethod
    def availability_sli(total_requests: int, failed_requests: int) -> float:
        """Fraction of requests that did not fail (server errors)."""
        total = max(int(total_requests), 0)
        failed = max(int(failed_requests), 0)
        if total == 0:
            return 1.0
        return max(0.0, min(1.0, (total - min(failed, total)) / total))

    @staticmethod
    def latency_sli(
        durations: Sequence[float] | Iterable[float],
        threshold_seconds: float,
    ) -> float:
        """Fraction of request durations at or under the threshold."""
        values = [float(d) for d in durations]
        if not values:
            return 1.0
        good = sum(1 for d in values if d <= threshold_seconds)
        return good / len(values)

    @staticmethod
    def error_budget_remaining(slo: SLO, sli: float) -> float:
        """Fraction of the error budget still unspent, clamped to [0, 1]."""
        budget = slo.error_budget_fraction
        if budget <= 0.0:
            return 0.0
        spent = max(0.0, 1.0 - sli)
        return max(0.0, min(1.0, (budget - spent) / budget))

    @staticmethod
    def burn_rate(slo: SLO, sli: float) -> float:
        """How many times faster than sustainable the budget is burning."""
        budget = slo.error_budget_fraction
        if budget <= 0.0:
            return math.inf
        return max(0.0, 1.0 - sli) / budget

    def status_for(self, slo: SLO, sli: float) -> str:
        burn = self.burn_rate(slo, sli)
        if self.error_budget_remaining(slo, sli) <= 0.0:
            return "breached"
        if burn <= self.BURN_OK:
            return "healthy"
        if burn <= self.BURN_AT_RISK:
            return "at_risk"
        return "breached"

    def generate_report(
        self,
        slo: SLO,
        sli: float,
        elapsed_days: float | None = None,
        total_requests: int | None = None,
    ) -> dict[str, Any]:
        """Full SLO report: SLI, budget, burn rate, projected exhaustion."""
        remaining = self.error_budget_remaining(slo, sli)
        burn = self.burn_rate(slo, sli)
        status = self.status_for(slo, sli)

        projected_exhaustion_days: float | None = None
        if burn > self.BURN_OK and math.isfinite(burn):
            projected_exhaustion_days = round(slo.window_days / burn, 2)

        report: dict[str, Any] = {
            "slo": slo.to_dict(),
            "sli": round(sli, 6),
            "meets_target": sli >= slo.target,
            "error_budget_remaining_percent": round(remaining * 100.0, 3),
            "burn_rate": round(burn, 4) if math.isfinite(burn) else None,
            "status": status,
            "projected_budget_exhaustion_days": projected_exhaustion_days,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        if elapsed_days is not None:
            window_elapsed_fraction = max(0.0, min(1.0, elapsed_days / slo.window_days))
            allowed_burn_to_date = slo.error_budget_fraction * window_elapsed_fraction
            actual_bad_fraction = max(0.0, 1.0 - sli)
            report["window_elapsed_fraction"] = round(window_elapsed_fraction, 6)
            report["budget_spent_to_date_percent"] = (
                round(actual_bad_fraction / allowed_burn_to_date * 100.0, 3)
                if allowed_burn_to_date > 0
                else (0.0 if actual_bad_fraction == 0 else math.inf)
            )
        if total_requests is not None:
            report["total_requests"] = total_requests
            report["remaining_bad_request_allowance"] = int(
                max(0.0, remaining) * slo.error_budget_fraction * total_requests
            )
        logger.info("slo_report_generated", slo=slo.name, status=status, sli=round(sli, 6))
        return report

    def generate_multi_report(
        self,
        measurements: dict[SLO, float] | Sequence[tuple[SLO, float]],
    ) -> dict[str, Any]:
        """Report across several SLOs with an overall worst-case status."""
        pairs = (
            measurements.items()
            if hasattr(measurements, "items")
            else list(measurements)
        )
        reports = {slo.name: self.generate_report(slo, sli) for slo, sli in pairs}
        rank = {"healthy": 0, "at_risk": 1, "breached": 2}
        overall = max((r["status"] for r in reports.values()), key=lambda s: rank[s], default="healthy")
        return {"overall_status": overall, "slos": reports}


DEFAULT_SLOS: list[SLO] = [
    SLO(
        name="api_availability",
        indicator="availability",
        target=0.999,
        window_days=30,
        description="99.9% of recommendation API requests succeed (non-5xx)",
    ),
    SLO(
        name="recommendation_latency",
        indicator="latency",
        target=0.99,
        window_days=30,
        latency_threshold_seconds=0.5,
        description="99% of recommendations served within 500ms",
    ),
]


class CapacityPlanner:
    """Traffic estimation and replica sizing recommendations."""

    @staticmethod
    def estimate_qps(
        daily_requests: int,
        peak_fraction: float = 0.2,
        peak_window_minutes: int = 60,
    ) -> float:
        """Estimate peak QPS assuming traffic concentrates in a peak window.

        peak_fraction: share of daily traffic landing inside the busiest
        peak_window_minutes interval.
        """
        if daily_requests < 0:
            raise ValueError("daily_requests must be non-negative")
        if not 0.0 < peak_fraction <= 1.0:
            raise ValueError("peak_fraction must be in (0, 1]")
        if peak_window_minutes <= 0:
            raise ValueError("peak_window_minutes must be positive")
        peak_window_seconds = peak_window_minutes * 60
        return daily_requests * peak_fraction / peak_window_seconds

    @staticmethod
    def recommend_replicas(
        peak_qps: float,
        per_replica_capacity_qps: float,
        headroom: float = 1.3,
        min_replicas: int = 2,
        max_replicas: int | None = None,
    ) -> int:
        """Replica count covering peak QPS with headroom and HA minimum."""
        if peak_qps < 0 or per_replica_capacity_qps <= 0:
            raise ValueError("peak_qps must be >= 0 and capacity > 0")
        if headroom < 1.0:
            raise ValueError("headroom must be >= 1.0")
        replicas = math.ceil(peak_qps * headroom / per_replica_capacity_qps)
        replicas = max(replicas, min_replicas)
        if max_replicas is not None:
            replicas = min(replicas, max_replicas)
        return replicas

    @staticmethod
    def plan_for_growth(
        daily_requests: int,
        monthly_growth_rate: float,
        months: int,
        per_replica_capacity_qps: float,
        **replica_kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Project peak QPS and replica needs over coming months."""
        plan: list[dict[str, Any]] = []
        projected_daily = float(daily_requests)
        growth = 1.0 + monthly_growth_rate
        for month in range(1, months + 1):
            projected_daily *= growth
            peak_qps = CapacityPlanner.estimate_qps(int(projected_daily))
            plan.append(
                {
                    "month": month,
                    "projected_daily_requests": int(projected_daily),
                    "estimated_peak_qps": round(peak_qps, 2),
                    "recommended_replicas": CapacityPlanner.recommend_replicas(
                        peak_qps, per_replica_capacity_qps, **replica_kwargs
                    ),
                }
            )
        return plan
