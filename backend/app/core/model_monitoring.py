"""ML model health monitoring, drift detection, and business metrics.

Statistical drift detection (PSI and Kolmogorov-Smirnov) over prediction
and feature distributions, product-funnel performance tracking (CTR,
conversion, session depth, retention), and revenue/CLV business metrics.
Optionally exports gauges to Prometheus for dashboarding and alerting.
"""

from __future__ import annotations

import math
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

import numpy as np
import structlog

try:
    from prometheus_client import Gauge

    MODEL_DRIFT_PSI = Gauge(
        "beautyrec_model_drift_psi",
        "Population Stability Index for a feature or predictions",
        ["feature"],
    )
    MODEL_DRIFT_KS_PVALUE = Gauge(
        "beautyrec_model_drift_ks_pvalue",
        "KS-test p-value comparing current vs baseline prediction distribution",
    )
    MODEL_CTR = Gauge("beautyrec_model_ctr", "Click-through rate of recommendations")
    MODEL_CONVERSION_RATE = Gauge(
        "beautyrec_model_conversion_rate", "Conversion rate after recommendation"
    )
    MODEL_AVG_SESSION_DEPTH = Gauge(
        "beautyrec_model_avg_session_depth", "Average recommendation session depth"
    )
    MODEL_RETENTION_RATE = Gauge(
        "beautyrec_model_retention_rate", "Rolling user retention rate"
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover
    PROMETHEUS_AVAILABLE = False

logger = structlog.get_logger(__name__)

try:
    from scipy import stats as _scipy_stats
except ImportError:  # pragma: no cover
    _scipy_stats = None


@dataclass
class DriftResult:
    """Outcome of a single drift test."""

    feature: str
    method: str
    statistic: float
    threshold: float
    drifted: bool
    p_value: float | None = None
    severity: str = "none"
    sample_size: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature": self.feature,
            "method": self.method,
            "statistic": round(self.statistic, 6),
            "threshold": self.threshold,
            "drifted": self.drifted,
            "p_value": round(self.p_value, 6) if self.p_value is not None else None,
            "severity": self.severity,
            "sample_size": self.sample_size,
            "timestamp": self.timestamp.isoformat(),
        }


