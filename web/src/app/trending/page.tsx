import MovieGrid from "@/components/movies/MovieGrid";
import { getTrending, getMovieById } from "@/lib/models";

export default async function TrendingPage() {
  const trending = getTrending().slice(0, 20).map((t) => {
    const movie = getMovieById(t.movie_id);
    if (!movie) return null;
    return {
      id: movie.id,
      title: movie.title,
      genres: movie.genres,
      year: movie.year,
      poster_url: movie.poster_url,
      vote_average: movie.vote_average,
    };
  }).filter((m): m is NonNullable<typeof m> => m !== null);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Trending Now</h1>
      <p className="text-gray-400">
        Movies that are popular right now based on ratings and engagement.
      </p>
      <MovieGrid movies={trending} />
    </div>
  );
}
