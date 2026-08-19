"""Model Monitoring and Drift Detection.

Implements data drift detection, model performance monitoring,
concept drift detection, and alerting for the recommendation system.
"""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class DriftType(str, Enum):
    DATA_DRIFT = "data_drift"
    CONCEPT_DRIFT = "concept_drift"
    PREDICTION_DRIFT = "prediction_drift"
    FEATURE_DRIFT = "feature_drift"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class DriftAlert:
    """Alert for detected drift."""
    drift_type: DriftType
    severity: AlertSeverity
    message: str
    metric_name: str
    current_value: float
    baseline_value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drift_type": self.drift_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "baseline_value": self.baseline_value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ModelMetrics:
    """Snapshot of model performance metrics."""
    timestamp: datetime
    precision_at_10: float = 0.0
    recall_at_10: float = 0.0
    ndcg_at_10: float = 0.0
    map_at_10: float = 0.0
    hit_rate: float = 0.0
    coverage: float = 0.0
    diversity: float = 0.0
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    latency_p99: float = 0.0
    throughput: float = 0.0
    cache_hit_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "precision_at_10": self.precision_at_10,
            "recall_at_10": self.recall_at_10,
            "ndcg_at_10": self.ndcg_at_10,
            "map_at_10": self.map_at_10,
            "hit_rate": self.hit_rate,
            "coverage": self.coverage,
            "diversity": self.diversity,
            "latency_p50": self.latency_p50,
            "latency_p95": self.latency_p95,
            "latency_p99": self.latency_p99,
            "throughput": self.throughput,
            "cache_hit_rate": self.cache_hit_rate,
        }


class DistributionDriftDetector:
    """Detects data drift using statistical tests."""

    def __init__(self, window_size: int = 1000, threshold: float = 0.05):
        self.window_size = window_size
        self.threshold = threshold
        self.baseline_distributions: dict[str, np.ndarray] = {}
        self.current_windows: dict[str, deque] = {}

    def set_baseline(self, feature_name: str, values: np.ndarray):
        """Set baseline distribution for a feature."""
        self.baseline_distributions[feature_name] = values
        self.current_windows[feature_name] = deque(maxlen=self.window_size)

    def update(self, feature_name: str, value: float):
        """Update current window with new value."""
        if feature_name not in self.current_windows:
            self.current_windows[feature_name] = deque(maxlen=self.window_size)
        self.current_windows[feature_name].append(value)

    def detect(self, feature_name: str) -> DriftAlert | None:
        """Detect drift for a feature using KS test approximation."""
        if feature_name not in self.baseline_distributions:
            return None
        if feature_name not in self.current_windows:
            return None
        if len(self.current_windows[feature_name]) < 100:
            return None

        baseline = self.baseline_distributions[feature_name]
        current = np.array(self.current_windows[feature_name])

        # Simple distribution comparison using means and variances
        baseline_mean = np.mean(baseline)
        current_mean = np.mean(current)
        baseline_std = np.std(baseline) + 1e-10
        current_std = np.std(current) + 1e-10

        # Mean drift score (normalized)
        mean_drift = abs(current_mean - baseline_mean) / baseline_std

        # Variance drift score
        var_drift = abs(current_std - baseline_std) / baseline_std

        # Combined drift score
        drift_score = (mean_drift + var_drift) / 2

        if drift_score > self.threshold:
            severity = (
                AlertSeverity.CRITICAL if drift_score > self.threshold * 3
                else AlertSeverity.WARNING if drift_score > self.threshold * 1.5
                else AlertSeverity.INFO
            )
            return DriftAlert(
                drift_type=DriftType.DATA_DRIFT,
                severity=severity,
                message=f"Data drift detected for {feature_name}",
                metric_name=feature_name,
                current_value=drift_score,
                baseline_value=self.threshold,
                threshold=self.threshold,
                metadata={
                    "baseline_mean": float(baseline_mean),
                    "current_mean": float(current_mean),
                    "baseline_std": float(baseline_std),
                    "current_std": float(current_std),
                },
            )
        return None


