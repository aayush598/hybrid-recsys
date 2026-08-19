from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Movie
from app.db.session import get_db
from app.schemas.recommendation import (
    MovieDetail,
    MovieResponse,
    PaginatedResponse,
)

router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def list_movies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    genre: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """List movies with optional genre filtering."""
    query = select(Movie)
    count_query = select(func.count(Movie.id))

    if genre:
        query = query.where(Movie.genres.contains(genre))
        count_query = count_query.where(Movie.genres.contains(genre))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    movies = result.scalars().all()

    return PaginatedResponse(
        items=[MovieResponse.model_validate(m) for m in movies],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{movie_id}", response_model=MovieDetail)
async def get_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed movie information."""
    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    movie = result.scalar_one_or_none()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    return MovieDetail(
        id=movie.id,
        title=movie.title,
        genres=movie.genres,
        year=movie.year,
        overview=movie.overview,
        poster_url=movie.poster_url,
        vote_average=movie.vote_average,
        vote_count=movie.vote_count,
        popularity=movie.popularity,
        tags=[],
    )


@router.get("/search/", response_model=PaginatedResponse)
async def search_movies(
    q: str = Query(..., min_length=1, max_length=500),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    genre: str = Query(default=None),
    year_from: int = Query(default=None),
    year_to: int = Query(default=None),
    min_rating: float = Query(default=None, ge=0, le=5),
    db: AsyncSession = Depends(get_db),
):
    """Full-text search across movie titles and genres."""
    query = select(Movie).where(
        or_(
            Movie.title.contains(q),
            Movie.genres.contains(q),
            Movie.overview.contains(q),
        )
    )
    count_query = select(func.count(Movie.id)).where(
        or_(
            Movie.title.contains(q),
            Movie.genres.contains(q),
            Movie.overview.contains(q),
        )
    )

    if genre:
        query = query.where(Movie.genres.contains(genre))
        count_query = count_query.where(Movie.genres.contains(genre))
    if year_from:
        query = query.where(Movie.year >= year_from)
        count_query = count_query.where(Movie.year >= year_from)
    if year_to:
        query = query.where(Movie.year <= year_to)
        count_query = count_query.where(Movie.year <= year_to)
    if min_rating:
        query = query.where(Movie.vote_average >= min_rating)
        count_query = count_query.where(Movie.vote_average >= min_rating)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    movies = result.scalars().all()

    return PaginatedResponse(
        items=[MovieResponse.model_validate(m) for m in movies],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/genres/list")
async def list_genres(db: AsyncSession = Depends(get_db)):
    """Get all available genres."""
    result = await db.execute(select(Movie.genres).where(Movie.genres.isnot(None)))
    all_genres = set()
    for row in result.scalars().all():
        for genre in row.split("|"):
            if genre:
                all_genres.add(genre)
    return {"genres": sorted(all_genres)}
