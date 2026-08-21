from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

try:
    from prometheus_client import Counter, Gauge, Histogram

    REQUEST_COUNT = Counter(
        "beautyrec_http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status_code"],
    )
    REQUEST_LATENCY = Histogram(
        "beautyrec_http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "endpoint"],
        buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )
    RECOMMENDATION_LATENCY = Histogram(
        "beautyrec_recommendation_latency_seconds",
        "Recommendation generation latency",
        ["algorithm"],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
    )
    ACTIVE_REQUESTS = Gauge(
        "beautyrec_active_requests",
        "Number of concurrent requests",
    )
    RECOMMENDATION_COUNT = Counter(
        "beautyrec_recommendations_total",
        "Total recommendations generated",
        ["algorithm"],
    )
    CACHE_HITS = Counter(
        "beautyrec_cache_hits_total",
        "Total cache hits",
        ["level"],
    )
    ERROR_COUNT = Counter(
        "beautyrec_errors_total",
        "Total errors by type",
        ["method", "endpoint", "status_code"],
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Request monitoring middleware.

    Tracks request count, latency, active connections, and errors.
    Generates correlation IDs for distributed tracing.
    Exposes metrics for Prometheus scraping.
    """

    SKIP_PATHS = {"/health", "/metrics", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        start_time = time.time()
        request.state.start_time = start_time

        if PROMETHEUS_AVAILABLE:
            ACTIVE_REQUESTS.inc()

        try:
            response = await call_next(request)
        except Exception as exc:
            if PROMETHEUS_AVAILABLE:
                ACTIVE_REQUESTS.dec()
                ERROR_COUNT.labels(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code="500",
                ).inc()
            raise exc

        duration = time.time() - start_time

        if PROMETHEUS_AVAILABLE:
            ACTIVE_REQUESTS.dec()
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
            ).inc()
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.url.path,
            ).observe(duration)
            if response.status_code >= 400:
                ERROR_COUNT.labels(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=str(response.status_code),
                ).inc()

        response.headers["X-Response-Time"] = f"{duration:.4f}s"
        response.headers["X-Correlation-ID"] = correlation_id

        return response
