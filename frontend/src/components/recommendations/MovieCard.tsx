import { Star, Play } from "lucide-react";
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

const GENRE_PALETTE: Record<string, { bg: string; accent: string }> = {
  Action: { bg: "from-red-950/40 to-red-900/20", accent: "text-red-400" },
  Comedy: { bg: "from-amber-950/40 to-amber-900/20", accent: "text-amber-400" },
  Drama: { bg: "from-blue-950/40 to-blue-900/20", accent: "text-blue-400" },
  Horror: { bg: "from-purple-950/40 to-purple-900/20", accent: "text-purple-400" },
  Romance: { bg: "from-pink-950/40 to-pink-900/20", accent: "text-pink-400" },
  "Sci-Fi": { bg: "from-cyan-950/40 to-cyan-900/20", accent: "text-cyan-400" },
  Thriller: { bg: "from-zinc-800/40 to-zinc-700/20", accent: "text-zinc-300" },
  Animation: { bg: "from-emerald-950/40 to-emerald-900/20", accent: "text-emerald-400" },
};

function getGenreStyle(genres: string | null) {
  if (!genres) return { bg: "from-surface-800 to-surface-750", accent: "text-zinc-400" };
  const primary = genres.split("|")[0];
  return GENRE_PALETTE[primary] || { bg: "from-surface-800 to-surface-750", accent: "text-zinc-400" };
}

function formatGenres(genres: string | null): string {
  if (!genres) return "";
  return genres.split("|").slice(0, 2).join(" / ");
}

export default function MovieCard({
  movie,
  score,
  algorithm,
  explanation,
  index = 0,
  showScore = false,
}: MovieCardProps) {
  const palette = getGenreStyle(movie.genres);

  return (
    <div
      className="group animate-fade-in"
      style={{ animationDelay: `${index * 40}ms`, animationFillMode: "both" }}
      role="article"
      aria-label={`${movie.title}${score !== undefined ? ` - ${(score * 100).toFixed(0)}% match` : ""}`}
    >
      <Link to={`/movie/${movie.id}`} className="block" aria-label={`View ${movie.title}`}>
        <div className="surface-card-hover overflow-hidden">
          {/* Poster */}
          <div className={`relative aspect-[2/3] bg-gradient-to-br ${palette.bg} overflow-hidden`}>
            {movie.poster_url ? (
              <img
                src={movie.poster_url}
                alt={movie.title}
                className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                loading="lazy"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <div className="text-center px-4">
                  <div className="w-12 h-12 rounded-xl bg-white/[0.06] flex items-center justify-center mx-auto mb-3">
                    <Play className="w-5 h-5 text-zinc-500" />
                  </div>
                  <p className="text-zinc-500 text-xs font-medium line-clamp-2 leading-relaxed">
                    {movie.title}
                  </p>
                </div>
              </div>
            )}

            {/* Hover overlay */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

            {/* Score badge */}
            {showScore && score !== undefined && (
              <div className="absolute top-2.5 right-2.5">
                <div className="px-2 py-1 rounded-md bg-black/60 backdrop-blur-sm border border-white/[0.1]">
                  <span className="text-2xs font-semibold text-white tabular-nums">
                    {(score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            )}

            {/* Year badge */}
            {movie.year && (
              <div className="absolute top-2.5 left-2.5">
                <div className="px-2 py-1 rounded-md bg-black/60 backdrop-blur-sm border border-white/[0.1]">
                  <span className="text-2xs font-medium text-zinc-300 tabular-nums">
                    {movie.year}
                  </span>
                </div>
              </div>
            )}

            {/* Hover explanation */}
            {explanation && (
              <div className="absolute bottom-0 left-0 right-0 p-3 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-out">
                <p className="text-2xs text-zinc-300 leading-relaxed bg-black/70 backdrop-blur-sm rounded-md px-2.5 py-2 line-clamp-2">
                  {explanation}
                </p>
              </div>
            )}
          </div>

          {/* Info */}
          <div className="p-3">
            <h3 className="text-sm font-medium text-zinc-100 line-clamp-1 group-hover:text-white transition-colors">
              {movie.title}
            </h3>

            <div className="flex items-center justify-between mt-1.5">
              <p className="text-2xs text-zinc-500 line-clamp-1">
                {formatGenres(movie.genres)}
              </p>

              {movie.vote_average !== null && movie.vote_average > 0 && (
                <div className="flex items-center gap-1 flex-shrink-0">
                  <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
                  <span className="text-2xs font-medium text-zinc-400 tabular-nums">
                    {movie.vote_average.toFixed(1)}
                  </span>
                </div>
              )}
            </div>

            {algorithm && showScore && (
              <div className="mt-2">
                <span className="text-2xs font-medium text-brand-400/80 uppercase tracking-wider">
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
