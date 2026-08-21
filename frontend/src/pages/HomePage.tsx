import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Sparkles,
  Zap,
  TrendingUp,
  Brain,
  BarChart3,
  Users,
  AlertCircle,
  ChevronDown,
  ArrowRight,
} from "lucide-react";
import { recommendationApi } from "../services/api";
import { useAppStore } from "../context/useAppStore";
import MovieCard from "../components/recommendations/MovieCard";
import type { Algorithm } from "../types";
import toast from "react-hot-toast";

const ALGORITHMS: {
  value: Algorithm;
  label: string;
  icon: typeof Sparkles;
  description: string;
  color: string;
}[] = [
  {
    value: "hybrid",
    label: "Hybrid",
    icon: Sparkles,
    description: "Best overall — combines all signals",
    color: "text-brand-400",
  },
  {
    value: "collaborative",
    label: "Collaborative",
    icon: Users,
    description: "Users like you also enjoyed",
    color: "text-blue-400",
  },
  {
    value: "content_based",
    label: "Content",
    icon: Brain,
    description: "Similar genres & themes",
    color: "text-emerald-400",
  },
  {
    value: "trending",
    label: "Trending",
    icon: TrendingUp,
    description: "Popular right now",
    color: "text-amber-400",
  },
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
    } catch (err: any) {
      setError(err.message || "Failed to fetch recommendations");
      toast.error("Failed to load recommendations");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
    window.scrollTo(0, 0);
  }, [selectedAlgorithm]);

  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="relative">
        {/* Background gradient */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-brand-500/[0.07] rounded-full blur-[120px]" />
          <div className="absolute top-20 left-1/3 w-[400px] h-[300px] bg-purple-500/[0.04] rounded-full blur-[100px]" />
        </div>

        <div className="relative max-w-6xl mx-auto px-4 sm:px-6 pt-24 pb-10">
          {/* Title */}
          <div className="text-center mb-10">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-500/[0.08] border border-brand-500/20 mb-5">
              <Sparkles className="w-3 h-3 text-brand-400" />
              <span className="text-2xs font-medium text-brand-300">
                AI-Powered Recommendations
              </span>
            </div>

            <h1 className="text-4xl sm:text-5xl font-bold text-white tracking-tight mb-3">
              Discover what to watch next
            </h1>
            <p className="text-zinc-400 text-base max-w-xl mx-auto leading-relaxed">
              Hybrid recommendation engine combining collaborative filtering,
              content analysis, and deep learning.
            </p>
          </div>

          {/* Control Card */}
          <div className="surface-card p-5 max-w-3xl mx-auto mb-8">
            <div className="flex flex-col sm:flex-row gap-3">
              {/* User ID */}
              <div className="flex-1">
                <label className="text-2xs font-medium text-zinc-500 uppercase tracking-wider mb-1.5 block">
                  User ID
                </label>
                <input
                  type="text"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  placeholder="1 — 162541"
                  className="input-base"
                />
              </div>

              {/* Result Count */}
              <div className="sm:w-36">
                <label className="text-2xs font-medium text-zinc-500 uppercase tracking-wider mb-1.5 block">
                  Results
                </label>
                <div className="relative">
                  <select
                    value={numRecs}
                    onChange={(e) => setNumRecs(Number(e.target.value))}
                    className="input-base pr-8 appearance-none cursor-pointer"
                  >
                    <option value={5}>5</option>
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
                </div>
              </div>

              {/* Generate Button */}
              <div className="sm:flex-shrink-0 sm:self-end">
                <button
                  onClick={fetchRecommendations}
                  disabled={isLoadingRecommendations}
                  className="btn-primary w-full sm:w-auto h-[38px] px-6"
                >
                  {isLoadingRecommendations ? (
                    <>
                      <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Generating
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Generate
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Algorithm Tabs */}
            <div className="flex gap-1 mt-4 p-1 bg-surface-800 rounded-lg">
              {ALGORITHMS.map(({ value, label, icon: Icon, description, color }) => (
                <button
                  key={value}
                  onClick={() => setAlgorithm(value)}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-all duration-150 ${
                    selectedAlgorithm === value
                      ? "bg-surface-700 text-white shadow-sm"
                      : "text-zinc-500 hover:text-zinc-300 hover:bg-surface-750"
                  }`}
                  title={description}
                >
                  <Icon className={`w-3.5 h-3.5 ${selectedAlgorithm === value ? color : ""}`} />
                  <span className="hidden sm:inline">{label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-4 gap-3 max-w-3xl mx-auto mb-12">
            {[
              {
                label: "Algorithm",
                value: ALGORITHMS.find((a) => a.value === selectedAlgorithm)?.label || "",
                icon: Brain,
                color: "text-brand-400",
              },
              {
                label: "Latency",
                value: latency ? `${latency.toFixed(0)}ms` : "—",
                icon: Zap,
                color: "text-emerald-400",
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
                  ? `${(
                      (recommendations.reduce((s, r) => s + r.score, 0) /
                        recommendations.length) *
                      100
                    ).toFixed(0)}%`
                  : "—",
                icon: TrendingUp,
                color: "text-purple-400",
              },
            ].map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="surface-card px-3 py-3 text-center">
                <Icon className={`w-4 h-4 ${color} mx-auto mb-1.5`} />
                <div className="text-sm font-semibold text-white tabular-nums">
                  {value}
                </div>
                <div className="text-2xs text-zinc-500 mt-0.5">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Error */}
      {error && (
        <div className="max-w-6xl mx-auto px-4 sm:px-6 mb-6">
          <div className="surface-card p-3.5 border-red-500/20 bg-red-500/[0.06] flex items-center gap-3">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span className="text-sm text-red-300">{error}</span>
          </div>
        </div>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <section className="max-w-6xl mx-auto px-4 sm:px-6 pb-20">
          <div className="flex items-center justify-between mb-5">
            <h2 className="section-title">Recommended for you</h2>
            <span className="text-2xs text-zinc-500 tabular-nums">
              {recommendations.length} results
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 sm:gap-4">
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

      {/* Quick Links */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pb-10">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-3xl mx-auto">
          <Link
            to="/trending"
            className="surface-card p-4 flex items-center gap-3 hover:bg-white/[0.04] transition-colors group"
          >
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center flex-shrink-0">
              <TrendingUp className="w-5 h-5 text-amber-400" />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-white">Trending Now</h3>
              <p className="text-2xs text-zinc-500">See what&apos;s popular</p>
            </div>
            <ArrowRight className="w-4 h-4 text-zinc-600 group-hover:text-zinc-400 transition-colors" />
          </Link>
          <Link
            to="/explore"
            className="surface-card p-4 flex items-center gap-3 hover:bg-white/[0.04] transition-colors group"
          >
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center flex-shrink-0">
              <BarChart3 className="w-5 h-5 text-blue-400" />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-white">Explore Library</h3>
              <p className="text-2xs text-zinc-500">Browse all movies</p>
            </div>
            <ArrowRight className="w-4 h-4 text-zinc-600 group-hover:text-zinc-400 transition-colors" />
          </Link>
        </div>
      </section>

      {/* Empty State */}
      {!isLoadingRecommendations && recommendations.length === 0 && !error && (
        <section className="max-w-6xl mx-auto px-4 sm:px-6 pb-20">
          <div className="surface-card p-16 text-center">
            <div className="w-14 h-14 rounded-2xl bg-brand-500/[0.08] flex items-center justify-center mx-auto mb-4">
              <Sparkles className="w-6 h-6 text-brand-400" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-1.5">
              Ready to discover
            </h3>
            <p className="text-sm text-zinc-500 max-w-sm mx-auto">
              Enter a user ID and click Generate to get personalized movie
              recommendations powered by AI.
            </p>
          </div>
        </section>
      )}
    </div>
  );
}
