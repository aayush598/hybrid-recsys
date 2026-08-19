from __future__ import annotations

import logging

from app.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)


class ModelManager:
    """Singleton model manager for the application.

    Manages the lifecycle of all ML models including loading,
    training, versioning, and health checks.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not ModelManager._initialized:
            self.recommendation_service = RecommendationService()
            ModelManager._initialized = True

    async def initialize(self) -> None:
        """Initialize all models."""
        from app.db.session import get_db_context

        async with get_db_context() as db:
            await self.recommendation_service.initialize(db)

    def get_service(self) -> RecommendationService:
        return self.recommendation_service

    def health_check(self) -> dict[str, bool]:
        """Check health of all models."""
        service = self.recommendation_service
        return {
            "collaborative_filtering": service.cf_model.is_loaded,
            "content_based": service.content_model.is_loaded,
            "trending": service.trending_model.is_loaded,
            "hybrid_ensemble": service.hybrid.is_loaded,
        }


model_manager = ModelManager()
