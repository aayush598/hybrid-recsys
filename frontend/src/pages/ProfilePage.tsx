import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  User,
  Star,
  BarChart3,
  Heart,
  Film,
  ArrowLeft,
  TrendingUp,
} from "lucide-react";
import { recommendationApi, movieApi } from "../services/api";
import type { UserProfile, Movie } from "../types";

interface RatedMovie {
  movie: Movie;
  rating: number;
}

export default function ProfilePage() {
  const { id } = useParams<{ id: string }>();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [ratedMovies, setRatedMovies] = useState<RatedMovie[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    const fetchProfile = async () => {
      setLoading(true);
      try {
        const data = await recommendationApi.getUserProfile(id);
        setProfile(data);

        // Fetch movie details for recent movies
        if (data.recent_movies && data.recent_movies.length > 0) {
          const movies = await Promise.all(
            data.recent_movies.slice(0, 10).map(async (movieId) => {
              try {
                const movie = await movieApi.getMovie(movieId);
                return { movie, rating: 4.0 };
              } catch {
                return null;
              }
            })
          );
          setRatedMovies(movies.filter(Boolean) as RatedMovie[]);
        }
      } catch (err) {
        console.error("Failed to fetch profile:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 w-48 shimmer rounded" />
          <div className="grid grid-cols-3 gap-4">
            <div className="h-32 shimmer rounded-xl" />
            <div className="h-32 shimmer rounded-xl" />
            <div className="h-32 shimmer rounded-xl" />
          </div>
          <div className="h-64 shimmer rounded-xl" />
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="surface-card p-10 text-center">
          <div className="w-14 h-14 rounded-2xl bg-surface-750 flex items-center justify-center mx-auto mb-4">
            <User className="w-6 h-6 text-zinc-600" />
          </div>
          <h2 className="text-lg font-semibold text-white mb-2">
            Profile not found
          </h2>
          <p className="text-sm text-zinc-500 mb-4">
            User profile doesn&apos;t exist or has no activity.
          </p>
          <Link
            to="/"
            className="btn-primary inline-flex items-center gap-2 px-4 py-2 text-sm"
          >
            Go home
          </Link>
        </div>
      </div>
    );
  }

  const genreEntries = Object.entries(profile.genre_preferences || {});
  const maxGenreScore = genreEntries.length > 0 ? genreEntries[0][1] : 1;

  return (
    <div className="min-h-screen max-w-6xl mx-auto px-4 sm:px-6 py-8">
      {/* Back */}
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-white transition-colors mb-6"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Back
      </Link>

      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-500/20 to-purple-500/20 flex items-center justify-center">
          <User className="w-7 h-7 text-brand-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            User {profile.user_id}
          </h1>
          <p className="text-sm text-zinc-500">
            {profile.total_ratings} ratings &middot; avg {profile.avg_rating.toFixed(1)}
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
        {[
          {
            label: "Total Ratings",
            value: profile.total_ratings,
            icon: Star,
            color: "text-amber-400",
          },
          {
            label: "Avg Rating",
            value: profile.avg_rating.toFixed(1),
            icon: BarChart3,
            color: "text-blue-400",
          },
          {
            label: "Top Genres",
            value: genreEntries.length,
            icon: Heart,
            color: "text-pink-400",
          },
          {
            label: "Movies Seen",
            value: profile.recent_movies?.length || 0,
            icon: Film,
            color: "text-emerald-400",
          },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="surface-card px-4 py-3 text-center">
            <Icon className={`w-5 h-5 ${color} mx-auto mb-2`} />
            <div className="text-lg font-semibold text-white tabular-nums">
              {value}
            </div>
            <div className="text-2xs text-zinc-500">{label}</div>
          </div>
        ))}
      </div>

      {/* Genre Preferences */}
      {genreEntries.length > 0 && (
        <div className="surface-card p-5 mb-8">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-white mb-4">
            <TrendingUp className="w-4 h-4 text-brand-400" />
            Genre Preferences
          </h2>
          <div className="space-y-3">
            {genreEntries.slice(0, 8).map(([genre, score]) => (
              <div key={genre}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-zinc-300">{genre}</span>
                  <span className="text-2xs text-zinc-500 tabular-nums">
                    {(score * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-1.5 bg-surface-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-brand-500 to-brand-400 rounded-full transition-all duration-500"
                    style={{
                      width: `${(score / maxGenreScore) * 100}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Movies */}
      {ratedMovies.length > 0 && (
        <div className="surface-card p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-white mb-4">
            <Film className="w-4 h-4 text-brand-400" />
            Recent Activity
          </h2>
          <div className="space-y-2">
            {ratedMovies.map(({ movie }) => (
              <Link
                key={movie.id}
                to={`/movie/${movie.id}`}
                className="flex items-center gap-3 p-3 rounded-lg hover:bg-white/[0.04] transition-colors group"
              >
                <div className="w-10 h-14 rounded-md bg-surface-800 overflow-hidden flex-shrink-0">
                  {movie.poster_url ? (
                    <img
                      src={movie.poster_url}
                      alt={movie.title}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <Film className="w-4 h-4 text-zinc-600" />
                    </div>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-medium text-zinc-200 group-hover:text-white truncate transition-colors">
                    {movie.title}
                  </h3>
                  <p className="text-2xs text-zinc-500">
                    {movie.genres?.split("|").slice(0, 2).join(" / ")}
                  </p>
                </div>
                {movie.vote_average && movie.vote_average > 0 && (
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
                    <span className="text-2xs text-zinc-400 tabular-nums">
                      {movie.vote_average.toFixed(1)}
                    </span>
                  </div>
                )}
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
