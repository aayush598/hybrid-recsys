import { Star } from "lucide-react";
import { Link } from "react-router-dom";
import type { Movie } from "../../types";

interface MovieCardProps {
  movie: Movie;
  score?: number;
  algorithm?: string;
  explanation?: string;
  index?: number;
  showScore?: boolean;
}

const GENRE_COLORS: Record<string, string> = {
  Action: "from-red-500/20 to-orange-500/20 border-red-500/30",
  Comedy: "from-yellow-500/20 to-amber-500/20 border-yellow-500/30",
  Drama: "from-blue-500/20 to-indigo-500/20 border-blue-500/30",
  Horror: "from-purple-500/20 to-pink-500/20 border-purple-500/30",
  Romance: "from-pink-500/20 to-rose-500/20 border-pink-500/30",
  "Sci-Fi": "from-cyan-500/20 to-teal-500/20 border-cyan-500/30",
  Thriller: "from-gray-500/20 to-slate-500/20 border-gray-500/30",
  Animation: "from-green-500/20 to-emerald-500/20 border-green-500/30",
  Documentary: "from-amber-500/20 to-yellow-500/20 border-amber-500/30",
};

function getGenreColor(genres: string | null): string {
  if (!genres) return "from-brand-500/20 to-purple-500/20 border-brand-500/30";
  const primary = genres.split("|")[0];
  return GENRE_COLORS[primary] || "from-brand-500/20 to-purple-500/20 border-brand-500/30";
}

function formatGenres(genres: string | null): string {
  if (!genres) return "Unknown";
  return genres.split("|").slice(0, 3).join(" · ");
}

export default function MovieCard({
  movie,
  score,
  algorithm,
  explanation,
  index = 0,
  showScore = false,
}: MovieCardProps) {
  const gradientClass = getGenreColor(movie.genres);

  return (
    <div
      className="group relative animate-fade-in"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <Link to={`/movie/${movie.id}`}>
        <div
          className={`glass-card overflow-hidden hover-lift cursor-pointer h-full
            bg-gradient-to-br ${gradientClass} border`}
        >
          <div className="aspect-[2/3] bg-gradient-to-br from-surface-700 to-surface-800 relative overflow-hidden">
            {movie.poster_url ? (
              <img
                src={movie.poster_url}
                alt={movie.title}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <div className="text-center p-4">
                  <div className="text-4xl mb-2">🎬</div>
                  <p className="text-gray-500 text-sm font-medium line-clamp-2">
                    {movie.title}
                  </p>
                </div>
              </div>
            )}

            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

            {showScore && score !== undefined && (
              <div className="absolute top-3 right-3">
                <div className="bg-brand-500/90 backdrop-blur-sm px-2.5 py-1 rounded-lg">
                  <span className="text-xs font-bold text-white">
                    {(score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            )}

            {movie.year && (
              <div className="absolute top-3 left-3">
                <div className="bg-black/60 backdrop-blur-sm px-2 py-1 rounded-lg">
                  <span className="text-xs text-gray-300">{movie.year}</span>
                </div>
              </div>
            )}

            {explanation && (
              <div className="absolute bottom-0 left-0 right-0 p-3 translate-y-full group-hover:translate-y-0 transition-transform duration-300">
                <div className="bg-black/80 backdrop-blur-sm rounded-lg p-2">
                  <p className="text-xs text-gray-300 line-clamp-2">
                    {explanation}
                  </p>
                </div>
              </div>
            )}
          </div>

          <div className="p-3">
            <h3 className="font-semibold text-sm text-white line-clamp-1 group-hover:text-brand-400 transition-colors">
              {movie.title}
            </h3>
            <p className="text-xs text-gray-400 mt-1">{formatGenres(movie.genres)}</p>

            {movie.vote_average !== null && movie.vote_average > 0 && (
              <div className="flex items-center gap-1 mt-2">
                <Star className="w-3 h-3 text-yellow-400 fill-yellow-400" />
                <span className="text-xs text-gray-300">
                  {movie.vote_average.toFixed(1)}
                </span>
              </div>
            )}

            {algorithm && (
              <div className="mt-2">
                <span className="text-[10px] uppercase tracking-wider text-brand-400 font-medium">
                  {algorithm.replace("_", " ")}
                </span>
              </div>
            )}
          </div>
        </div>
      </Link>
    </div>
  );
}
