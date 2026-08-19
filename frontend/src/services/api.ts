import axios from "axios";
import type {
  RecommendationResponse,
  PaginatedResponse,
  HealthStatus,
  UserProfile,
  Movie,
  Algorithm,
} from "../types";

const api = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API Error:", error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const recommendationApi = {
  getRecommendations: async (
    userId?: string,
    numRecommendations: number = 10,
    algorithm?: Algorithm
  ): Promise<RecommendationResponse> => {
    const { data } = await api.post("/recommendations/", {
      user_id: userId || undefined,
      num_recommendations: numRecommendations,
      algorithm: algorithm || undefined,
      exclude_seen: true,
    });
    return data;
  },

  getSimilarMovies: async (
    movieId: number,
    topK: number = 10
  ): Promise<{ movie_id: number; similar: any[] }> => {
    const { data } = await api.get(
      `/recommendations/similar/${movieId}?top_k=${topK}`
    );
    return data;
  },

  getTrending: async (period: string = "30d") => {
    const { data } = await api.get(`/recommendations/trending?period=${period}`);
    return data;
  },

  recordInteraction: async (
    userId: string,
    movieId: number,
    interactionType: string,
    intensity: number = 1.0
  ) => {
    await api.post("/recommendations/interact", {
      user_id: userId,
      movie_id: movieId,
      interaction_type: interactionType,
      intensity,
    });
  },

  getUserProfile: async (userId: string): Promise<UserProfile> => {
    const { data } = await api.get(`/recommendations/user/${userId}/profile`);
    return data;
  },

  getModelStatus: async () => {
    const { data } = await api.get("/recommendations/debug/model-status");
    return data;
  },
};

export const movieApi = {
  listMovies: async (
    page: number = 1,
    pageSize: number = 20,
    genre?: string
  ): Promise<PaginatedResponse> => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (genre) params.append("genre", genre);
    const { data } = await api.get(`/movies/?${params}`);
    return data;
  },

  getMovie: async (movieId: number): Promise<Movie> => {
    const { data } = await api.get(`/movies/${movieId}`);
    return data;
  },

  searchMovies: async (
    query: string,
    page: number = 1,
    pageSize: number = 20,
    genre?: string
  ): Promise<PaginatedResponse> => {
    const params = new URLSearchParams({
      q: query,
      page: String(page),
      page_size: String(pageSize),
    });
    if (genre) params.append("genre", genre);
    const { data } = await api.get(`/movies/search/?${params}`);
    return data;
  },

  getGenres: async (): Promise<{ genres: string[] }> => {
    const { data } = await api.get("/movies/genres/list");
    return data;
  },
};

export const healthApi = {
  check: async (): Promise<HealthStatus> => {
    const { data } = await api.get("/health");
    return data;
  },
};

export default api;
