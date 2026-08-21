"""Alert rule evaluation and management.

Rules are declarative metric conditions (e.g. ``"error_rate > 0.05"``)
evaluated against a metrics snapshot. Firing respects per-rule cooldowns,
alerts are tracked through their lifecycle (firing -> acknowledged ->
resolved) and persisted to an in-memory history.
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class Severity(str, Enum):
    """Alert severity levels, P0 most critical."""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"

    @property
    def rank(self) -> int:
        return int(self.value[1])


class AlertStatus(str, Enum):
    FIRING = "firing"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


_CONDITION_RE = re.compile(
    r"^\s*([A-Za-z_][\w.]*)\s*(<=|>=|==|!=|<|>)\s*(-?\d+(?:\.\d+)?)\s*$"
)

_OPERATORS: dict[str, Any] = {
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def resolve_metric(metrics: dict[str, Any], key: str) -> Any:
    """Resolve a possibly dotted metric path ("model.quality_drop_percent")."""
    value: Any = metrics
    for part in key.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


@dataclass
class AlertRule:
    """A declarative alert condition evaluated against a metrics snapshot."""

    name: str
    condition: str
    severity: Severity | str
    message: str
    cooldown_seconds: int = 300
    labels: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.severity, str):
            self.severity = Severity(self.severity.upper())
        match = _CONDITION_RE.match(self.condition)
        if not match:
            raise ValueError(f"Invalid condition expression: {self.condition!r}")
        self._metric_key, self._operator, self._threshold = (
            match.group(1),
            match.group(2),
            float(match.group(3)),
        )

    @property
    def metric_key(self) -> str:
        return self._metric_key

    @property
    def threshold(self) -> float:
        return self._threshold

    def evaluate(self, metrics: dict[str, Any]) -> bool:
        """Return True when the condition holds for the given metrics."""
        value = resolve_metric(metrics, self._metric_key)
        if value is None or isinstance(value, bool):
            return False
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return False
        return _OPERATORS[self._operator](numeric, self._threshold)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "condition": self.condition,
            "severity": self.severity.value,
            "message": self.message,
            "cooldown_seconds": self.cooldown_seconds,
            "labels": self.labels,
        }


@dataclass
class Alert:
    """A single alert occurrence with lifecycle timestamps."""

    id: str
    rule_name: str
    severity: Severity
    message: str
    metric_value: float | None = None
    labels: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None

    @property
    def status(self) -> AlertStatus:
        if self.resolved_at is not None:
            return AlertStatus.RESOLVED
        if self.acknowledged_at is not None:
            return AlertStatus.ACKNOWLEDGED
        return AlertStatus.FIRING

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "metric_value": self.metric_value,
            "labels": self.labels,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat()
            if self.acknowledged_at
            else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class AlertHistory:
    """Append-only alert history with time-based queries."""

    def __init__(self, max_entries: int = 5_000) -> None:
        self.max_entries = max_entries
        self._entries: list[Alert] = []

    def record(self, alert: Alert) -> None:
        self._entries.append(alert)
        if len(self._entries) > self.max_entries:
            del self._entries[: len(self._entries) - self.max_entries]

    def query(
        self,
        since: datetime | None = None,
        severity: Severity | str | None = None,
        rule_name: str | None = None,
        status: AlertStatus | None = None,
    ) -> list[Alert]:
        results = self._entries
        if since is not None:
            results = [a for a in results if a.created_at >= since]
        if severity is not None:
            wanted = Severity(severity) if isinstance(severity, str) else severity
            results = [a for a in results if a.severity == wanted]
        if rule_name is not None:
            results = [a for a in results if a.rule_name == rule_name]
        if status is not None:
            results = [a for a in results if a.status == status]
        return list(results)

    def summary(self) -> dict[str, Any]:
        by_severity: dict[str, int] = {}
        for alert in self._entries:
            by_severity[alert.severity.value] = by_severity.get(alert.severity.value, 0) + 1
        return {
            "total": len(self._entries),
            "by_severity": dict(sorted(by_severity.items())),
            "last_alert_at": self._entries[-1].created_at.isoformat()
            if self._entries
            else None,
        }


HIGH_ERROR_RATE = AlertRule(
    name="high_error_rate",
    condition="error_rate > 0.05",
    severity="P1",
    message="HTTP error rate exceeded 5% over the evaluation window",
    cooldown_seconds=300,
    labels={"team": "recommendations", "category": "api"},
)

HIGH_LATENCY = AlertRule(
    name="high_latency",
    condition="latency_p95_seconds > 2.0",
    severity="P2",
    message="p95 request latency exceeded 2 seconds",
    cooldown_seconds=300,
    labels={"team": "recommendations", "category": "api"},
)

LOW_CACHE_HIT_RATE = AlertRule(
    name="low_cache_hit_rate",
    condition="cache_hit_rate < 0.50",
    severity="P3",
    message="Recommendation cache hit rate dropped below 50%",
    cooldown_seconds=600,
    labels={"team": "recommendations", "category": "performance"},
)

MODEL_DEGRADATION = AlertRule(
    name="model_degradation",
    condition="model_quality_drop_percent > 10.0",
    severity="P1",
    message="Model quality metric degraded by more than 10% from baseline",
    cooldown_seconds=900,
    labels={"team": "ml", "category": "model"},
)

DEFAULT_RULES: list[AlertRule] = [
    HIGH_ERROR_RATE,
    HIGH_LATENCY,
    LOW_CACHE_HIT_RATE,
    MODEL_DEGRADATION,
]


class AlertManager:
    """Evaluates rules, fires alerts with cooldowns, tracks lifecycle."""

    def __init__(
        self,
        rules: list[AlertRule] | None = None,
        history: AlertHistory | None = None,
    ) -> None:
        self.rules: list[AlertRule] = list(rules) if rules is not None else list(DEFAULT_RULES)
        self.history = history or AlertHistory()
        self.active: dict[str, Alert] = {}
        self._last_fired_at: dict[str, float] = {}

    def add_rule(self, rule: AlertRule) -> None:
        self.rules.append(rule)

    def check_rules(self, metrics: dict[str, Any]) -> list[Alert]:
        """Evaluate all rules against a metrics snapshot; fire on breach.

        Returns the list of newly fired alerts (cooldown-suppressed
        breaches do not produce new alerts).
        """
        fired: list[Alert] = []
        now = time.monotonic()
        for rule in sorted(self.rules, key=lambda r: r.severity.rank):
            if not rule.evaluate(metrics):
                continue
            last = self._last_fired_at.get(rule.name)
            if last is not None and (now - last) < rule.cooldown_seconds:
                logger.debug(
                    "alert_suppressed_by_cooldown",
                    rule=rule.name,
                    cooldown_seconds=rule.cooldown_seconds,
                )
                continue
            fired.append(
                self.fire_alert(rule, value=resolve_metric(metrics, rule.metric_key))
            )
        return fired

    def fire_alert(
        self,
        rule: AlertRule,
        value: float | None = None,
        labels: dict[str, str] | None = None,
    ) -> Alert:
        """Manually fire an alert for a rule."""
        alert = Alert(
            id=uuid.uuid4().hex[:12],
            rule_name=rule.name,
            severity=rule.severity,
            message=rule.message,
            metric_value=float(value) if value is not None else None,
            labels={**rule.labels, **(labels or {})},
        )
        self.active[alert.id] = alert
        self.history.record(alert)
        self._last_fired_at[rule.name] = time.monotonic()
        logger.warning(
            "alert_fired",
            alert_id=alert.id,
            rule=rule.name,
            severity=rule.severity.value,
            metric_value=alert.metric_value,
            message=rule.message,
        )
        return alert

    def get_active_alerts(
        self, include_acknowledged: bool = True
    ) -> list[Alert]:
        """Return unresolved alerts, most severe first."""
        alerts = [a for a in self.active.values() if a.status != AlertStatus.RESOLVED]
        if not include_acknowledged:
            alerts = [a for a in alerts if a.status == AlertStatus.FIRING]
        alerts.sort(key=lambda a: (a.severity.rank, a.created_at))
        return alerts

    def acknowledge(self, alert_id: str) -> bool:
        """Acknowledge a firing alert; returns False if unknown/resolved."""
        alert = self.active.get(alert_id)
        if alert is None or alert.status != AlertStatus.FIRING:
            return False
        alert.acknowledged_at = datetime.now(timezone.utc)
        logger.info("alert_acknowledged", alert_id=alert_id, rule=alert.rule_name)
        return True

    def resolve(self, alert_id: str) -> bool:
        """Resolve an active alert; returns False if unknown."""
        alert = self.active.get(alert_id)
        if alert is None or alert.resolved_at is not None:
            return False
        alert.resolved_at = datetime.now(timezone.utc)
        logger.info("alert_resolved", alert_id=alert_id, rule=alert.rule_name)
        return True

    def resolve_rule(self, rule_name: str) -> int:
        """Resolve every active alert raised by a rule; returns count."""
        count = 0
        for alert in list(self.active.values()):
            if alert.rule_name == rule_name and alert.resolved_at is None:
                self.resolve(alert.id)
                count += 1
        return count
