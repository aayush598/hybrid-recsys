"""Load testing with Locust.

Run: locust -f tests/load/locustfile.py --host=http://localhost:8000
"""

from locust import HttpUser, between, tag, task


class RecommendationUser(HttpUser):
    """Simulates a real user interacting with the recommendation system."""

    wait_time = between(1, 3)
    host = "http://localhost:8000"

    def on_start(self):
        self.user_id = str(self.environment.runner.user_count if self.environment.runner else 1)

    @tag("recommendations")
    @task(10)
    def get_hybrid_recommendations(self):
        self.client.post(
            "/api/v1/recommendations/",
            json={
                "user_id": self.user_id,
                "num_recommendations": 10,
                "algorithm": "hybrid",
            },
            name="/api/v1/recommendations/ [hybrid]",
        )

    @tag("recommendations")
    @task(5)
    def get_collaborative_recommendations(self):
        self.client.post(
            "/api/v1/recommendations/",
            json={
                "user_id": self.user_id,
                "num_recommendations": 10,
                "algorithm": "collaborative",
            },
            name="/api/v1/recommendations/ [collaborative]",
        )

    @tag("recommendations")
    @task(3)
    def get_content_recommendations(self):
        self.client.post(
            "/api/v1/recommendations/",
            json={
                "user_id": self.user_id,
                "num_recommendations": 10,
                "algorithm": "content_based",
            },
            name="/api/v1/recommendations/ [content]",
        )

    @tag("recommendations")
    @task(4)
    def get_trending(self):
        self.client.get(
            "/api/v1/recommendations/trending",
            name="/api/v1/recommendations/trending",
        )

    @tag("movies")
    @task(8)
    def browse_movies(self):
        self.client.get(
            "/api/v1/movies/?page=1&page_size=20",
            name="/api/v1/movies/",
        )

    @tag("movies")
    @task(6)
    def search_movies(self):
        queries = ["action", "comedy", "drama", "love", "war", "space"]
        query = queries[self.environment.runner.user_count % len(queries)] if self.environment.runner else "action"
        self.client.get(
            f"/api/v1/movies/search/?q={query}",
            name="/api/v1/movies/search/",
        )

    @tag("movies")
    @task(3)
    def get_movie_detail(self):
        movie_ids = [260, 1196, 2571, 1210, 480]
        movie_id = movie_ids[self.environment.runner.user_count % len(movie_ids)] if self.environment.runner else 260
        self.client.get(
            f"/api/v1/movies/{movie_id}",
            name="/api/v1/movies/{id}",
        )

    @tag("similar")
    @task(4)
    def get_similar_movies(self):
        self.client.get(
            "/api/v1/recommendations/similar/260?top_k=10",
            name="/api/v1/recommendations/similar/{id}",
        )

    @tag("health")
    @task(1)
    def health_check(self):
        self.client.get("/health", name="/health")


class APIOnlyUser(HttpUser):
    """Lighter user for API endpoint testing."""

    wait_time = between(0.5, 1.5)
    host = "http://localhost:8000"

    @task(5)
    def get_genres(self):
        self.client.get("/api/v1/movies/genres/list")

    @task(3)
    def health(self):
        self.client.get("/health")

    @task(2)
    def model_status(self):
        self.client.get("/api/v1/recommendations/debug/model-status")