class PerformanceDriftDetector:
    """Detects model performance degradation over time."""

    def __init__(
        self,
        metric_name: str = "ndcg_at_10",
        window_size: int = 10,
        degradation_threshold: float = 0.05,
    ):
        self.metric_name = metric_name
        self.window_size = window_size
        self.degradation_threshold = degradation_threshold
        self.history: deque[ModelMetrics] = deque(maxlen=100)
        self.baseline_metrics: ModelMetrics | None = None

    def set_baseline(self, metrics: ModelMetrics):
        """Set baseline performance metrics."""
        self.baseline_metrics = metrics
        logger.info(f"Set baseline for {self.metric_name}: {getattr(metrics, self.metric_name)}")

    def update(self, metrics: ModelMetrics):
        """Update with new performance metrics."""
        self.history.append(metrics)

    def detect(self) -> DriftAlert | None:
        """Detect performance degradation."""
        if self.baseline_metrics is None or len(self.history) < self.window_size:
            return None

        baseline_value = getattr(self.baseline_metrics, self.metric_name)
        recent_values = [
            getattr(m, self.metric_name) for m in list(self.history)[-self.window_size:]
        ]
        current_value = np.mean(recent_values)

        if baseline_value == 0:
            return None

        degradation = (baseline_value - current_value) / baseline_value

        if degradation > self.degradation_threshold:
            severity = (
                AlertSeverity.CRITICAL if degradation > self.degradation_threshold * 3
                else AlertSeverity.WARNING
            )
            return DriftAlert(
                drift_type=DriftType.CONCEPT_DRIFT,
                severity=severity,
                message=f"Model performance degraded: {self.metric_name}",
                metric_name=self.metric_name,
                current_value=current_value,
                baseline_value=baseline_value,
                threshold=self.degradation_threshold,
                metadata={
                    "degradation_percent": degradation * 100,
                    "window_size": self.window_size,
                    "recent_values": recent_values,
                },
            )
        return None


class PredictionDriftDetector:
    """Detects drift in model prediction distributions."""

    def __init__(self, window_size: int = 1000, threshold: float = 0.1):
        self.window_size = window_size
        self.threshold = threshold
        self.baseline_scores: np.ndarray | None = None
        self.current_scores: deque = deque(maxlen=window_size)

    def set_baseline(self, scores: np.ndarray):
        """Set baseline prediction score distribution."""
        self.baseline_scores = scores

    def update(self, score: float):
        """Update with new prediction score."""
        self.current_scores.append(score)

    def detect(self) -> DriftAlert | None:
        """Detect prediction distribution drift."""
        if self.baseline_scores is None or len(self.current_scores) < 100:
            return None

        baseline_mean = float(np.mean(self.baseline_scores))
        current_mean = float(np.mean(self.current_scores))

        drift = abs(current_mean - baseline_mean)
        if drift > self.threshold:
            return DriftAlert(
                drift_type=DriftType.PREDICTION_DRIFT,
                severity=AlertSeverity.WARNING,
                message="Prediction score distribution shifted",
                metric_name="prediction_mean",
                current_value=current_mean,
                baseline_value=baseline_mean,
                threshold=self.threshold,
            )
        return None


