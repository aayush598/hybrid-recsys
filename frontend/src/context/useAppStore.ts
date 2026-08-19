import { create } from "zustand";
import type { Algorithm, Movie, RecommendationItem } from "../types";

interface AppState {
  userId: string | null;
  sessionId: string;
  selectedAlgorithm: Algorithm;
  recommendations: RecommendationItem[];
  isLoadingRecommendations: boolean;
  searchQuery: string;
  searchResults: Movie[];
  selectedMovie: Movie | null;
  userRatings: Map<number, number>;
  latency: number | null;

  setUserId: (id: string | null) => void;
  setAlgorithm: (algo: Algorithm) => void;
  setRecommendations: (recs: RecommendationItem[]) => void;
  setIsLoading: (loading: boolean) => void;
  setSearchQuery: (query: string) => void;
  setSearchResults: (results: Movie[]) => void;
  setSelectedMovie: (movie: Movie | null) => void;
  rateMovie: (movieId: number, rating: number) => void;
  setLatency: (ms: number) => void;
}

const generateSessionId = () => `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

export const useAppStore = create<AppState>((set) => ({
  userId: null,
  sessionId: generateSessionId(),
  selectedAlgorithm: "hybrid",
  recommendations: [],
  isLoadingRecommendations: false,
  searchQuery: "",
  searchResults: [],
  selectedMovie: null,
  userRatings: new Map(),
  latency: null,

  setUserId: (id) => set({ userId: id }),
  setAlgorithm: (algo) => set({ selectedAlgorithm: algo }),
  setRecommendations: (recs) => set({ recommendations: recs }),
  setIsLoading: (loading) => set({ isLoadingRecommendations: loading }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setSearchResults: (results) => set({ searchResults: results }),
  setSelectedMovie: (movie) => set({ selectedMovie: movie }),
  rateMovie: (movieId, rating) =>
    set((state) => {
      const newRatings = new Map(state.userRatings);
      newRatings.set(movieId, rating);
      return { userRatings: newRatings };
    }),
  setLatency: (ms) => set({ latency: ms }),
}));
