import MovieGrid from "@/components/movies/MovieGrid";
import Link from "next/link";
import { getMovieById, getSimilarMovies } from "@/lib/models";

export default async function MovieDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const movieId = parseInt(id);
  const movie = getMovieById(movieId);

  if (!movie) {
    return (
      <div className="text-center py-20">
        <h1 className="text-2xl font-bold">Movie Not Found</h1>
        <Link href="/movies" className="text-purple-400 hover:underline mt-4 inline-block">
          ← Back to Movies
        </Link>
      </div>
    );
  }

  const similar: { id: number; title: string; genres: string; year: number | null; poster_url: string; vote_average: number | null }[] =
    getSimilarMovies(movieId)
    .slice(0, 6)
    .map((s) => {
      const m = getMovieById(s.movie_id);
      if (!m) return null;
      return {
        id: m.id,
        title: m.title,
        genres: m.genres,
        year: m.year,
        poster_url: m.poster_url,
        vote_average: m.vote_average,
      };
    })
    .filter((m): m is NonNullable<typeof m> => m !== null);

  return (
    <div className="space-y-8">
      <Link href="/movies" className="text-purple-400 hover:text-purple-300 text-sm">
        ← Back to Movies
      </Link>

      <div className="flex flex-col md:flex-row gap-8">
        <div className="w-full md:w-1/3">
          <div className="aspect-[2/3] bg-gray-800 rounded-lg flex items-center justify-center">
            <span className="text-6xl">🎬</span>
          </div>
        </div>

        <div className="flex-1 space-y-4">
          <h1 className="text-3xl font-bold">{movie.title}</h1>

          <div className="flex items-center gap-4 text-sm">
            {movie.year && <span className="text-gray-400">{movie.year}</span>}
            {movie.vote_average && (
              <span className="text-yellow-400">★ {movie.vote_average.toFixed(1)}</span>
            )}
            {movie.vote_count && (
              <span className="text-gray-500">({movie.vote_count} votes)</span>
            )}
          </div>

          {movie.genres && (
            <div className="flex flex-wrap gap-2">
              {movie.genres.split("|").map((g: string) => (
                <Link
                  key={g}
                  href={`/movies?genre=${encodeURIComponent(g.trim())}`}
                  className="px-3 py-1 bg-gray-800 rounded-full text-sm hover:bg-gray-700"
                >
                  {g.trim()}
                </Link>
              ))}
            </div>
          )}

          {movie.overview && (
            <p className="text-gray-300 leading-relaxed">{movie.overview}</p>
          )}
        </div>
      </div>

      {similar.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold mb-4">Similar Movies</h2>
          <MovieGrid movies={similar} />
        </section>
      )}
    </div>
  );
}
