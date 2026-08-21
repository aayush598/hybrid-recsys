"""CORS configuration helpers.

Builds a configured :class:`CORSMiddleware` for the API with three
presets: ``development`` (allow all), ``production`` (explicit origin
allow-list) and ``strict`` (single origin, limited methods).
"""

from __future__ import annotations

from typing import Callable

from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
]

_STRICT_METHODS = ["GET", "POST"]
_PROD_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]


def get_cors_middleware(
    app: ASGIApp | None = None,
    allowed_origins: list[str] | None = None,
    mode: str = "development",
) -> CORSMiddleware | Callable[[ASGIApp], CORSMiddleware]:
    """Return a configured CORSMiddleware.

    If ``app`` is provided the middleware instance is returned directly;
    otherwise a factory accepting an ASGI app is returned so the result
    can be used as ``app.add_middleware(...)``-style wrapper.
    """
    origins = list(allowed_origins) if allowed_origins else list(DEFAULT_ALLOWED_ORIGINS)

    if mode == "development":
        kwargs = dict(
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    elif mode == "production":
        if not origins:
            raise ValueError("production CORS mode requires allowed_origins")
        kwargs = dict(
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=_PROD_METHODS,
            allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
        )
    elif mode == "strict":
        kwargs = dict(
            allow_origins=[origins[0]] if origins else DEFAULT_ALLOWED_ORIGINS[:1],
            allow_credentials=True,
            allow_methods=_STRICT_METHODS,
            allow_headers=["Authorization", "Content-Type"],
        )
    else:
        raise ValueError(f"Unknown CORS mode: {mode!r}")

    def factory(target_app: ASGIApp) -> CORSMiddleware:
        return CORSMiddleware(target_app, **kwargs)

    return factory(app) if app is not None else factory


__all__ = ["get_cors_middleware", "DEFAULT_ALLOWED_ORIGINS"]
