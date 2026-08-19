from __future__ import annotations

from typing import Any, Optional


class BeautyRecException(Exception):
    """Base exception for BeautyRec application."""

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        status_code: int = 500,
        detail: Any | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)


class ModelNotLoadedError(BeautyRecException):
    def __init__(self, model_name: str = "unknown"):
        super().__init__(
            message=f"Model '{model_name}' is not loaded. Please train or load the model first.",
            status_code=503,
            detail={"model": model_name, "error_type": "model_not_loaded"},
        )


class DataNotFoundError(BeautyRecException):
    def __init__(self, resource: str, resource_id: Any = None):
        msg = f"{resource} not found"
        if resource_id:
            msg += f" (id={resource_id})"
        super().__init__(message=msg, status_code=404)


class ValidationError(BeautyRecException):
    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message=message, status_code=422, detail=detail)


class RateLimitExceededError(BeautyRecException):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message=f"Rate limit exceeded. Please retry after {retry_after} seconds.",
            status_code=429,
            detail={"retry_after": retry_after},
        )


class CircuitBreakerOpenError(BeautyRecException):
    def __init__(self, service_name: str):
        super().__init__(
            message=f"Service '{service_name}' is temporarily unavailable (circuit breaker open).",
            status_code=503,
            detail={"service": service_name, "error_type": "circuit_breaker_open"},
        )


class FeatureStoreError(BeautyRecException):
    def __init__(self, message: str = "Feature store operation failed"):
        super().__init__(message=message, status_code=500)


class PipelineError(BeautyRecException):
    def __init__(self, stage: str, message: str = ""):
        super().__init__(
            message=f"Pipeline error at stage '{stage}': {message}" if message else f"Pipeline error at stage '{stage}'",
            status_code=500,
            detail={"stage": stage},
        )


class AuthenticationError(BeautyRecException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message=message, status_code=401)


class AuthorizationError(BeautyRecException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message, status_code=403)


class ConflictError(BeautyRecException):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message=message, status_code=409)


class TimeoutError(BeautyRecException):
    def __init__(self, operation: str = "request", timeout_s: float = 30.0):
        super().__init__(
            message=f"Operation '{operation}' timed out after {timeout_s}s",
            status_code=504,
        )
