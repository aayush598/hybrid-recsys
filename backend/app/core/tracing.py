"""In-memory distributed tracing and latency tracking.

Provides trace/span propagation for HTTP requests without any external
tracing backend. Trace IDs are accepted from upstream callers via the
``X-Trace-ID`` header (or generated) and returned to clients in response
headers, enabling end-to-end correlation across services.
"""

from __future__ import annotations

import math
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

TRACE_HEADER = "X-Trace-ID"
SPAN_HEADER = "X-Span-ID"


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


@dataclass
class Span:
    """A single span within a distributed trace."""

    span_id: str
    trace_id: str
    name: str
    parent_span_id: str | None = None
    start_time: float = field(default_factory=time.perf_counter)
    end_time: float | None = None
    status: str = "unset"
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 3),
            "attributes": self.attributes,
        }


class Tracer:
    """Memory-backed tracer storing spans keyed by span ID."""

    def __init__(self, max_spans: int = 10_000) -> None:
        self.max_spans = max_spans
        self._spans: OrderedDict[str, Span] = OrderedDict()

    def start_span(
        self,
        name: str,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
    ) -> str:
        """Start a new span and return its span ID."""
        span = Span(
            span_id=_new_id(),
            trace_id=trace_id or _new_id(),
            name=name,
            parent_span_id=parent_span_id,
            start_time=time.perf_counter(),
        )
        self._spans[span.span_id] = span
        while len(self._spans) > self.max_spans:
            self._spans.popitem(last=False)
        return span.span_id

    def end_span(self, span_id: str, status: str = "ok") -> Span | None:
        """Close a span with a status ("ok", "error", ...)."""
        span = self._spans.get(span_id)
        if span is None:
            return None
        if span.end_time is None:
            span.end_time = time.perf_counter()
        span.status = status
        return span

    def record_attribute(self, span_id: str, key: str, value: Any) -> bool:
        """Attach an attribute to an open span."""
        span = self._spans.get(span_id)
        if span is None:
            return False
        span.attributes[key] = value
        return True

    def get_span(self, span_id: str) -> Span | None:
        return self._spans.get(span_id)

    def get_trace(self, trace_id: str) -> list[Span]:
        """Return all spans belonging to a trace, ordered by start time."""
        spans = [s for s in self._spans.values() if s.trace_id == trace_id]
        spans.sort(key=lambda s: s.start_time)
        return spans

    @property
    def active_span_count(self) -> int:
        return sum(1 for s in self._spans.values() if s.end_time is None)


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    rank = math.ceil(pct / 100.0 * len(sorted_values)) - 1
    rank = max(0, min(len(sorted_values) - 1, rank))
    return sorted_values[rank]


class LatencyTracker:
    """Tracks per-endpoint latency samples and computes percentiles."""

    def __init__(self, window_size: int = 10_000) -> None:
        self.window_size = window_size
        self._samples: dict[str, list[float]] = {}

    def record_latency(self, endpoint: str, duration: float) -> None:
        """Record one request duration (seconds) for an endpoint."""
        samples = self._samples.setdefault(endpoint, [])
        samples.append(duration)
        if len(samples) > self.window_size:
            del samples[: len(samples) - self.window_size]

    def get_percentiles(self, endpoint: str) -> dict[str, float]:
        """Return p50/p95/p99 (seconds) plus count for an endpoint."""
        samples = sorted(self._samples.get(endpoint, []))
        return {
            "count": len(samples),
            "p50": round(_percentile(samples, 50), 6),
            "p95": round(_percentile(samples, 95), 6),
            "p99": round(_percentile(samples, 99), 6),
        }

    def get_all_percentiles(self) -> dict[str, dict[str, float]]:
        return {endpoint: self.get_percentiles(endpoint) for endpoint in self._samples}

    def reset(self, endpoint: str | None = None) -> None:
        if endpoint is None:
            self._samples.clear()
        else:
            self._samples.pop(endpoint, None)


tracer = Tracer()
latency_tracker = LatencyTracker()


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware assigning trace/span IDs and recording latency.

    - Reads ``X-Trace-ID`` from the incoming request or generates one.
    - Starts a server span per request; exposes it via ``request.state``.
    - Returns ``X-Trace-ID`` / ``X-Span-ID`` headers on the response.
    - Feeds per-endpoint durations into :class:`LatencyTracker`.
    """

    SKIP_PATHS = {"/health", "/metrics", "/favicon.ico"}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        trace_id = request.headers.get(TRACE_HEADER) or _new_id()
        method = request.method
        path = request.url.path
        span_id = tracer.start_span(
            f"{method} {path}",
            trace_id=trace_id,
            parent_span_id=request.headers.get(SPAN_HEADER),
        )

        request.state.trace_id = trace_id
        request.state.span_id = span_id
        request.state.correlation_id = trace_id

        tracer.record_attribute(span_id, "http.method", method)
        tracer.record_attribute(span_id, "http.path", path)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            tracer.record_attribute(span_id, "user.id", str(user_id))

        status = "ok"
        try:
            response = await call_next(request)
        except Exception as exc:
            status = "error"
            tracer.record_attribute(span_id, "error.type", type(exc).__name__)
            tracer.end_span(span_id, status=status)
            raise
        finally:
            pass

        duration = time.perf_counter() - tracer.get_span(span_id).start_time
        latency_tracker.record_latency(path, duration)
        tracer.record_attribute(span_id, "http.status_code", response.status_code)
        if response.status_code >= 500:
            status = "error"
        tracer.end_span(span_id, status=status)

        response.headers[TRACE_HEADER] = trace_id
        response.headers[SPAN_HEADER] = span_id
        response.headers["X-Response-Time"] = f"{duration:.4f}s"
        return response
