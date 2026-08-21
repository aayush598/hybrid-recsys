import MovieGrid from "@/components/movies/MovieGrid";
import { getTrending, getMovieById } from "@/lib/models";

export default async function TrendingPage() {
  const trending = getTrending()
    .slice(0, 30)
    .map((t, i) => {
      const movie = getMovieById(t.movie_id);
      if (!movie) return null;
      return {
        id: movie.id,
        title: movie.title,
        genres: movie.genres,
        year: movie.year,
        poster_url: movie.poster_url,
        vote_average: movie.vote_average,
        rank: i + 1,
        score: t.score,
      };
    })
    .filter(
      (m): m is NonNullable<typeof m> & { rank: number; score: number } =>
        m !== null
    );

  return (
    <div className="space-y-6 pb-16">
      <div>
        <h1 className="page-title">Trending Now</h1>
        <p className="text-sm text-slate-500 mt-1">
          Top {trending.length} movies ranked by community engagement score
        </p>
      </div>

      <div className="space-y-2">
        {trending.map((movie) => (
          <a
            key={movie.id}
            href={`/movies/${movie.id}`}
            className="card-hover flex items-center gap-4 p-4"
          >
            <div className="w-10 h-10 rounded-lg bg-surface-3 flex items-center justify-center shrink-0">
              <span className="text-sm font-bold text-slate-500">
                {movie.rank}
              </span>
            </div>

            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-medium text-white truncate">
                {movie.title}
              </h3>
              <div className="flex items-center gap-2 mt-0.5">
                {movie.year && (
                  <span className="text-xs text-slate-500">{movie.year}</span>
                )}
                {movie.genres && (
                  <span className="text-xs text-slate-600">
                    {movie.genres.split("|").slice(0, 2).join(", ")}
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              {movie.vote_average && (
                <div className="flex items-center gap-1">
                  <svg className="w-3.5 h-3.5 text-warning" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  <span className="text-xs text-slate-400">
                    {movie.vote_average.toFixed(1)}
                  </span>
                </div>
              )}
              <div className="badge badge-success text-2xs">
                {(movie.score * 100).toFixed(0)}
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
