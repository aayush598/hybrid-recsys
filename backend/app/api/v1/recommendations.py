from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Movie
from app.db.session import get_db
from app.schemas.recommendation import (
    InteractionCreate,
    MovieResponse,
    RatingCreate,
    RecommendationRequest,
    RecommendationResponse,
    TrendingResponse,
)
from app.services.model_manager import model_manager

router = APIRouter()
settings = get_settings()


@router.post("/", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate personalized recommendations.

    Supports multiple algorithms:
    - hybrid: Best overall (default)
    - collaborative: User-based collaborative filtering
    - content_based: Content similarity matching
    - trending: Popularity-based recommendations
    """
    service = model_manager.get_service()
    return await service.get_recommendations(
        db=db,
        user_id=request.user_id,
        session_id=request.session_id,
        num_recommendations=request.num_recommendations,
        algorithm=request.algorithm,
        exclude_seen=request.exclude_seen,
    )


@router.get("/similar/{movie_id}")
async def get_similar_movies(
    movie_id: int,
    top_k: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Find movies similar to a given movie using hybrid similarity."""
    service = model_manager.get_service()
    results = await service.get_similar_items(db, movie_id, top_k)
    if not results:
        raise HTTPException(status_code=404, detail="Movie not found or no similar items")
    return {"movie_id": movie_id, "similar": results}


@router.post("/interact")
async def record_interaction(
    interaction: InteractionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Record a user interaction (view, like, bookmark, etc.)."""
    service = model_manager.get_service()
    await service.record_interaction(
        db=db,
        user_id="anonymous",
        movie_id=interaction.movie_id,
        interaction_type=interaction.interaction_type,
        intensity=interaction.intensity,
    )
    return {"status": "recorded"}


@router.get("/user/{user_id}/profile")
async def get_user_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get user preference profile for transparency."""
    service = model_manager.get_service()
    profile = await service.get_user_profile(db, user_id)
    return profile


@router.post("/user/{user_id}/rate")
async def rate_movie(
    user_id: str,
    rating_data: RatingCreate,
    db: AsyncSession = Depends(get_db),
):
    """Rate a movie (updates recommendation system)."""
    service = model_manager.get_service()
    await service.record_rating(
        db=db,
        user_id=user_id,
        movie_id=rating_data.movie_id,
        rating=rating_data.rating,
    )
    return {"status": "rated", "movie_id": rating_data.movie_id, "rating": rating_data.rating}


@router.get("/trending", response_model=TrendingResponse)
async def get_trending(
    period: str = Query(default="30d", pattern=r"^\d+[dwm]$"),
    db: AsyncSession = Depends(get_db),
):
    """Get currently trending movies."""
    service = model_manager.get_service()
    trending_recs = service.trending_model.predict(top_k=20)

    movies = []
    for movie_id, score in trending_recs:
        result = await db.execute(select(Movie).where(Movie.id == movie_id))
        movie = result.scalar_one_or_none()
        if movie:
            movies.append(MovieResponse.model_validate(movie))

    return TrendingResponse(
        trending=movies,
        period=period,
        generated_at=datetime.utcnow(),
    )


@router.get("/debug/model-status")
async def model_status(db: AsyncSession = Depends(get_db)):
    """Debug endpoint showing model and infrastructure status."""
    service = model_manager.get_service()
    status = await service.get_debug_status(db)
    return status
