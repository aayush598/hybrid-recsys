from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger("middleware.security")


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware that adds security headers and request validation.

    Adds standard security headers to all responses:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Content-Security-Policy: default-src 'self'
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    """

    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": "default-src 'self'",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
    }

    DANGEROUS_PATHS = {
        "/etc/passwd",
        "/etc/shadow",
        "/proc/self/environ",
        "/.env",
        "/wp-admin",
    }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        request.state.start_time = time.time()

        path = request.url.path.lower()
        for dangerous in self.DANGEROUS_PATHS:
            if dangerous in path:
                logger.warning("Blocked dangerous path access", path=path, request_id=request_id)
                return Response(status_code=404)

        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("content-length", "0")
            if int(content_length) > 10 * 1024 * 1024:
                return Response(status_code=413, content="Request too large")

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        for header, value in self.SECURITY_HEADERS.items():
            response.headers[header] = value

        return response