class DriftDetector:
    """PSI and Kolmogorov-Smirnov drift tests over numeric distributions."""

    PSI_DRIFT_THRESHOLD = 0.2
    PSI_WARN_THRESHOLD = 0.1
    MIN_SAMPLES = 30

    @staticmethod
    def psi(
        expected: Sequence[float] | np.ndarray,
        actual: Sequence[float] | np.ndarray,
        bins: int = 10,
        eps: float = 1e-6,
    ) -> float:
        """Population Stability Index between expected and actual samples.

        Bins are equal-frequency quantiles of the expected distribution.
        Convention: < 0.1 no drift, 0.1-0.25 moderate, > 0.25 significant.
        """
        expected = np.asarray(expected, dtype=float)
        actual = np.asarray(actual, dtype=float)
        if expected.size == 0 or actual.size == 0:
            return 0.0

        edges = np.unique(np.quantile(expected, np.linspace(0.0, 1.0, bins + 1)))
        if edges.size < 2:
            return 0.0

        expected = np.clip(expected, edges[0], edges[-1])
        actual = np.clip(actual, edges[0], edges[-1])
        e_pct = np.histogram(expected, bins=edges)[0] / expected.size
        a_pct = np.histogram(actual, bins=edges)[0] / actual.size

        e_pct = np.clip(e_pct, eps, None)
        a_pct = np.clip(a_pct, eps, None)
        return float(np.sum((a_pct - e_pct) * np.log(a_pct / e_pct)))

    @staticmethod
    def ks_statistic(
        sample_a: Sequence[float] | np.ndarray,
        sample_b: Sequence[float] | np.ndarray,
    ) -> float:
        """Two-sample Kolmogorov-Smirnov statistic (max CDF distance)."""
        a = np.sort(np.asarray(sample_a, dtype=float))
        b = np.sort(np.asarray(sample_b, dtype=float))
        if a.size == 0 or b.size == 0:
            return 0.0
        all_values = np.concatenate([a, b])
        cdf_a = np.searchsorted(a, all_values, side="right") / a.size
        cdf_b = np.searchsorted(b, all_values, side="right") / b.size
        return float(np.max(np.abs(cdf_a - cdf_b)))

    @staticmethod
    def ks_pvalue(d_statistic: float, n_a: int, n_b: int) -> float:
        """Asymptotic two-sample KS p-value (valid for n_a*n_b/(n_a+n_b)>~4)."""
        if d_statistic <= 0.0:
            return 1.0
        n_eff = math.sqrt(n_a * n_b / (n_a + n_b))
        lam = (n_eff + 0.12 + 0.11 / n_eff) * d_statistic
        p_value = 0.0
        for k in range(1, 101):
            term = 2.0 * ((-1.0) ** (k - 1)) * math.exp(-2.0 * k * k * lam * lam)
            p_value += term
            if abs(term) < 1e-12:
                break
        return float(min(1.0, max(0.0, p_value)))

    def ks_test(
        self,
        baseline: Sequence[float] | np.ndarray,
        current: Sequence[float] | np.ndarray,
        alpha: float = 0.05,
    ) -> DriftResult:
        """Run the KS test; drift when p-value < alpha."""
        base_arr = np.asarray(baseline, dtype=float)
        curr_arr = np.asarray(current, dtype=float)

        if _scipy_stats is not None and base_arr.size and curr_arr.size:
            result = _scipy_stats.ks_2samp(base_arr, curr_arr)
            statistic, p_value = float(result.statistic), float(result.pvalue)
        else:
            statistic = self.ks_statistic(base_arr, curr_arr)
            p_value = (
                self.ks_pvalue(statistic, base_arr.size, curr_arr.size)
                if base_arr.size and curr_arr.size
                else 1.0
            )

        drifted = bool(curr_arr.size >= self.MIN_SAMPLES and p_value < alpha)
        severity = "high" if drifted and p_value < alpha / 10 else "medium" if drifted else "low"
        return DriftResult(
            feature="distribution",
            method="ks_test",
            statistic=statistic,
            threshold=alpha,
            drifted=drifted,
            p_value=p_value,
            severity=severity,
            sample_size=int(curr_arr.size),
        )

    def detect(
        self,
        baseline: Sequence[float] | np.ndarray,
        current: Sequence[float] | np.ndarray,
        method: str = "psi",
        threshold: float | None = None,
        feature: str = "distribution",
    ) -> DriftResult:
        """Detect drift with the chosen method ("psi" or "ks_test")."""
        curr_size = len(current)
        if method == "ks_test":
            result = self.ks_test(baseline, current)
            result.feature = feature
            return result

        limit = threshold if threshold is not None else self.PSI_DRIFT_THRESHOLD
        score = self.psi(baseline, current)
        drifted = bool(curr_size >= self.MIN_SAMPLES and score > limit)
        severity = (
            "high" if score > max(limit, self.PSI_WARN_THRESHOLD) * 2 else "medium" if drifted else "low"
        )
        return DriftResult(
            feature=feature,
            method="psi",
            statistic=score,
            threshold=limit,
            drifted=drifted,
            severity=severity,
            sample_size=curr_size,
        )


