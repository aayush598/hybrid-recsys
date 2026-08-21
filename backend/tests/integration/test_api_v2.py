"""Integration tests for the v2 API surface: authentication endpoints."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

USER_PAYLOAD = {
    "username": "movie_fan",
    "email": "fan@example.com",
    "password": "Sup3r-Secret!",
}


@pytest.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    from app.auth import get_db as auth_get_db
    from app.auth.router import get_db as router_get_db, router as auth_router
    from app.db.session import Base

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app = FastAPI()
    app.include_router(auth_router)
    # The same dependency object is imported into two modules; override both.
    app.dependency_overrides[router_get_db] = override_get_db
    app.dependency_overrides[auth_get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http

    await engine.dispose()


async def _register(client: AsyncClient, **overrides) -> dict:
    payload = {**USER_PAYLOAD, **overrides}
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


class TestRegistration:
    async def test_register_returns_token_pair(self, client):
        body = await _register(client)
        assert body["token_type"] == "bearer"
        assert body["access_token"] and body["refresh_token"]
        assert body["expires_in"] > 0

    async def test_duplicate_username_or_email_conflict(self, client):
        await _register(client)
        conflict = await client.post("/auth/register", json=USER_PAYLOAD)
        assert conflict.status_code == 409

        same_email = await client.post(
            "/auth/register",
            json={**USER_PAYLOAD, "username": "someone_else"},
        )
        assert same_email.status_code == 409

    async def test_short_password_rejected(self, client):
        response = await client.post(
            "/auth/register", json={**USER_PAYLOAD, "password": "short"}
        )
        assert response.status_code == 422

    async def test_invalid_email_rejected(self, client):
        response = await client.post(
            "/auth/register", json={**USER_PAYLOAD, "email": "not-an-email"}
        )
        assert response.status_code == 422

    async def test_short_username_rejected(self, client):
        response = await client.post(
            "/auth/register", json={**USER_PAYLOAD, "username": "ab"}
        )
        assert response.status_code == 422


class TestLogin:
    async def test_login_with_username_and_email(self, client):
        await _register(client)
        by_username = await client.post(
            "/auth/login",
            json={"username": USER_PAYLOAD["username"], "password": USER_PAYLOAD["password"]},
        )
        by_email = await client.post(
            "/auth/login",
            json={"username": USER_PAYLOAD["email"], "password": USER_PAYLOAD["password"]},
        )
        assert by_username.status_code == 200
        assert by_email.status_code == 200
        assert by_username.json()["access_token"]

    async def test_wrong_password_unauthorized(self, client):
        await _register(client)
        response = await client.post(
            "/auth/login",
            json={"username": USER_PAYLOAD["username"], "password": "WrongPassword1!"},
        )
        assert response.status_code == 401

    async def test_unknown_user_unauthorized(self, client):
        response = await client.post(
            "/auth/login", json={"username": "ghost", "password": "Whatever123!"}
        )
        assert response.status_code == 401


class TestProfileAndRefresh:
    async def test_me_returns_registered_user(self, client):
        tokens = await _register(client)
        me = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert me.status_code == 200
        profile = me.json()
        assert profile["username"] == USER_PAYLOAD["username"]
        assert profile["email"] == USER_PAYLOAD["email"]
        assert profile["is_active"] is True

    async def test_me_requires_token(self, client):
        response = await client.get("/auth/me")
        assert response.status_code == 401

    async def test_me_rejects_garbage_token(self, client):
        response = await client.get("/auth/me", headers={"Authorization": "Bearer junk"})
        assert response.status_code == 401

    async def test_refresh_rotates_tokens(self, client):
        tokens = await _register(client)
        refreshed = await client.post(
            "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert refreshed.status_code == 200
        new_tokens = refreshed.json()
        assert new_tokens["access_token"]
        assert new_tokens["token_type"] == "bearer"

        me = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
        )
        assert me.status_code == 200

    async def test_access_token_cannot_refresh(self, client):
        tokens = await _register(client)
        response = await client.post(
            "/auth/refresh", json={"refresh_token": tokens["access_token"]}
        )
        assert response.status_code == 401


class TestEndToEndFlow:
    async def test_register_login_profile_roundtrip(self, client):
        from app.auth import verify_token

        tokens = await _register(client)
        login = await client.post(
            "/auth/login",
            json={"username": USER_PAYLOAD["username"], "password": USER_PAYLOAD["password"]},
        )
        assert login.status_code == 200

        access = login.json()["access_token"]
        claims = verify_token(access)
        me = await client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
        assert me.status_code == 200
        profile = me.json()
        assert claims["sub"] == profile["id"]
        assert claims["username"] == profile["username"]
