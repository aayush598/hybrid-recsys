import MovieGrid from "@/components/movies/MovieGrid";
import { getHybridRecommendations, getMovieById } from "@/lib/models";
import { prisma } from "@/lib/db";

function resolveRecKey(userId: string): string {
  if (userId.startsWith("user-")) return userId.substring(5);
  return userId;
}

async function getProfile(userId: string) {
  try {
    const ratings = await prisma.rating.findMany({
      where: { userId },
      include: { movie: true },
      orderBy: { timestamp: "desc" },
    });

    if (ratings.length === 0) {
      return { user_id: userId, total_ratings: 0, avg_rating: 0, genre_preferences: {}, recent_movies: [] };
    }

    const genrePreferences: Record<string, number> = {};
    for (const r of ratings) {
      if (r.movie.genres) {
        for (const genre of r.movie.genres.split("|")) {
          const g = genre.trim();
          if (g) genrePreferences[g] = (genrePreferences[g] || 0) + r.rating;
        }
      }
    }

    const total = Object.values(genrePreferences).reduce((a, b) => a + b, 0) || 1;
    const normalized: Record<string, number> = {};
    for (const [k, v] of Object.entries(genrePreferences)) {
      normalized[k] = v / total;
    }

    const sorted = Object.entries(normalized).sort((a, b) => b[1] - a[1]).slice(0, 10);

    return {
      user_id: userId,
      total_ratings: ratings.length,
      avg_rating: ratings.reduce((a, r) => a + r.rating, 0) / ratings.length,
      genre_preferences: Object.fromEntries(sorted),
      recent_movies: ratings.slice(0, 20).map((r) => r.movieId),
    };
  } catch {
    return null;
  }
}

async function getRecs(userId: string) {
  try {
    const key = resolveRecKey(userId);
    const recs = getHybridRecommendations(key);
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

export default async function ProfilePage({ params }: { params: Promise<{ userId: string }> }) {
  const { userId } = await params;
  const [profile, recs] = await Promise.all([getProfile(userId), getRecs(userId)]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">User Profile</h1>
        <p className="text-gray-400 mt-1">{userId}</p>
      </div>

      {profile && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-900 rounded-lg p-4">
            <p className="text-gray-500 text-sm">Total Ratings</p>
            <p className="text-2xl font-bold">{profile.total_ratings}</p>
          </div>
          <div className="bg-gray-900 rounded-lg p-4">
            <p className="text-gray-500 text-sm">Avg Rating</p>
            <p className="text-2xl font-bold">{profile.avg_rating?.toFixed(1) || "N/A"}</p>
          </div>
          <div className="bg-gray-900 rounded-lg p-4 col-span-2">
            <p className="text-gray-500 text-sm">Top Genres</p>
            <div className="flex flex-wrap gap-1 mt-2">
              {Object.entries(profile.genre_preferences || {})
                .slice(0, 5)
                .map(([genre, score]) => (
                  <span key={genre} className="px-2 py-0.5 bg-purple-900/50 rounded text-xs">
                    {genre} ({((score as number) * 100).toFixed(0)}%)
                  </span>
                ))}
            </div>
          </div>
        </div>
      )}

      <section>
        <h2 className="text-2xl font-bold mb-4">Personalized Recommendations</h2>
        <MovieGrid movies={recs} />
      </section>
    </div>
  );
}
