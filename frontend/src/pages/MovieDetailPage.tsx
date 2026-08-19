import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Star, Calendar, Users, Sparkles, Info } from "lucide-react";
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
        const movieData = await movieApi.getMovie(Number(id));
        setMovie(movieData);
        const similarData = await recommendationApi.getSimilarMovies(Number(id), 12);
        setSimilar(similarData.similar);
      } catch (err) {
        console.error("Failed to fetch movie:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen max-w-7xl mx-auto px-4 py-8">
        <div className="animate-pulse">
          <div className="h-8 w-32 shimmer rounded mb-8" />
          <div className="flex gap-8">
            <div className="w-80 aspect-[2/3] shimmer rounded-2xl" />
            <div className="flex-1">
              <div className="h-10 shimmer rounded w-3/4 mb-4" />
              <div className="h-4 shimmer rounded w-1/2 mb-6" />
              <div className="h-20 shimmer rounded mb-4" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!movie) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card p-8 text-center">
          <h2 className="text-xl font-semibold text-white mb-2">Movie not found</h2>
          <Link to="/" className="text-brand-400 hover:text-brand-300 text-sm">
            Go back home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Back Button */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-gray-400 hover:text-white text-sm mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </Link>
      </div>

      {/* Movie Hero */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        <div className="flex flex-col md:flex-row gap-8">
          {/* Poster */}
          <div className="w-full md:w-80 flex-shrink-0">
            <div className="aspect-[2/3] glass-card overflow-hidden rounded-2xl">
              {movie.poster_url ? (
                <img
                  src={movie.poster_url}
                  alt={movie.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-surface-700 to-surface-800">
                  <div className="text-center">
                    <div className="text-6xl mb-4">🎬</div>
                    <p className="text-gray-400 text-sm">{movie.title}</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Details */}
          <div className="flex-1">
            <h1 className="font-display text-4xl font-bold text-white mb-3">
              {movie.title}
            </h1>

            <div className="flex flex-wrap items-center gap-4 mb-6">
              {movie.vote_average !== null && movie.vote_average > 0 && (
                <div className="flex items-center gap-1.5 bg-yellow-500/10 border border-yellow-500/20 rounded-lg px-3 py-1.5">
                  <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                  <span className="text-sm font-semibold text-yellow-300">
                    {movie.vote_average.toFixed(1)}
                  </span>
                </div>
              )}
              {movie.year && (
                <div className="flex items-center gap-1.5 text-gray-400 text-sm">
                  <Calendar className="w-4 h-4" />
                  {movie.year}
                </div>
              )}
              {movie.vote_count !== null && movie.vote_count > 0 && (
                <div className="flex items-center gap-1.5 text-gray-400 text-sm">
                  <Users className="w-4 h-4" />
                  {movie.vote_count.toLocaleString()} ratings
                </div>
              )}
            </div>

            {movie.genres && (
              <div className="flex flex-wrap gap-2 mb-6">
                {movie.genres.split("|").map((genre) => (
                  <span
                    key={genre}
                    className="px-3 py-1 rounded-full text-xs font-medium bg-brand-500/10 text-brand-300 border border-brand-500/20"
                  >
                    {genre}
                  </span>
                ))}
              </div>
            )}

            {movie.overview && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-300 mb-2 flex items-center gap-2">
                  <Info className="w-4 h-4" />
                  Overview
                </h3>
                <p className="text-gray-400 text-sm leading-relaxed">{movie.overview}</p>
              </div>
            )}

            {/* AI Insight Card */}
            <div className="glass-card p-4 bg-gradient-to-r from-brand-500/10 to-purple-500/10 border-brand-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-brand-400" />
                <span className="text-sm font-semibold text-brand-300">
                  AI Recommendation Insight
                </span>
              </div>
              <p className="text-xs text-gray-400">
                This movie is recommended using our hybrid ensemble model that combines
                collaborative filtering (user similarity), content-based matching (genre
                and thematic analysis), and trending signals for optimal personalization.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Similar Movies */}
      {similar.length > 0 && (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-1 h-8 bg-gradient-to-b from-brand-500 to-purple-600 rounded-full" />
            <h2 className="font-display text-2xl font-bold text-white">Similar Movies</h2>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
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
