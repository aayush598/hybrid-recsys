import MovieGrid from "@/components/movies/MovieGrid";
import Link from "next/link";
import { getHybridRecommendations, getMovieById, getTrending } from "@/lib/models";
import { prisma } from "@/lib/db";

async function getRecommendations() {
  try {
    const recs = getHybridRecommendations("1");
    return recs.slice(0, 12).map((r) => {
      const movie = getMovieById(r.movie_id);
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
  } catch {
    return [];
  }
}

async function getTrendingData() {
  try {
    return getTrending().slice(0, 12).map((t) => {
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
  } catch {
    return [];
  }
}

async function getHealth() {
  try {
    const movieCount = await prisma.movie.count();
    const ratingCount = await prisma.rating.count();
    return { movie_count: movieCount, rating_count: ratingCount };
  } catch {
    return null;
  }
}

export default async function HomePage() {
  const [recs, trending, health] = await Promise.all([getRecommendations(), getTrendingData(), getHealth()]);

  return (
    <div className="space-y-12">
      <section className="text-center py-12">
        <h1 className="text-4xl font-bold mb-4">
          <span className="bg-gradient-to-r from-purple-400 via-pink-500 to-red-500 bg-clip-text text-transparent">
            AI-Powered Movie Recommendations
          </span>
        </h1>
        <p className="text-gray-400 text-lg max-w-2xl mx-auto">
          Hybrid collaborative filtering + content-based analysis delivering personalized recommendations.
          {health && (
            <span className="block mt-2 text-sm text-green-400">
              System Online: {health.movie_count} movies | {health.rating_count} ratings
            </span>
          )}
        </p>
      </section>

      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">Recommended for You</h2>
          <Link href="/movies" className="text-purple-400 hover:text-purple-300 text-sm">
            View All →
          </Link>
        </div>
        <MovieGrid movies={recs} />
      </section>

      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">Trending Now</h2>
          <Link href="/trending" className="text-purple-400 hover:text-purple-300 text-sm">
            View All →
          </Link>
        </div>
        <MovieGrid movies={trending} />
      </section>
    </div>
  );
}