class ModelMonitor:
    """Central model monitoring system."""

    def __init__(self):
        self.performance_detector = PerformanceDriftDetector()
        self.prediction_detector = PredictionDriftDetector()
        self.feature_detectors: dict[str, DistributionDriftDetector] = {}
        self.alerts: list[DriftAlert] = []
        self.metrics_history: list[ModelMetrics] = []

    def initialize(
        self,
        baseline_metrics: ModelMetrics,
        feature_distributions: dict[str, np.ndarray] | None = None,
        prediction_scores: np.ndarray | None = None,
    ):
        """Initialize monitoring with baseline data."""
        self.performance_detector.set_baseline(baseline_metrics)

        if feature_distributions:
            for feature_name, values in feature_distributions.items():
                detector = DistributionDriftDetector()
                detector.set_baseline(feature_name, values)
                self.feature_detectors[feature_name] = detector

        if prediction_scores is not None:
            self.prediction_detector.set_baseline(prediction_scores)

        logger.info("Model monitor initialized with baseline data")

    def record_metrics(self, metrics: ModelMetrics):
        """Record new performance metrics and check for drift."""
        self.metrics_history.append(metrics)
        self.performance_detector.update(metrics)

        alert = self.performance_detector.detect()
        if alert:
            self.alerts.append(alert)
            logger.warning(f"Drift alert: {alert.message}")

    def record_prediction(self, score: float, features: dict[str, float] | None = None):
        """Record a new prediction and check for drift."""
        self.prediction_detector.update(score)

        if features:
            for feature_name, value in features.items():
                if feature_name not in self.feature_detectors:
                    self.feature_detectors[feature_name] = DistributionDriftDetector()
                self.feature_detectors[feature_name].update(feature_name, value)

    def check_all(self) -> list[DriftAlert]:
        """Run all drift detection checks."""
        alerts = []

        # Check performance drift
        alert = self.performance_detector.detect()
        if alert:
            alerts.append(alert)

        # Check prediction drift
        alert = self.prediction_detector.detect()
        if alert:
            alerts.append(alert)

        # Check feature drift
        for feature_name, detector in self.feature_detectors.items():
            alert = detector.detect(feature_name)
            if alert:
                alerts.append(alert)

        self.alerts.extend(alerts)
        return alerts

    def get_alerts(
        self,
        severity: AlertSeverity | None = None,
        since: datetime | None = None,
    ) -> list[DriftAlert]:
        """Get alerts filtered by severity and time."""
        alerts = self.alerts
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if since:
            alerts = [a for a in alerts if a.timestamp >= since]
        return alerts

    def get_metrics_history(
        self,
        last_n: int | None = None,
    ) -> list[ModelMetrics]:
        """Get historical metrics."""
        history = self.metrics_history
        if last_n:
            history = history[-last_n:]
        return history

    def generate_report(self) -> dict[str, Any]:
        """Generate monitoring report."""
        return {
            "total_alerts": len(self.alerts),
            "critical_alerts": len([a for a in self.alerts if a.severity == AlertSeverity.CRITICAL]),
            "warning_alerts": len([a for a in self.alerts if a.severity == AlertSeverity.WARNING]),
            "recent_alerts": [a.to_dict() for a in self.alerts[-10:]],
            "metrics_history": [m.to_dict() for m in self.metrics_history[-20:]],
            "feature_detectors": list(self.feature_detectors.keys()),
            "generated_at": datetime.utcnow().isoformat(),
        }


class ContinuousRetrainer:
    """Manages automatic model retraining based on drift detection."""

    def __init__(
        self,
        retrain_threshold: float = 0.1,
        min_samples: int = 1000,
        cooldown_hours: int = 24,
    ):
        self.retrain_threshold = retrain_threshold
        self.min_samples = min_samples
        self.cooldown_hours = cooldown_hours
        self.last_retrain: datetime | None = None
        self.pending_samples: list[Any] = []
        self.retrain_history: list[dict[str, Any]] = []

    def add_sample(self, sample: Any):
        """Add a sample for potential retraining."""
        self.pending_samples.append(sample)

    def should_retrain(self, alerts: list[DriftAlert]) -> bool:
        """Check if model should be retrained."""
        # Check cooldown
        if self.last_retrain:
            hours_since = (datetime.utcnow() - self.last_retrain).total_seconds() / 3600
            if hours_since < self.cooldown_hours:
                return False

        # Check if enough samples
        if len(self.pending_samples) < self.min_samples:
            return False

        # Check for critical alerts
        critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        if critical_alerts:
            logger.info(f"Retraining triggered by {len(critical_alerts)} critical alerts")
            return True

        # Check for performance degradation
        perf_alerts = [a for a in alerts if a.drift_type == DriftType.CONCEPT_DRIFT]
        if perf_alerts:
            logger.info("Retraining triggered by performance degradation")
            return True

        return False

    def trigger_retrain(self) -> dict[str, Any]:
        """Trigger model retraining."""
        retrain_info = {
            "triggered_at": datetime.utcnow().isoformat(),
            "samples_used": len(self.pending_samples),
            "reason": "drift_detection",
        }

        self.retrain_history.append(retrain_info)
        self.last_retrain = datetime.utcnow()
        self.pending_samples = []

        logger.info(f"Model retraining triggered: {retrain_info}")
        return retrain_info


# Global monitor instance
_model_monitor: ModelMonitor | None = None


def get_model_monitor() -> ModelMonitor:
    """Get the global model monitor."""
    global _model_monitor
    if _model_monitor is None:
        _model_monitor = ModelMonitor()
    return _model_monitor
