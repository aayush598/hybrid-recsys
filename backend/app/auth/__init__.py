"""JWT authentication system for BeautyRec.

Provides token creation/verification, password hashing (passlib bcrypt),
and the ``get_current_user`` FastAPI dependency.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db

from .models import UserAuth

__all__ = [
    "JWT_ALGORITHM",
    "JWT_SECRET",
    "REFRESH_TOKEN_EXPIRY",
    "TOKEN_EXPIRY",
    "create_access_token",
    "create_refresh_token",
    "get_current_user",
    "hash_password",
    "oauth2_scheme",
    "verify_password",
    "verify_token",
]

settings = get_settings()
logger = structlog.get_logger(__name__)

# Secret and algorithm sourced from application settings (env-driven).
JWT_SECRET: str = settings.SECRET_KEY
JWT_ALGORITHM: str = settings.ALGORITHM  # HS256

# Default access-token lifetime: 24 hours.
TOKEN_EXPIRY: timedelta = timedelta(hours=24)
REFRESH_TOKEN_EXPIRY: timedelta = timedelta(days=7)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(hashed_password: str, plain_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Token creation / verification
# ---------------------------------------------------------------------------
def _build_claims(data: dict[str, Any], expires_delta: timedelta, token_type: str) -> dict[str, Any]:
    now = datetime.now(UTC)
    claims = data.copy()
    claims.update(
        {
            "iat": now,
            "exp": now + expires_delta,
            "type": token_type,
            "jti": f"{now.timestamp():.0f}",
        }
    )
    return claims


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token.

    ``data`` should include identity claims such as ``sub`` (user id) and ``role``.
    """
    claims = _build_claims(data, expires_delta or TOKEN_EXPIRY, token_type="access")
    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT refresh token with a longer lifetime."""
    claims = _build_claims(data, expires_delta or REFRESH_TOKEN_EXPIRY, token_type="refresh")
    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    """Decode and validate a JWT, returning its payload.

    Raises ``HTTPException 401`` for expired, invalid, or wrong-type tokens.
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload: dict[str, Any] = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except JWTError as exc:
        logger.warning("JWT verification failed", error=str(exc))
        raise credentials_error from exc

    if expected_type is not None and payload.get("type") != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token type, expected '{expected_type}'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserAuth:
    """Resolve the authenticated ``UserAuth`` from the Authorization header."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(token, expected_type="access")
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(UserAuth).where(UserAuth.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user
