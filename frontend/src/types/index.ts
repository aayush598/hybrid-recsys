export interface Movie {
  id: number;
  title: string;
  genres: string | null;
  year: number | null;
  overview: string | null;
  poster_url: string | null;
  vote_average: number | null;
  vote_count: number | null;
  popularity: number | null;
  tags?: string[];
  similar_movies?: Movie[];
}

export interface RecommendationItem {
  movie: Movie;
  score: number;
  algorithm: string;
  explanation: string | null;
  confidence: number;
}

export interface RecommendationResponse {
  user_id: string | null;
  session_id: string | null;
  recommendations: RecommendationItem[];
  algorithm_used: string;
  latency_ms: number;
  model_version: string;
  generated_at: string;
}

export interface PaginatedResponse {
  items: Movie[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface HealthStatus {
  status: string;
  version: string;
  uptime_seconds: number;
  models_loaded: Record<string, boolean>;
  redis_connected: boolean;
  database_connected: boolean;
}

export interface UserProfile {
  user_id: string;
  total_ratings: number;
  avg_rating: number;
  genre_preferences: Record<string, number>;
  recent_movies: number[];
}

export type Algorithm = "hybrid" | "collaborative" | "content_based" | "trending" | "similar";

export interface TrendingResponse {
  trending: Movie[];
  period: string;
  generated_at: string;
}

export interface DebugStatus {
  models: Record<string, boolean>;
  infrastructure: Record<string, boolean>;
  config: Record<string, any>;
  cache_stats?: Record<string, any>;
  feature_store_stats?: Record<string, any>;
  bandit_stats?: Record<string, any>;
  streaming_stats?: Record<string, any>;
  monitoring_report?: Record<string, any>;
}
