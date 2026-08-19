"""OpenTelemetry Distributed Tracing Integration.

Implements distributed tracing for tracking requests across services
and identifying performance bottlenecks in the recommendation system.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Span:
    """A single trace span."""
    span_id: str
    trace_id: str
    parent_span_id: str | None
    operation_name: str
    start_time: float
    end_time: float | None = None
    status: str = "ok"
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    def set_attribute(self, key: str, value: Any):
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None):
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        })

    def finish(self):
        self.end_time = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes,
            "events": self.events,
        }


class Tracer:
    """Distributed tracer implementation."""

    def __init__(self, service_name: str = "beautyrec"):
        self.service_name = service_name
        self.spans: list[Span] = []
        self._span_counter = 0
        self._trace_counter = 0

    def _generate_span_id(self) -> str:
        self._span_counter += 1
        return f"span-{self._span_counter:016d}"

    def _generate_trace_id(self) -> str:
        self._trace_counter += 1
        return f"trace-{self._trace_counter:016d}"

    def start_span(
        self,
        operation_name: str,
        parent_span_id: str | None = None,
        trace_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Span:
        """Start a new span."""
        if trace_id is None:
            trace_id = self._generate_trace_id()

        span = Span(
            span_id=self._generate_span_id(),
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=time.time(),
            attributes=attributes or {},
        )
        span.set_attribute("service.name", self.service_name)

        self.spans.append(span)
        return span

    @contextmanager
    def trace(self, operation_name: str, attributes: dict[str, Any] | None = None):
        """Context manager for tracing an operation."""
        span = self.start_span(operation_name, attributes=attributes)
        try:
            yield span
        except Exception as e:
            span.status = "error"
            span.set_attribute("error", str(e))
            raise
        finally:
            span.finish()

    def get_trace(self, trace_id: str) -> list[Span]:
        """Get all spans for a trace."""
        return [s for s in self.spans if s.trace_id == trace_id]

    def get_spans_by_operation(self, operation_name: str) -> list[Span]:
        """Get all spans for an operation."""
        return [s for s in self.spans if s.operation_name == operation_name]

    def get_slowest_spans(self, n: int = 10) -> list[Span]:
        """Get the N slowest spans."""
        return sorted(self.spans, key=lambda s: s.duration_ms, reverse=True)[:n]

    def get_error_spans(self) -> list[Span]:
        """Get all error spans."""
        return [s for s in self.spans if s.status == "error"]

    def get_trace_summary(self, trace_id: str) -> dict[str, Any]:
        """Get summary of a trace."""
        spans = self.get_trace(trace_id)
        if not spans:
            return {}

        root_span = next((s for s in spans if s.parent_span_id is None), None)
        total_duration = max(s.end_time or s.start_time for s in spans) - min(s.start_time for s in spans)

        return {
            "trace_id": trace_id,
            "total_spans": len(spans),
            "total_duration_ms": total_duration * 1000,
            "root_operation": root_span.operation_name if root_span else "unknown",
            "error_count": sum(1 for s in spans if s.status == "error"),
            "operations": list(set(s.operation_name for s in spans)),
        }

    def get_performance_report(self) -> dict[str, Any]:
        """Generate performance report from spans."""
        if not self.spans:
            return {"message": "No spans recorded"}

        operation_stats: dict[str, list[float]] = {}
        for span in self.spans:
            if span.operation_name not in operation_stats:
                operation_stats[span.operation_name] = []
            operation_stats[span.operation_name].append(span.duration_ms)

        report = {}
        for op, durations in operation_stats.items():
            durations_arr = sorted(durations)
            report[op] = {
                "count": len(durations),
                "avg_ms": sum(durations) / len(durations),
                "p50_ms": durations_arr[len(durations) // 2],
                "p95_ms": durations_arr[int(len(durations) * 0.95)],
                "p99_ms": durations_arr[int(len(durations) * 0.99)],
                "max_ms": max(durations),
                "min_ms": min(durations),
            }

        return {
            "total_spans": len(self.spans),
            "total_traces": len(set(s.trace_id for s in self.spans)),
            "error_rate": sum(1 for s in self.spans if s.status == "error") / len(self.spans),
            "operations": report,
        }


class SpanExporter:
    """Exports spans to various backends."""

    def __init__(self, tracer: Tracer):
        self.tracer = tracer

    def export_to_log(self):
        """Export spans to structured logs."""
        for span in self.tracer.spans:
            logger.info(
                f"Span: {span.operation_name}",
                extra={
                    "span_id": span.span_id,
                    "trace_id": span.trace_id,
                    "duration_ms": span.duration_ms,
                    "status": span.status,
                    "attributes": span.attributes,
                },
            )

    def export_to_dict(self) -> list[dict[str, Any]]:
        """Export spans as dictionaries."""
        return [span.to_dict() for span in self.tracer.spans]


# Global tracer instance
_tracer: Tracer | None = None


def get_tracer() -> Tracer:
    """Get the global tracer."""
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer


def trace_recommendation(user_id: int) -> Span:
    """Convenience function for tracing recommendation requests."""
    return get_tracer().start_span(
        "recommendation",
        attributes={"user.id": user_id},
    )


def trace_model_inference(model_name: str) -> Span:
    """Convenience function for tracing model inference."""
    return get_tracer().start_span(
        "model_inference",
        attributes={"model.name": model_name},
    )
