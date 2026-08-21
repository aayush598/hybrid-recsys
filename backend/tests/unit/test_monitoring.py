"""Unit tests for monitoring: logging, tracing, alerting, drift, SLOs."""

from __future__ import annotations

import logging

import numpy as np
import pytest


class TestSetupLogging:
    def test_json_configuration(self):
        from app.core.logging_config import setup_logging

        setup_logging(level="INFO", format="json")
        root = logging.getLogger()
        assert root.level == logging.INFO
        assert root.handlers
        root.handlers.clear()

    def test_console_configuration(self):
        from app.core.logging_config import setup_logging

        setup_logging(level="DEBUG", format="console")
        root = logging.getLogger()
        assert root.level == logging.DEBUG
        root.handlers.clear()

    def test_correlation_id_context(self):
        from app.core.logging_config import clear_log_context, new_correlation_id

        correlation_id = new_correlation_id()
        assert len(correlation_id) == 32
        clear_log_context()


class TestTracer:
    def test_span_lifecycle(self):
        from app.core.tracing import Tracer

        tracer = Tracer()
        span_id = tracer.start_span("GET /recommendations", trace_id="trace-1")
        tracer.record_attribute(span_id, "http.method", "GET")
        span = tracer.end_span(span_id)
        assert span is not None
        assert span.status == "ok"
        assert span.duration_ms >= 0.0
        assert span.attributes["http.method"] == "GET"

    def test_get_trace_returns_ordered_spans(self):
        from app.core.tracing import Tracer

        tracer = Tracer()
        parent = tracer.start_span("parent", trace_id="t42")
        child = tracer.start_span("child", trace_id="t42", parent_span_id=parent)
        spans = tracer.get_trace("t42")
        assert [s.name for s in spans] == ["parent", "child"]
        assert spans[1].parent_span_id == parent
        tracer.end_span(child)
        tracer.end_span(parent)

    def test_unknown_span_end_is_noop(self):
        from app.core.tracing import Tracer

        assert Tracer().end_span("missing") is None


class TestLatencyTracker:
    def test_percentiles_and_count(self):
        from app.core.tracing import LatencyTracker

        tracker = LatencyTracker()
        for value in [0.1, 0.2, 0.3, 0.4, 0.5]:
            tracker.record_latency("/recs", value)
        percentiles = tracker.get_percentiles("/recs")
        assert percentiles["count"] == 5
        assert percentiles["p50"] == pytest.approx(0.3)
        assert 0.0 < percentiles["p50"] <= percentiles["p95"] <= percentiles["p99"]

    def test_unknown_endpoint_returns_empty(self):
        from app.core.tracing import LatencyTracker

        stats = LatencyTracker().get_percentiles("/nope")
        assert stats["count"] == 0 and stats["p99"] == 0.0

    def test_reset(self):
        from app.core.tracing import LatencyTracker

        tracker = LatencyTracker()
        tracker.record_latency("/a", 0.5)
        tracker.reset("/a")
        assert tracker.get_percentiles("/a")["count"] == 0


class TestAlertManager:
    def test_rule_fires_on_breach(self):
        from app.core.alerting import AlertManager, AlertRule

        rule = AlertRule(
            name="high_errors", condition="error_rate > 0.5",
            severity="P1", message="too many errors",
        )
        manager = AlertManager(rules=[rule])
        fired = manager.check_rules({"error_rate": 0.9})
        assert len(fired) == 1
        assert fired[0].rule_name == "high_errors"
        assert manager.get_active_alerts()

    def test_cooldown_suppresses_repeat_alerts(self):
        from app.core.alerting import AlertManager, AlertRule

        rule = AlertRule(
            name="hot", condition="temp > 100", severity="P2", message="hot",
            cooldown_seconds=3600,
        )
        manager = AlertManager(rules=[rule])
        first = manager.check_rules({"temp": 150})
        second = manager.check_rules({"temp": 150})
        assert first and not second

    def test_acknowledge_and_resolve_lifecycle(self):
        from app.core.alerting import AlertManager, AlertRule, AlertStatus

        rule = AlertRule(
            name="disk", condition="disk_usage > 90", severity="P0", message="full"
        )
        manager = AlertManager(rules=[rule])
        (alert,) = manager.check_rules({"disk_usage": 95})
        assert alert.status == AlertStatus.FIRING
        assert manager.acknowledge(alert.id)
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert manager.resolve(alert.id)
        assert alert.status == AlertStatus.RESOLVED
        assert manager.resolve(alert.id) is False

    def test_no_fire_when_condition_false(self):
        from app.core.alerting import AlertManager, AlertRule

        rule = AlertRule(
            name="never", condition="x > 10", severity="P3", message="-"
        )
        manager = AlertManager(rules=[rule])
        assert manager.check_rules({"x": 5}) == []


