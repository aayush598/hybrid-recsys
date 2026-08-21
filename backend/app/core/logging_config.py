"""Structured logging configuration.

Provides JSON-structured logging for centralized collection and
human-readable console output for development. Every log record is
enriched with correlation_id, request_id, and user_id pulled from
context variables so requests can be traced across services.
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import uuid
from typing import Any

import structlog

correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
user_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_id", default=None
)

RESERVED_FIELDS = frozenset(
    {
        "timestamp",
        "level",
        "logger",
        "event",
        "correlation_id",
        "request_id",
        "user_id",
        "taskName",
    }
)


def set_correlation_id(value: str | None) -> str | None:
    """Set the correlation ID for the current execution context."""
    correlation_id_var.set(value)
    return value


def set_request_id(value: str | None) -> str | None:
    """Set the request ID for the current execution context."""
    request_id_var.set(value)
    return value


def set_user_id(value: str | None) -> str | None:
    """Set the authenticated user ID for the current execution context."""
    user_id_var.set(value)
    return value


def new_correlation_id() -> str:
    """Generate and bind a fresh correlation ID."""
    return set_correlation_id(uuid.uuid4().hex) or ""


def clear_log_context() -> None:
    """Reset all logging context variables."""
    correlation_id_var.set(None)
    request_id_var.set(None)
    user_id_var.set(None)


class LogContextFilter(logging.Filter):
    """Stdlib logging filter injecting correlation context into records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get() or "-"
        record.request_id = request_id_var.get() or "-"
        record.user_id = user_id_var.get() or "-"
        return True


def _add_log_context(
    logger: Any, method_name: str, event_dict: structlog.types.EventDict
) -> structlog.types.EventDict:
    """Structlog processor merging context variables into the event dict."""
    for var, key in (
        (correlation_id_var, "correlation_id"),
        (request_id_var, "request_id"),
        (user_id_var, "user_id"),
    ):
        value = var.get()
        if value is not None and key not in event_dict:
            event_dict[key] = value
    return event_dict


def json_log_formatter(
    logger: Any, method_name: str, event_dict: structlog.types.EventDict
) -> str:
    """Structlog renderer producing single-line JSON for log shippers."""
    payload: dict[str, Any] = {
        "timestamp": event_dict.pop("timestamp", None),
        "level": event_dict.pop("level", method_name),
        "logger": event_dict.pop("logger", logger or "app"),
        "event": event_dict.pop("event", ""),
    }
    for key in ("correlation_id", "request_id", "user_id"):
        if key in event_dict:
            payload[key] = event_dict.pop(key)
    for key, value in event_dict.items():
        if key not in RESERVED_FIELDS:
            payload[key] = value
    return json.dumps(payload, default=str, separators=(",", ":"))


class JSONLogFormatter(logging.Formatter):
    """Stdlib formatter emitting JSON, passing structlog payloads through."""

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if message.lstrip().startswith("{"):
            try:
                json.loads(message)
                return message
            except ValueError:
                pass
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": message,
            "correlation_id": getattr(record, "correlation_id", "-"),
            "request_id": getattr(record, "request_id", "-"),
            "user_id": getattr(record, "user_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        extra = {
            k: v
            for k, v in record.__dict__.items()
            if k not in RESERVED_FIELDS
            and not k.startswith("_")
            and k
            not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "asctime",
            }
        }
        payload.update(extra)
        return json.dumps(payload, default=str, separators=(",", ":"))


class ConsoleLogFormatter(logging.Formatter):
    """Readable console formatter with correlation ID column."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)-8s [%(correlation_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_logging(
    level: str = "INFO",
    format: str = "json",
    correlation_id: bool = True,
) -> None:
    """Configure structlog and stdlib logging.

    Args:
        level: Log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        format: "json" for machine-readable output, "console"/"text" for dev.
        correlation_id: When True, attach correlation/request/user IDs to
            every log record emitted through any logger.
    """
    log_level = getattr(logging, str(level).upper(), logging.INFO)
    use_json = str(format).lower() not in {"console", "text", "pretty"}

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]
    if correlation_id:
        shared_processors.append(_add_log_context)

    renderer: structlog.types.Processor = (
        json_log_formatter
        if use_json
        else structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
    )

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    root = logging.getLogger()
    root.setLevel(log_level)
    for existing in list(root.handlers):
        root.removeHandler(existing)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(JSONLogFormatter() if use_json else ConsoleLogFormatter())
    if correlation_id:
        handler.addFilter(LogContextFilter())
    root.addHandler(handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        std_logger = logging.getLogger(logger_name)
        std_logger.handlers.clear()
        std_logger.propagate = True
        std_logger.setLevel(log_level)

    logging.getLogger("uvicorn.access").setLevel(max(log_level, logging.WARNING))


def get_logger(name: str, **initial_context: Any) -> structlog.stdlib.BoundLogger:
    """Get a structured logger bound with initial context."""
    return structlog.get_logger(name, **initial_context)


class RequestLogger:
    """Logs HTTP request lifecycle events with correlation ID injection."""

    def __init__(self, logger_name: str = "beautyrec.request") -> None:
        self._logger = get_logger(logger_name)

    @staticmethod
    def _ensure_context(
        correlation_id: str | None, request_id: str | None, user_id: str | None
    ) -> str:
        if correlation_id:
            set_correlation_id(correlation_id)
        elif not correlation_id_var.get():
            set_correlation_id(uuid.uuid4().hex)
        if request_id:
            set_request_id(request_id)
        if user_id:
            set_user_id(user_id)
        return correlation_id_var.get() or ""

    def log_request(
        self,
        method: str,
        path: str,
        correlation_id: str | None = None,
        request_id: str | None = None,
        user_id: str | None = None,
        **fields: Any,
    ) -> str:
        """Log an incoming request; returns the correlation ID used."""
        cid = self._ensure_context(correlation_id, request_id, user_id)
        self._logger.info(
            "http_request",
            method=method,
            path=path,
            correlation_id=cid,
            user_id=user_id,
            **fields,
        )
        return cid

    def log_response(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        correlation_id: str | None = None,
        user_id: str | None = None,
        **fields: Any,
    ) -> None:
        """Log a completed response with timing information."""
        cid = correlation_id or correlation_id_var.get()
        log_fn = self._logger.info
        if status_code >= 500:
            log_fn = self._logger.error
        elif status_code >= 400:
            log_fn = self._logger.warning
        log_fn(
            "http_response",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration_ms, 3),
            correlation_id=cid,
            user_id=user_id,
            **fields,
        )

    def log_error(
        self,
        method: str,
        path: str,
        error: BaseException | str,
        correlation_id: str | None = None,
        user_id: str | None = None,
        **fields: Any,
    ) -> None:
        """Log a request failure with full exception detail."""
        cid = correlation_id or correlation_id_var.get()
        self._logger.error(
            "http_error",
            method=method,
            path=path,
            error=str(error),
            error_type=type(error).__name__ if isinstance(error, BaseException) else "Error",
            correlation_id=cid,
            user_id=user_id,
            exc_info=isinstance(error, BaseException),
            **fields,
        )
