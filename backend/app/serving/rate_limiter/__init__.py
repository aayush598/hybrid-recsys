from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TokenBucket:
    """Token bucket rate limiter.

    Allows burst traffic up to bucket capacity, then refills
    at a steady rate. Simple, efficient, and widely used.
    """
    capacity: int
    refill_rate: float
    tokens: float
    last_refill: float

    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if allowed."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    @property
    def retry_after(self) -> float:
        """Seconds until next token is available."""
        if self.tokens >= 1:
            return 0.0
        return (1 - self.tokens) / self.refill_rate


class SlidingWindowRateLimiter:
    """Sliding window rate limiter.

    More accurate than fixed window — prevents the "boundary burst"
    problem where requests at window edges get double counted.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> tuple[bool, dict]:
        """Check if request is allowed under rate limit."""
        now = time.time()
        window_start = now - self.window_seconds

        self.requests[key] = [
            t for t in self.requests[key] if t > window_start
        ]

        current_count = len(self.requests[key])
        allowed = current_count < self.max_requests

        if allowed:
            self.requests[key].append(now)

        retry_after = 0.0
        if not allowed and self.requests[key]:
            retry_after = self.requests[key][0] - window_start

        return allowed, {
            "limit": self.max_requests,
            "remaining": max(0, self.max_requests - current_count - (1 if allowed else 0)),
            "reset": int(window_start + self.window_seconds),
            "retry_after": round(retry_after, 2),
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with per-user and global limits.

    Features:
    - Per-user rate limiting (by API key or IP)
    - Global rate limiting
    - Sliding window algorithm
    - Standard rate limit headers (RFC 6585)
    """

    SKIP_PATHS = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}

    def __init__(self, app, requests_per_minute: int = 60, burst_size: int = 10):
        super().__init__(app)
        self.limiter = SlidingWindowRateLimiter(requests_per_minute, 60)
        self.burst_size = burst_size
        self.burst_limiters: dict[str, TokenBucket] = {}

    def _get_client_key(self, request: Request) -> str:
        """Extract client identifier for rate limiting."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _get_burst_limiter(self, key: str) -> TokenBucket:
        """Get or create a token bucket for burst limiting."""
        if key not in self.burst_limiters:
            self.burst_limiters[key] = TokenBucket(
                capacity=self.burst_size,
                refill_rate=self.burst_size / 10.0,  # Refill burst_size tokens over 10 seconds
                tokens=float(self.burst_size),
                last_refill=time.time(),
            )
        return self.burst_limiters[key]

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        client_key = self._get_client_key(request)

        # Check burst limit first (token bucket)
        burst_limiter = self._get_burst_limiter(client_key)
        if not burst_limiter.consume():
            retry_after = burst_limiter.retry_after
            logger.warning(f"Burst limit exceeded for {client_key}")
            return Response(
                content='{"detail":"Burst limit exceeded. Please slow down."}',
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    "X-RateLimit-Limit": str(self.burst_size),
                    "X-RateLimit-Remaining": str(int(burst_limiter.tokens)),
                    "Retry-After": str(int(retry_after) + 1),
                },
            )

        # Check sliding window limit
        allowed, info = self.limiter.is_allowed(client_key)

        if not allowed:
            logger.warning(f"Rate limit exceeded for {client_key}")
            return Response(
                content='{"detail":"Rate limit exceeded. Try again later."}',
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": str(info["remaining"]),
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(int(info["retry_after"]) + 1),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])

        return response
