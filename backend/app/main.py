from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import BeautyRecException
from app.core.logging import get_logger, setup_logging
from app.db.session import close_db, init_db
from app.middleware.monitoring import MonitoringMiddleware
from app.middleware.security import SecurityMiddleware
from app.serving.rate_limiter import RateLimitMiddleware

settings = get_settings()
logger = get_logger(__name__)

_models_loaded = False
_start_time = time.time()


def create_app() -> FastAPI:
    """Application factory pattern.

    Creates and configures the FastAPI application with all middleware,
    routes, lifecycle events, and exception handlers.
    """
    setup_logging(settings.LOG_LEVEL)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        global _models_loaded
        logger.info("Starting BeautyRec application", version=settings.APP_VERSION)
        await init_db()
        _models_loaded = await _initialize_models()
        _setup_default_experiments()
        logger.info("Application startup complete", models_loaded=_models_loaded)
        yield
        logger.info("Shutting down BeautyRec application")
        await close_db()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Production-grade hybrid recommendation system inspired by Netflix & Orbo.ai BeautyGPT",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "Health", "description": "System health and monitoring"},
            {"name": "Recommendations", "description": "AI-powered recommendation generation"},
            {"name": "Movies", "description": "Movie browsing, search, and metadata"},
            {"name": "Users", "description": "User management and profiles"},
            {"name": "WebSocket", "description": "Real-time recommendation streaming"},
            {"name": "A/B Testing", "description": "Experiment management and results"},
        ],
    )

    # Exception handler
    @app.exception_handler(BeautyRecException)
    async def beautyrec_exception_handler(request: Request, exc: BeautyRecException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "error_type": exc.__class__.__name__, "detail_extra": exc.detail},
        )

    # Middleware stack (order matters: last added = first executed)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if settings.is_production:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*.orbo.ai", "*.localhost"])

    app.add_middleware(RateLimitMiddleware, requests_per_minute=120, burst_size=20)
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(MonitoringMiddleware)

    # API Routes
    from app.api.v1.health import router as health_router
    from app.api.v1.movies import router as movies_router
    from app.api.v1.recommendations import router as rec_router
    from app.api.v1.users import router as users_router
    from app.api.v1.websocket.realtime import router as ws_router

    app.include_router(health_router, prefix="/api/v1", tags=["Health"])
    app.include_router(rec_router, prefix="/api/v1/recommendations", tags=["Recommendations"])
    app.include_router(movies_router, prefix="/api/v1/movies", tags=["Movies"])
    app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(ws_router, tags=["WebSocket"])

    # A/B Test endpoints
    from app.api.v1.ab_testing import router as ab_router
    app.include_router(ab_router, prefix="/api/v1/experiments", tags=["A/B Testing"])

    return app


def _setup_default_experiments() -> None:
    """Create default A/B test experiments."""
    from app.serving.ab_testing.manager import ab_test_manager

    ab_test_manager.create_experiment(
        "algorithm_selection",
        [
            {"name": "hybrid", "weight": 0.4, "config": {"algorithm": "hybrid"}},
            {"name": "collaborative", "weight": 0.2, "config": {"algorithm": "collaborative"}},
            {"name": "content_based", "weight": 0.2, "config": {"algorithm": "content_based"}},
            {"name": "trending", "weight": 0.2, "config": {"algorithm": "trending"}},
        ],
        description="Test which algorithm performs best overall",
    )

    ab_test_manager.create_experiment(
        "result_count",
        [
            {"name": "10_results", "weight": 0.5, "config": {"num_recommendations": 10}},
            {"name": "20_results", "weight": 0.5, "config": {"num_recommendations": 20}},
        ],
        description="Test optimal number of recommendations to show",
    )


async def _initialize_models() -> bool:
    """Load or train ML models on startup."""
    from app.services.model_manager import model_manager

    try:
        await model_manager.initialize()
        return True
    except Exception as e:
        logger.error(f"Model initialization failed: {e}")
        return False


app = create_app()


def get_uptime() -> float:
    return time.time() - _start_time


def models_are_loaded() -> bool:
    return _models_loaded
