from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MovieBase(BaseModel):
    title: str
    genres: str | None = None
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    vote_average: float | None = None
    vote_count: int | None = None


class MovieResponse(MovieBase):
    id: int
    popularity: float | None = None

    model_config = {"from_attributes": True}


class MovieDetail(MovieResponse):
    tags: list[str] = []
    similar_movies: list[MovieResponse] = []


class RatingCreate(BaseModel):
    movie_id: int = Field(..., gt=0)
    rating: float = Field(..., ge=0.5, le=5.0)


class RatingResponse(BaseModel):
    id: int
    movie_id: int
    rating: float
    timestamp: datetime

    model_config = {"from_attributes": True}


class InteractionCreate(BaseModel):
    movie_id: int = Field(..., gt=0)
    interaction_type: str = Field(..., pattern=r"^(view|click|like|bookmark|share|skip|dwell)$")
    intensity: float = Field(default=1.0, ge=0.0, le=10.0)


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8)
    display_name: str | None = None
    age: int | None = Field(None, ge=13, le=120)
    gender: str | None = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    display_name: str | None = None
    age: int | None = None
    gender: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RecommendationRequest(BaseModel):
    user_id: str | None = None
    session_id: str | None = None
    num_recommendations: int = Field(default=10, ge=1, le=100)
    algorithm: str | None = Field(
        default=None,
        pattern=r"^(collaborative|content_based|neural|hybrid|trending|similar)$",
    )
    exclude_seen: bool = True
    context: dict | None = None


class RecommendationItem(BaseModel):
    movie: MovieResponse
    score: float = Field(..., ge=0.0, le=1.0)
    algorithm: str
    explanation: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class RecommendationResponse(BaseModel):
    user_id: str | None = None
    session_id: str | None = None
    recommendations: list[RecommendationItem]
    algorithm_used: str
    latency_ms: float
    model_version: str = "1.0.0"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ExplanationRequest(BaseModel):
    user_id: str
    movie_id: int


class ExplanationResponse(BaseModel):
    movie_id: int
    movie_title: str
    reasons: list[str]
    contributing_factors: dict[str, float]
    confidence: float


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    models_loaded: dict[str, bool]
    redis_connected: bool
    database_connected: bool


class PaginatedResponse(BaseModel):
    items: list[MovieResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    genres: list[str] | None = None
    year_from: int | None = None
    year_to: int | None = None
    min_rating: float | None = Field(None, ge=0, le=5)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class TrendingResponse(BaseModel):
    trending: list[MovieResponse]
    period: str
    generated_at: datetime


class ABTestVariant(BaseModel):
    experiment: str
    variant: str


class ModelMetrics(BaseModel):
    precision_at_k: dict[int, float]
    recall_at_k: dict[int, float]
    ndcg_at_k: dict[int, float]
    map_at_k: dict[int, float]
    coverage: float
    diversity: float
    novelty: float
    hit_rate: float
