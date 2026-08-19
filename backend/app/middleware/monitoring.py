from __future__ import annotations

import time

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
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Request monitoring middleware.

    Tracks request count, latency, and active connections.
    Exposes metrics for Prometheus scraping.
    """

    SKIP_PATHS = {"/health", "/metrics", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        start_time = time.time()
        request.state.start_time = start_time

        if PROMETHEUS_AVAILABLE:
            ACTIVE_REQUESTS.inc()

        try:
            response = await call_next(request)
        except Exception as exc:
            if PROMETHEUS_AVAILABLE:
                ACTIVE_REQUESTS.dec()
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

        response.headers["X-Response-Time"] = f"{duration:.4f}s"

        return response
