from __future__ import annotations

from fastapi import APIRouter

from app.schemas.recommendation import HealthResponse
from app.services.model_manager import model_manager

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    from app.core.config import get_settings
    from app.main import get_uptime, models_are_loaded

    settings = get_settings()
    models = model_manager.health_check()

    return HealthResponse(
        status="healthy" if models_are_loaded() else "degraded",
        version=settings.APP_VERSION,
        uptime_seconds=round(get_uptime(), 2),
        models_loaded=models,
        redis_connected=True,
        database_connected=True,
    )


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    try:
        from prometheus_client import generate_latest

        return generate_latest()
    except ImportError:
        return {"message": "Prometheus not installed"}
