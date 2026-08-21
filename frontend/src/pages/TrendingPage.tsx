import { useEffect, useState } from "react";
import { TrendingUp, Clock } from "lucide-react";
import { recommendationApi } from "../services/api";
import MovieCard from "../components/recommendations/MovieCard";
import type { Movie } from "../types";

interface TrendingItem {
  movie: Movie;
  score: number;
  algorithm: string;
  explanation: string;
}

export default function TrendingPage() {
  const [trending, setTrending] = useState<TrendingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState("30d");

  useEffect(() => {
    const fetchTrending = async () => {
      setLoading(true);
      try {
        const data = await recommendationApi.getTrending(period);
        const items = data.trending.map((movie: Movie, idx: number) => ({
          movie,
          score: data.trending.length > 0 ? 1 - idx / data.trending.length : 0,
          algorithm: "trending",
          explanation: `Trending in the last ${period}`,
        }));
        setTrending(items);
      } catch (err) {
        console.error("Failed to fetch trending:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchTrending();
    window.scrollTo(0, 0);
  }, [period]);

  return (
    <div className="min-h-screen max-w-6xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Trending Now
            </h1>
            <p className="text-sm text-zinc-500">
              Most popular movies in the community
            </p>
          </div>
        </div>

        {/* Period selector */}
        <div className="flex gap-2 mt-4">
          {[
            { value: "7d", label: "7 Days" },
            { value: "30d", label: "30 Days" },
            { value: "90d", label: "90 Days" },
            { value: "1y", label: "1 Year" },
          ].map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setPeriod(value)}
              className={`px-3 py-1.5 rounded-md text-2xs font-medium transition-all ${
                period === value
                  ? "bg-white/[0.1] text-white border border-white/[0.12]"
                  : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04] border border-transparent"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 sm:gap-4">
          {Array.from({ length: 20 }).map((_, i) => (
            <div key={i} className="surface-card overflow-hidden">
              <div className="aspect-[2/3] shimmer" />
              <div className="p-3 space-y-2">
                <div className="h-3.5 shimmer w-3/4 rounded" />
                <div className="h-3 shimmer w-1/2 rounded" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Results */}
      {!loading && trending.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 sm:gap-4">
          {trending.map((item, idx) => (
            <MovieCard
              key={item.movie.id}
              movie={item.movie}
              score={item.score}
              algorithm={item.algorithm}
              explanation={item.explanation}
              index={idx}
              showScore
            />
          ))}
        </div>
      )}

      {/* Empty */}
      {!loading && trending.length === 0 && (
        <div className="surface-card p-16 text-center">
          <div className="w-14 h-14 rounded-2xl bg-surface-750 flex items-center justify-center mx-auto mb-4">
            <Clock className="w-6 h-6 text-zinc-600" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-1.5">
            No trending movies
          </h3>
          <p className="text-sm text-zinc-500">
            Check back later for trending movies.
          </p>
        </div>
      )}
    </div>
  );
}
