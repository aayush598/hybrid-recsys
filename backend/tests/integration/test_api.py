from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import Base, engine
from app.main import app


@pytest.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.integration
class TestHealthEndpoint:
    async def test_health_check(self, client: AsyncClient):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "uptime_seconds" in data


@pytest.mark.integration
class TestMovieAPI:
    async def test_list_movies(self, client: AsyncClient):
        response = await client.get("/api/v1/movies/?page=1&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    async def test_search_movies(self, client: AsyncClient):
        response = await client.get("/api/v1/movies/search/?q=love&page=1&page_size=5")
        assert response.status_code == 200

    async def test_get_genres(self, client: AsyncClient):
        response = await client.get("/api/v1/movies/genres/list")
        assert response.status_code == 200
        data = response.json()
        assert "genres" in data

    async def test_get_nonexistent_movie(self, client: AsyncClient):
        response = await client.get("/api/v1/movies/99999999")
        assert response.status_code == 404


@pytest.mark.integration
class TestRecommendationAPI:
    async def test_get_recommendations(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/recommendations/",
            json={"user_id": "1", "num_recommendations": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert "algorithm_used" in data
        assert "latency_ms" in data

    async def test_recommendations_with_algorithm(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/recommendations/",
            json={
                "user_id": "1",
                "num_recommendations": 5,
                "algorithm": "trending",
            },
        )
        assert response.status_code == 200

    async def test_trending(self, client: AsyncClient):
        response = await client.get("/api/v1/recommendations/trending")
        assert response.status_code == 200

    async def test_model_status(self, client: AsyncClient):
        response = await client.get("/api/v1/recommendations/debug/model-status")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "config" in data
        assert "infrastructure" in data


@pytest.mark.integration
class TestUserAPI:
    async def test_create_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/users/",
            json={
                "username": "testuser_integration",
                "email": "test_integration@example.com",
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["username"] == "testuser_integration"
