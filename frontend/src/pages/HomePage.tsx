import { useEffect, useState } from "react";
import { Sparkles, Zap, TrendingUp, Brain, BarChart3, Users, AlertCircle } from "lucide-react";
import { recommendationApi } from "../services/api";
import { useAppStore } from "../context/useAppStore";
import MovieCard from "../components/recommendations/MovieCard";
import type { Algorithm } from "../types";
import toast from "react-hot-toast";

const ALGORITHMS: { value: Algorithm; label: string; icon: any; description: string }[] = [
  { value: "hybrid", label: "AI Hybrid", icon: Sparkles, description: "Best overall — combines all signals" },
  { value: "collaborative", label: "Collaborative", icon: Users, description: "Users like you also enjoyed" },
  { value: "content_based", label: "Content Match", icon: Brain, description: "Similar genres & themes" },
  { value: "trending", label: "Trending", icon: TrendingUp, description: "Popular right now" },
];

export default function HomePage() {
  const {
    recommendations,
    setRecommendations,
    isLoadingRecommendations,
    setIsLoading,
    selectedAlgorithm,
    setAlgorithm,
    latency,
    setLatency,
  } = useAppStore();

  const [error, setError] = useState<string | null>(null);
  const [userId, setUserId] = useState("1");
  const [numRecs, setNumRecs] = useState(20);

  const fetchRecommendations = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await recommendationApi.getRecommendations(
        userId || undefined,
        numRecs,
        selectedAlgorithm
      );
      setRecommendations(response.recommendations);
      setLatency(response.latency_ms);
      toast.success(`Generated ${response.recommendations.length} recommendations in ${response.latency_ms.toFixed(0)}ms`);
    } catch (err: any) {
      setError(err.message || "Failed to fetch recommendations");
      toast.error("Failed to load recommendations");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, [selectedAlgorithm]);

  const stats = [
    {
      label: "Algorithm",
      value: selectedAlgorithm.replace("_", " ").toUpperCase(),
      icon: Brain,
      color: "text-brand-400",
    },
    {
      label: "Latency",
      value: latency ? `${latency.toFixed(0)}ms` : "—",
      icon: Zap,
      color: "text-green-400",
    },
    {
      label: "Results",
      value: String(recommendations.length),
      icon: BarChart3,
      color: "text-blue-400",
    },
    {
      label: "Avg Score",
      value: recommendations.length
        ? `${(recommendations.reduce((s, r) => s + r.score, 0) / recommendations.length * 100).toFixed(0)}%`
        : "—",
      icon: TrendingUp,
      color: "text-purple-400",
    },
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-brand-500/10 via-surface-900 to-surface-900" />
        <div className="absolute inset-0">
          <div className="absolute top-20 left-1/4 w-72 h-72 bg-brand-500/20 rounded-full blur-[128px]" />
          <div className="absolute top-40 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-[128px]" />
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-12">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 bg-brand-500/10 border border-brand-500/20 rounded-full px-4 py-1.5 mb-6">
              <Sparkles className="w-4 h-4 text-brand-400" />
              <span className="text-xs font-medium text-brand-300">
                AI-Powered Recommendation Engine
              </span>
            </div>

            <h1 className="font-display text-5xl md:text-7xl font-bold mb-4">
              <span className="gradient-text">Discover</span>{" "}
              <span className="text-white">Your Next</span>
              <br />
              <span className="text-white">Favorite Movie</span>
            </h1>

            <p className="text-gray-400 text-lg max-w-2xl mx-auto mb-8">
              Hybrid recommendation system combining collaborative filtering,
              content-based matching, and deep learning — inspired by Netflix
              and Orbo.ai's BeautyGPT architecture.
            </p>
          </div>

          {/* Control Panel */}
          <div className="glass-card p-6 max-w-4xl mx-auto mb-8">
            <div className="flex flex-col md:flex-row gap-4 items-center">
              <div className="flex-1">
                <label className="text-xs text-gray-400 mb-1 block">User ID</label>
                <input
                  type="text"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  placeholder="Enter user ID (1-162541)"
                  className="w-full bg-surface-700 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <div className="flex-1">
                <label className="text-xs text-gray-400 mb-1 block">Results</label>
                <select
                  value={numRecs}
                  onChange={(e) => setNumRecs(Number(e.target.value))}
                  className="w-full bg-surface-700 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  <option value={5}>5 movies</option>
                  <option value={10}>10 movies</option>
                  <option value={20}>20 movies</option>
                  <option value={50}>50 movies</option>
                </select>
              </div>
              <div className="flex-1" />
              <button
                onClick={fetchRecommendations}
                disabled={isLoadingRecommendations}
                className="w-full md:w-auto bg-gradient-to-r from-brand-500 to-purple-600 text-white font-semibold px-8 py-2.5 rounded-xl hover:opacity-90 transition-opacity disabled:opacity-50 mt-auto"
              >
                {isLoadingRecommendations ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin">⏳</span> Generating...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4" /> Generate
                  </span>
                )}
              </button>
            </div>

            {/* Algorithm Selector */}
            <div className="flex flex-wrap gap-2 mt-4">
              {ALGORITHMS.map(({ value, label, icon: Icon, description }) => (
                <button
                  key={value}
                  onClick={() => setAlgorithm(value)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                    selectedAlgorithm === value
                      ? "bg-brand-500 text-white shadow-lg shadow-brand-500/25"
                      : "bg-surface-700 text-gray-300 hover:bg-surface-600 border border-white/5"
                  }`}
                  title={description}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Stats Bar */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 max-w-4xl mx-auto mb-12">
            {stats.map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="glass-card p-4 text-center">
                <Icon className={`w-5 h-5 ${color} mx-auto mb-1`} />
                <div className="text-lg font-bold text-white">{value}</div>
                <div className="text-xs text-gray-400">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Error State */}
      {error && (
        <div className="max-w-7xl mx-auto px-4 mb-8">
          <div className="glass-card p-4 border-red-500/30 bg-red-500/10 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <span className="text-sm text-red-300">{error}</span>
          </div>
        </div>
      )}

      {/* Recommendations Grid */}
      {recommendations.length > 0 && (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-1 h-8 bg-gradient-to-b from-brand-500 to-purple-600 rounded-full" />
            <h2 className="font-display text-2xl font-bold text-white">
              Recommended For You
            </h2>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {recommendations.map((rec, idx) => (
              <MovieCard
                key={rec.movie.id}
                movie={rec.movie}
                score={rec.score}
                algorithm={rec.algorithm}
                explanation={rec.explanation || undefined}
                index={idx}
                showScore
              />
            ))}
          </div>
        </section>
      )}

      {/* Empty State */}
      {!isLoadingRecommendations && recommendations.length === 0 && !error && (
        <section className="max-w-7xl mx-auto px-4 pb-20">
          <div className="glass-card p-12 text-center">
            <Sparkles className="w-12 h-12 text-brand-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">
              Ready to Discover
            </h3>
            <p className="text-gray-400">
              Enter a user ID and click Generate to get personalized recommendations.
            </p>
          </div>
        </section>
      )}
    </div>
  );
}
