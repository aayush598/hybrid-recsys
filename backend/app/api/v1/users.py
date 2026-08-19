from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_db
from app.schemas.recommendation import RatingCreate, UserCreate, UserResponse

router = APIRouter()


@router.post("/", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user."""
    existing = await db.execute(
        select(User).where(
            (User.username == user.username) | (User.email == user.email)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username or email already exists")

    from passlib.hash import bcrypt

    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=bcrypt.hash(user.password),
        display_name=user.display_name,
        age=user.age,
        gender=user.gender,
    )
    db.add(new_user)
    await db.flush()

    return UserResponse.model_validate(new_user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get user profile."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.post("/rate")
async def rate_movie(
    rating: RatingCreate,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Record a movie rating from a user."""
    from app.db.models import Rating

    existing = await db.execute(
        select(Rating).where(Rating.user_id == user_id, Rating.movie_id == rating.movie_id)
    )
    existing_rating = existing.scalar_one_or_none()

    if existing_rating:
        existing_rating.rating = rating.rating
    else:
        new_rating = Rating(
            user_id=user_id,
            movie_id=rating.movie_id,
            rating=rating.rating,
        )
        db.add(new_rating)

    return {"status": "recorded", "movie_id": rating.movie_id, "rating": rating.rating}
