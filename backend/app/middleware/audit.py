"""Audit logging middleware and model.

``AuditMiddleware`` records every write operation (POST/PUT/DELETE/PATCH)
with the acting user, timestamp, endpoint, response status, client IP and
user agent. Entries are persisted to the ``audit_logs`` table best-effort;
a persistence failure never breaks the live request.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import structlog
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.auth import verify_token
from app.db.session import Base, async_session_factory

logger = structlog.get_logger("middleware.audit")

AUDITED_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH"})


class AuditLog(Base):
    """Persistent audit trail of write operations."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    details: Mapped[str | None] = mapped_column(Text, nullable=True)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _extract_user_id(request: Request) -> str | None:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return None
    try:
        payload = verify_token(auth_header[7:].strip(), expected_type="access")
        return payload.get("sub")
    except Exception:
        return None


class AuditMiddleware(BaseHTTPMiddleware):
    """Log all write operations (POST/PUT/DELETE/PATCH) to the audit trail."""

    def __init__(self, app, include_query_params: bool = True) -> None:
        super().__init__(app)
        self.include_query_params = include_query_params

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        if request.method in AUDITED_METHODS:
            try:
                await self._record(request, response)
            except Exception as exc:  # noqa: BLE001 - auditing must never break requests
                logger.error("Audit log persistence failed", error=str(exc))
        return response

    async def _record(self, request: Request, response: Response) -> None:
        details: dict[str, object] = {
            "query": str(request.url.query) if self.include_query_params and request.url.query else None,
            "path_params": dict(getattr(request, "path_params", {}) or {}),
            "request_id": getattr(request.state, "request_id", None),
        }

        entry = AuditLog(
            user_id=_extract_user_id(request),
            action=f"{request.method} {request.url.path}",
            endpoint=str(request.url.path),
            method=request.method,
            status_code=response.status_code,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            timestamp=datetime.now(UTC),
            details=json.dumps({k: v for k, v in details.items() if v is not None}, default=str),
        )

        async with async_session_factory() as session:
            session.add(entry)
            await session.commit()

        logger.info(
            "audit",
            user_id=entry.user_id,
            action=entry.action,
            status_code=entry.status_code,
            ip_address=entry.ip_address,
        )
