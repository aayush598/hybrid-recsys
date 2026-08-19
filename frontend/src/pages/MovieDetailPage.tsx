import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Star,
  Calendar,
  Users,
  Sparkles,
  Play,
  Tag,
  Info,
} from "lucide-react";
import { movieApi, recommendationApi } from "../services/api";
import MovieCard from "../components/recommendations/MovieCard";
import type { Movie } from "../types";

export default function MovieDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [movie, setMovie] = useState<Movie | null>(null);
  const [similar, setSimilar] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    const fetchData = async () => {
      setLoading(true);
      try {
        const [movieData, similarData] = await Promise.all([
          movieApi.getMovie(Number(id)),
          recommendationApi.getSimilarMovies(Number(id), 12),
        ]);
        setMovie(movieData);
        setSimilar(similarData.similar);
      } catch (err) {
        console.error("Failed to fetch movie:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
    window.scrollTo(0, 0);
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <div className="animate-pulse">
          <div className="h-6 w-24 shimmer rounded mb-8" />
          <div className="flex flex-col md:flex-row gap-8">
            <div className="w-full md:w-72 aspect-[2/3] shimmer rounded-xl" />
            <div className="flex-1 space-y-4">
              <div className="h-8 shimmer rounded w-3/4" />
              <div className="h-4 shimmer rounded w-1/3" />
              <div className="flex gap-2">
                <div className="h-6 w-16 shimmer rounded" />
                <div className="h-6 w-16 shimmer rounded" />
                <div className="h-6 w-16 shimmer rounded" />
              </div>
              <div className="h-20 shimmer rounded" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!movie) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="surface-card p-10 text-center">
          <h2 className="text-lg font-semibold text-white mb-2">
            Movie not found
          </h2>
          <Link
            to="/"
            className="text-sm text-brand-400 hover:text-brand-300 transition-colors"
          >
            Go back home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Back */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 pt-8">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back
        </Link>
      </div>

      {/* Movie Info */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-col md:flex-row gap-8">
          {/* Poster */}
          <div className="w-full md:w-72 flex-shrink-0">
            <div className="aspect-[2/3] surface-card overflow-hidden rounded-xl">
              {movie.poster_url ? (
                <img
                  src={movie.poster_url}
                  alt={movie.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-surface-800">
                  <div className="text-center px-6">
                    <div className="w-16 h-16 rounded-2xl bg-surface-750 flex items-center justify-center mx-auto mb-4">
                      <Play className="w-7 h-7 text-zinc-600" />
                    </div>
                    <p className="text-sm text-zinc-500 font-medium line-clamp-2">
                      {movie.title}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Details */}
          <div className="flex-1 min-w-0">
            <h1 className="text-3xl sm:text-4xl font-bold text-white tracking-tight mb-3">
              {movie.title}
            </h1>

            {/* Meta Row */}
            <div className="flex flex-wrap items-center gap-3 mb-5">
              {movie.vote_average !== null && movie.vote_average > 0 && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-500/[0.08] border border-amber-500/20">
                  <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                  <span className="text-sm font-semibold text-amber-300 tabular-nums">
                    {movie.vote_average.toFixed(1)}
                  </span>
                </div>
              )}
              {movie.year && (
                <div className="flex items-center gap-1.5 text-zinc-400 text-sm">
                  <Calendar className="w-3.5 h-3.5" />
                  <span className="tabular-nums">{movie.year}</span>
                </div>
              )}
              {movie.vote_count !== null && movie.vote_count > 0 && (
                <div className="flex items-center gap-1.5 text-zinc-500 text-sm">
                  <Users className="w-3.5 h-3.5" />
                  <span className="tabular-nums">
                    {movie.vote_count.toLocaleString()} ratings
                  </span>
                </div>
              )}
            </div>

            {/* Genres */}
            {movie.genres && (
              <div className="flex flex-wrap gap-1.5 mb-5">
                {movie.genres.split("|").map((genre) => (
                  <span key={genre} className="badge">
                    {genre}
                  </span>
                ))}
              </div>
            )}

            {/* Overview */}
            {movie.overview && (
              <div className="mb-6">
                <h3 className="flex items-center gap-1.5 text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                  <Info className="w-3.5 h-3.5" />
                  Overview
                </h3>
                <p className="text-sm text-zinc-400 leading-relaxed">
                  {movie.overview}
                </p>
              </div>
            )}

            {/* Tags */}
            {movie.tags && movie.tags.length > 0 && (
              <div className="mb-6">
                <h3 className="flex items-center gap-1.5 text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                  <Tag className="w-3.5 h-3.5" />
                  Tags
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {movie.tags.slice(0, 15).map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 rounded-md text-2xs font-medium bg-surface-750 text-zinc-400 border border-white/[0.04]"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* AI Insight */}
            <div className="surface-card p-4 bg-gradient-to-r from-brand-500/[0.04] to-purple-500/[0.04]">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-md bg-brand-500/[0.1] flex items-center justify-center">
                  <Sparkles className="w-3.5 h-3.5 text-brand-400" />
                </div>
                <span className="text-sm font-medium text-zinc-300">
                  How this is recommended
                </span>
              </div>
              <p className="text-xs text-zinc-500 leading-relaxed">
                Our hybrid ensemble combines collaborative filtering (user
                similarity patterns), content-based analysis (genre and thematic
                matching), and trending signals to surface movies you&apos;re
                most likely to enjoy.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Similar Movies */}
      {similar.length > 0 && (
        <section className="max-w-6xl mx-auto px-4 sm:px-6 pb-20">
          <div className="divider mb-6" />
          <div className="flex items-center justify-between mb-5">
            <h2 className="section-title">Similar movies</h2>
            <span className="text-2xs text-zinc-600 tabular-nums">
              {similar.length} results
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 sm:gap-4">
            {similar.map((item: any, idx: number) => (
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
        </section>
      )}
    </div>
  );
}
