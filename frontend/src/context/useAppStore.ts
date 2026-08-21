import { create } from "zustand";
import type { Algorithm, RecommendationItem } from "../types";

interface AppState {
  userId: string | null;
  sessionId: string;
  selectedAlgorithm: Algorithm;
  recommendations: RecommendationItem[];
  isLoadingRecommendations: boolean;
  searchQuery: string;
  latency: number | null;

  setUserId: (id: string | null) => void;
  setAlgorithm: (algo: Algorithm) => void;
  setRecommendations: (recs: RecommendationItem[]) => void;
  setIsLoading: (loading: boolean) => void;
  setSearchQuery: (query: string) => void;
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
  latency: null,

  setUserId: (id) => set({ userId: id }),
  setAlgorithm: (algo) => set({ selectedAlgorithm: algo }),
  setRecommendations: (recs) => set({ recommendations: recs }),
  setIsLoading: (loading) => set({ isLoadingRecommendations: loading }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setLatency: (ms) => set({ latency: ms }),
}));