class ModelHealthMonitor:
    """Tracks prediction/feature distributions against baselines."""

    def __init__(
        self,
        psi_threshold: float = DriftDetector.PSI_DRIFT_THRESHOLD,
        ks_alpha: float = 0.05,
        window_size: int = 10_000,
    ) -> None:
        self.psi_threshold = psi_threshold
        self.ks_alpha = ks_alpha
        self.window_size = window_size
        self.detector = DriftDetector()
        self._prediction_baseline: np.ndarray | None = None
        self._prediction_window: list[float] = []
        self._feature_baselines: dict[str, np.ndarray] = {}
        self._feature_windows: dict[str, list[float]] = {}
        self._results: list[DriftResult] = []

    def set_prediction_baseline(self, scores: Sequence[float]) -> None:
        self._prediction_baseline = np.asarray(scores, dtype=float)

    def set_feature_baseline(self, feature_name: str, values: Sequence[float]) -> None:
        self._feature_baselines[feature_name] = np.asarray(values, dtype=float)
        self._feature_windows.setdefault(feature_name, [])

    def track_prediction_distribution(
        self, score: float, features: dict[str, float] | None = None
    ) -> None:
        """Record one served prediction score (and optional features)."""
        self._prediction_window.append(float(score))
        if len(self._prediction_window) > self.window_size:
            del self._prediction_window[: len(self._prediction_window) - self.window_size]
        if features:
            for name, value in features.items():
                window = self._feature_windows.setdefault(name, [])
                window.append(float(value))
                if len(window) > self.window_size:
                    del window[: len(window) - self.window_size]

    def detect_drift(self) -> DriftResult | None:
        """KS-test current prediction scores against the baseline."""
        if self._prediction_baseline is None or not self._prediction_window:
            return None
        result = self.detector.ks_test(self._prediction_baseline, self._prediction_window)
        result.feature = "predictions"
        self._record(result)
        if PROMETHEUS_AVAILABLE:
            MODEL_DRIFT_KS_PVALUE.set(result.p_value or 1.0)
        if result.drifted:
            logger.warning("prediction_drift_detected", **result.to_dict())
        return result

    def detect_feature_drift(self, feature_name: str) -> DriftResult | None:
        """PSI-test one tracked feature against its baseline."""
        baseline = self._feature_baselines.get(feature_name)
        window = self._feature_windows.get(feature_name)
        if baseline is None or not window:
            return None
        result = self.detector.detect(
            baseline, window, method="psi", threshold=self.psi_threshold, feature=feature_name
        )
        self._record(result)
        if PROMETHEUS_AVAILABLE:
            MODEL_DRIFT_PSI.labels(feature=feature_name).set(result.statistic)
        if result.drifted:
            logger.warning("feature_drift_detected", **result.to_dict())
        return result

    def check_all(self) -> list[DriftResult]:
        """Run every applicable drift check."""
        results: list[DriftResult] = []
        drift = self.detect_drift()
        if drift:
            results.append(drift)
        for feature_name in list(self._feature_baselines):
            result = self.detect_feature_drift(feature_name)
            if result:
                results.append(result)
        return results

    def _record(self, result: DriftResult) -> None:
        self._results.append(result)
        if len(self._results) > 1_000:
            del self._results[: len(self._results) - 1_000]

    def get_results(self, drifted_only: bool = False) -> list[DriftResult]:
        results = [r for r in self._results if r.drifted] if drifted_only else list(self._results)
        return results

    def health_status(self) -> dict[str, Any]:
        recent_drifts = [r for r in self._results[-50:] if r.drifted]
        high = sum(1 for r in recent_drifts if r.severity == "high")
        status = "unhealthy" if high else "degraded" if recent_drifts else "healthy"
        return {
            "status": status,
            "baseline_set": self._prediction_baseline is not None,
            "tracked_features": sorted(self._feature_baselines),
            "prediction_samples": len(self._prediction_window),
            "recent_drift_count": len(recent_drifts),
            "recent_high_severity": high,
        }


