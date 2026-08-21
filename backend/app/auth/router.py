"""Authentication API endpoints: register, login, profile, token refresh."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
    verify_token,
)
from app.auth.models import UserAuth
from app.db.session import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(description="Username or email address")
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: object
    last_login: object | None = None


def _token_response(user: UserAuth) -> TokenResponse:
    claims = {"sub": user.id, "role": user.role.value, "username": user.username}
    return TokenResponse(
        access_token=create_access_token(claims),
        refresh_token=create_refresh_token(claims),
        expires_in=86400,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Create a new user account and return an access/refresh token pair."""
    result = await db.execute(
        select(UserAuth).where(
            or_(UserAuth.username == payload.username, UserAuth.email == payload.email)
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already registered")

    user = UserAuth(
        username=payload.username,
        email=str(payload.email),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username or email already registered"
        ) from exc
    await db.refresh(user)

    logger.info("User registered", user_id=user.id, username=user.username)
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Authenticate with username/email + password and receive a JWT."""
    result = await db.execute(
        select(UserAuth).where(
            or_(UserAuth.username == payload.username, UserAuth.email == payload.username)
        )
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(user.hashed_password, payload.password):
        logger.warning("Failed login attempt", identifier=payload.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    from datetime import UTC, datetime

    user.last_login = datetime.now(UTC)
    await db.commit()

    logger.info("User logged in", user_id=user.id)
    return _token_response(user)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserAuth = Depends(get_current_user)) -> UserAuth:
    """Return the profile of the currently authenticated user."""
    return current_user


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Exchange a valid refresh token for a new access/refresh token pair."""
    claims = verify_token(payload.refresh_token, expected_type="refresh")
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    result = await db.execute(select(UserAuth).where(UserAuth.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer active")

    logger.info("Token refreshed", user_id=user.id)
    return _token_response(user)
