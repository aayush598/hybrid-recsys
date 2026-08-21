import MovieGrid from "@/components/movies/MovieGrid";
import Link from "next/link";
import RatingWidget from "@/components/ui/RatingWidget";
import LikeButton from "@/components/ui/LikeButton";
import { getMovieById, getSimilarMovies } from "@/lib/models";

export default async function MovieDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const movieId = parseInt(id);
  const movie = getMovieById(movieId);

  if (!movie) {
    return (
      <div className="text-center py-20">
        <h1 className="text-2xl font-bold text-primary">Movie Not Found</h1>
        <Link href="/movies" className="text-secondary hover:text-primary mt-4 inline-block text-sm font-medium">
          Back to Movies
        </Link>
      </div>
    );
  }

  const similar: {
    id: number;
    title: string;
    genres: string;
    year: number | null;
    poster_url: string;
    vote_average: number | null;
  }[] = getSimilarMovies(movieId)
    .slice(0, 6)
    .map((s) => {
      const m = getMovieById(s.movie_id);
      if (!m) return null;
      return { id: m.id, title: m.title, genres: m.genres, year: m.year, poster_url: m.poster_url, vote_average: m.vote_average };
    })
    .filter((m): m is NonNullable<typeof m> => m !== null);

  const genres = movie.genres ? movie.genres.split("|").map((g) => g.trim()).filter(Boolean) : [];
  const stars = movie.vote_average ? Math.round(movie.vote_average / 2) : 0;

  return (
    <div className="space-y-10 pb-16">
      <Link href="/movies" className="inline-flex items-center gap-1 text-sm text-muted hover:text-primary transition-colors">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
        </svg>
        Back to Movies
      </Link>

      <div className="card overflow-hidden">
        <div className="flex flex-col lg:flex-row">
          <div className="w-full lg:w-80 shrink-0">
            <div className="aspect-[2/3] bg-neutral-100 flex items-center justify-center">
              <svg className="w-16 h-16 text-neutral-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h1.5C5.496 19.5 6 18.996 6 18.375m-3.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-1.5A1.125 1.125 0 0118 18.375M20.625 4.5H3.375m17.25 0c.621 0 1.125.504 1.125 1.125M20.625 4.5h-1.5C18.504 4.5 18 5.004 18 5.625m3.75 0v1.5c0 .621-.504 1.125-1.125 1.125M3.375 4.5c-.621 0-1.125.504-1.125 1.125M3.375 4.5h1.5C5.496 4.5 6 5.004 6 5.625m-3.75 0v1.5c0 .621.504 1.125 1.125 1.125m0 0h1.5m-1.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m1.5-3.75C5.496 8.25 6 7.746 6 7.125v-1.5M4.875 8.25C5.496 8.25 6 8.754 6 9.375v1.5m0-5.25v5.25m0-5.25C6 5.004 6.504 4.5 7.125 4.5h9.75c.621 0 1.125.504 1.125 1.125m1.125 2.625h1.5m-1.5 0A1.125 1.125 0 0118 7.125v-1.5m1.125 2.625c-.621 0-1.125.504-1.125 1.125v1.5m2.625-2.625c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125M18 5.625v5.25M7.125 12h9.75m-9.75 0A1.125 1.125 0 016 10.875M7.125 12C6.504 12 6 12.504 6 13.125m0-2.25C6 11.496 5.496 12 4.875 12M18 10.875c0 .621-.504 1.125-1.125 1.125M18 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125m-12 5.25v-5.25m0 5.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125m-12 0v-1.5c0-.621-.504-1.125-1.125-1.125M18 18.375v-5.25m0 5.25v-1.5c0-.621.504-1.125 1.125-1.125M18 13.125v1.5c0 .621.504 1.125 1.125 1.125M18 13.125c0-.621.504-1.125 1.125-1.125M6 13.125v1.5c0 .621-.504 1.125-1.125 1.125M6 13.125C6 12.504 5.496 12 4.875 12m-1.5 0h1.5m-1.5 0c-.621 0-1.125-.504-1.125-1.125v-1.5c0-.621.504-1.125 1.125-1.125M19.125 12h1.5m0 0c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h1.5m14.25 0h1.5" />
              </svg>
            </div>
          </div>

          <div className="flex-1 p-6 lg:p-8 space-y-5">
            <div>
              <h1 className="text-2xl lg:text-3xl font-bold text-primary tracking-tight">
                {movie.title}
              </h1>
              <div className="flex items-center gap-3 mt-2 text-sm">
                {movie.year && <span className="text-secondary">{movie.year}</span>}
                {movie.vote_average && (
                  <div className="flex items-center gap-1.5">
                    <div className="flex gap-0.5">
                      {[1, 2, 3, 4, 5].map((i) => (
                        <svg key={i} className={`w-3.5 h-3.5 ${i <= stars ? "text-amber-400" : "text-neutral-300"}`} fill="currentColor" viewBox="0 0 20 20">
                          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                      ))}
                    </div>
                    <span className="text-primary font-medium">{movie.vote_average.toFixed(1)}</span>
                    {movie.vote_count && (
                      <span className="text-muted">({movie.vote_count.toLocaleString()} votes)</span>
                    )}
                  </div>
                )}
              </div>
            </div>

            {genres.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {genres.map((g) => (
                  <Link key={g} href={`/movies?genre=${encodeURIComponent(g)}`} className="genre-pill">
                    {g}
                  </Link>
                ))}
              </div>
            )}

            {movie.overview && (
              <p className="text-sm text-secondary leading-relaxed">{movie.overview}</p>
            )}

            <div className="divider" />

            <div className="space-y-3">
              <p className="text-xs font-medium text-muted uppercase tracking-wider">Your Rating</p>
              <div className="flex items-center gap-4">
                <RatingWidget movieId={movieId} userId="user-1" />
                <LikeButton movieId={movieId} userId="user-1" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {similar.length > 0 && (
        <section>
          <h2 className="section-title mb-5">Similar Movies</h2>
          <p className="text-xs text-muted mb-4">
            Found using hybrid CF + content similarity scoring
          </p>
          <MovieGrid movies={similar} />
        </section>
      )}
    </div>
  );
}