class PerformanceTracker:
    """Product-funnel metrics: CTR, conversion, session depth, retention."""

    def __init__(self, max_sessions: int = 100_000) -> None:
        self.max_sessions = max_sessions
        self.impressions = 0
        self.clicks = 0
        self.sessions_seen = 0
        self.conversions = 0
        self._session_depths: OrderedDict[str, int] = OrderedDict()
        self.retention_returning_users = 0
        self.retention_cohort_users = 0

    def track_ctr(self, clicked: bool = False, impressions: int = 1) -> None:
        """Record impression(s); optionally a click on one of them."""
        self.impressions += impressions
        if clicked:
            self.clicks += 1

    def track_conversion(self, converted: bool = True, sessions: int = 1) -> None:
        """Record session(s); optionally a conversion within them."""
        self.sessions_seen += sessions
        if converted:
            self.conversions += sessions

    def track_session_depth(self, session_id: str, depth: int) -> None:
        """Record how many recommendations a session consumed."""
        if session_id in self._session_depths:
            self._session_depths.move_to_end(session_id)
        self._session_depths[session_id] = max(int(depth), 0)
        while len(self._session_depths) > self.max_sessions:
            self._session_depths.popitem(last=False)

    def track_retention(self, returning_users: int, cohort_size: int) -> None:
        """Accumulate a retention cohort measurement."""
        self.retention_returning_users += max(returning_users, 0)
        self.retention_cohort_users += max(cohort_size, 0)

    @property
    def ctr(self) -> float:
        return self.clicks / self.impressions if self.impressions else 0.0

    @property
    def conversion_rate(self) -> float:
        return self.conversions / self.sessions_seen if self.sessions_seen else 0.0

    @property
    def avg_session_depth(self) -> float:
        if not self._session_depths:
            return 0.0
        return sum(self._session_depths.values()) / len(self._session_depths)

    @property
    def retention_rate(self) -> float:
        if not self.retention_cohort_users:
            return 0.0
        return self.retention_returning_users / self.retention_cohort_users

    def snapshot(self) -> dict[str, float]:
        data = {
            "impressions": self.impressions,
            "clicks": self.clicks,
            "ctr": round(self.ctr, 6),
            "sessions": self.sessions_seen,
            "conversions": self.conversions,
            "conversion_rate": round(self.conversion_rate, 6),
            "avg_session_depth": round(self.avg_session_depth, 4),
            "retention_rate": round(self.retention_rate, 6),
        }
        if PROMETHEUS_AVAILABLE:
            MODEL_CTR.set(self.ctr)
            MODEL_CONVERSION_RATE.set(self.conversion_rate)
            MODEL_AVG_SESSION_DEPTH.set(self.avg_session_depth)
            MODEL_RETENTION_RATE.set(self.retention_rate)
        return data


class BusinessMetrics:
    """Revenue and customer-lifetime-value calculations."""

    @staticmethod
    def calculate_revenue_metrics(
        transactions: Iterable[float], active_users: int
    ) -> dict[str, float]:
        """Aggregate revenue KPIs from a set of transaction values.

        Returns total revenue, order count, average order value, ARPU,
        paying users, and ARPPU.
        """
        values = [float(v) for v in transactions if v is not None]
        total_revenue = sum(values)
        paying_users = len(values)
        active_users = max(int(active_users), 0)
        return {
            "total_revenue": round(total_revenue, 2),
            "order_count": paying_users,
            "average_order_value": round(total_revenue / paying_users, 4) if paying_users else 0.0,
            "revenue_per_user": round(total_revenue / active_users, 4) if active_users else 0.0,
            "paying_users": paying_users,
            "arppu": round(total_revenue / paying_users, 4) if paying_users else 0.0,
        }

    @staticmethod
    def calculate_clv(
        average_order_value: float,
        purchases_per_year: float,
        gross_margin: float = 0.7,
        lifespan_years: float = 3.0,
    ) -> float:
        """Customer lifetime value.

        CLV = AOV x purchase frequency x gross margin x lifespan.
        """
        if min(average_order_value, purchases_per_year, lifespan_years) < 0:
            raise ValueError("CLV inputs must be non-negative")
        margin = min(max(gross_margin, 0.0), 1.0)
        clv = average_order_value * purchases_per_year * margin * lifespan_years
        return round(clv, 2)


_default_monitor: ModelHealthMonitor | None = None


def get_model_health_monitor() -> ModelHealthMonitor:
    """Process-wide singleton monitor instance."""
    global _default_monitor
    if _default_monitor is None:
        _default_monitor = ModelHealthMonitor()
    return _default_monitor