class TestDriftDetector:
    def test_psi_identical_distributions_low(self):
        from app.core.model_monitoring import DriftDetector

        rng = np.random.default_rng(7)
        sample = rng.normal(0, 1, size=500)
        assert DriftDetector.psi(sample, sample) < 0.01

    def test_psi_shifted_distribution_high(self):
        from app.core.model_monitoring import DriftDetector

        rng = np.random.default_rng(7)
        baseline = rng.normal(0, 1, size=500)
        current = rng.normal(6, 1, size=500)
        assert DriftDetector.psi(baseline, current) > 0.25

    def test_ks_test_detects_shift(self):
        from app.core.model_monitoring import DriftDetector

        detector = DriftDetector()
        rng = np.random.default_rng(3)
        baseline = rng.normal(0, 1, size=300)
        same = rng.normal(0, 1, size=300)
        shifted = rng.normal(1.5, 1, size=300)

        stable = detector.ks_test(baseline, same)
        drifted = detector.ks_test(baseline, shifted)
        assert not stable.drifted
        assert drifted.drifted
        assert drifted.p_value < stable.p_value

    def test_detect_dispatches_by_method(self):
        from app.core.model_monitoring import DriftDetector

        detector = DriftDetector()
        rng = np.random.default_rng(11)
        baseline = rng.normal(0, 1, 200)
        result = detector.detect(baseline, baseline + 8, method="psi", feature="age")
        assert result.method == "psi"
        assert result.feature == "age"


class TestSLOCalculator:
    def test_availability_sli(self):
        from app.core.slo import SLOCalculator

        assert SLOCalculator.availability_sli(1000, 5) == pytest.approx(0.995)
        assert SLOCalculator.availability_sli(0, 0) == 1.0

    def test_latency_sli(self):
        from app.core.slo import SLOCalculator

        durations = [0.1, 0.2, 0.4, 0.9]
        assert SLOCalculator.latency_sli(durations, threshold_seconds=0.5) == 0.75

    def test_error_budget_and_burn_rate(self):
        from app.core.slo import SLO, SLOCalculator

        slo = SLO(name="avail", indicator="availability", target=0.99)
        calculator = SLOCalculator()
        assert calculator.error_budget_remaining(slo, sli=1.0) == 1.0
        assert calculator.error_budget_remaining(slo, sli=0.99) == 0.0
        assert calculator.burn_rate(slo, sli=0.985) == pytest.approx(1.5)

    def test_generate_report_fields(self):
        from app.core.slo import SLO, SLOCalculator

        slo = SLO(name="latency", indicator="latency", target=0.99,
                  latency_threshold_seconds=0.5)
        report = SLOCalculator().generate_report(slo, sli=0.999)
        assert report["meets_target"] is True
        assert report["status"] in {"healthy", "at_risk", "breached"}
        assert "error_budget_remaining_percent" in report

    def test_invalid_slo_rejected(self):
        from app.core.slo import SLO

        with pytest.raises(ValueError):
            SLO(name="bad", indicator="quantum", target=0.99)
