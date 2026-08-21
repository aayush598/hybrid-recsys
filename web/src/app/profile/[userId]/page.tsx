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
      return {
        user_id: userId,
        total_ratings: 0,
        avg_rating: 0,
        genre_preferences: {},
        recent_movies: [],
        rating_distribution: {},
      };
    }

    const genrePreferences: Record<string, number> = {};
    const ratingDistribution: Record<string, number> = {};
    for (const r of ratings) {
      const bucket = Math.floor(r.rating).toString();
      ratingDistribution[bucket] = (ratingDistribution[bucket] || 0) + 1;
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
    const sorted = Object.entries(normalized)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10);

    return {
      user_id: userId,
      total_ratings: ratings.length,
      avg_rating: ratings.reduce((a, r) => a + r.rating, 0) / ratings.length,
      genre_preferences: Object.fromEntries(sorted),
      recent_movies: ratings.slice(0, 12).map((r) => r.movieId),
      rating_distribution: ratingDistribution,
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

export default async function ProfilePage({
  params,
}: {
  params: Promise<{ userId: string }>;
}) {
  const { userId } = await params;
  const [profile, recs] = await Promise.all([
    getProfile(userId),
    getRecs(userId),
  ]);

  const maxGenreScore = profile
    ? Math.max(...Object.values(profile.genre_preferences as Record<string, number>), 1)
    : 1;

  return (
    <div className="space-y-8 pb-16">
      <div>
        <h1 className="page-title">User Profile</h1>
        <p className="text-sm text-slate-500 mt-1">{userId}</p>
      </div>

      {profile && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="stat-card">
              <span className="stat-label">Total Ratings</span>
              <span className="stat-value">{profile.total_ratings}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Avg Rating</span>
              <span className="stat-value">
                {profile.avg_rating?.toFixed(1) || "N/A"}
              </span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Top Genre</span>
              <span className="stat-value text-base">
                {Object.keys(profile.genre_preferences)[0] || "N/A"}
              </span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Unique Genres</span>
              <span className="stat-value">
                {Object.keys(profile.genre_preferences).length}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card p-5">
              <h2 className="text-sm font-semibold text-white mb-4">
                Genre Preferences
              </h2>
              <div className="space-y-2.5">
                {Object.entries(profile.genre_preferences)
                  .slice(0, 8)
                  .map(([genre, score]) => (
                    <div key={genre} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-300">{genre}</span>
                        <span className="text-slate-500">
                          {((score as number) * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="h-1.5 bg-surface-3 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-accent rounded-full transition-all"
                          style={{
                            width: `${((score as number) / maxGenreScore) * 100}%`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
              </div>
            </div>

            <div className="card p-5">
              <h2 className="text-sm font-semibold text-white mb-4">
                Rating Distribution
              </h2>
              <div className="space-y-2">
                {[5, 4, 3, 2, 1].map((star) => {
                  const count =
                    profile.rating_distribution?.[star.toString()] || 0;
                  const maxCount = Math.max(
                    ...Object.values(
                      profile.rating_distribution as Record<string, number>
                    ),
                    1
                  );
                  return (
                    <div key={star} className="flex items-center gap-3">
                      <span className="text-xs text-slate-500 w-3">
                        {star}
                      </span>
                      <svg
                        className="w-3 h-3 text-warning shrink-0"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                      <div className="flex-1 h-1.5 bg-surface-3 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-warning/70 rounded-full"
                          style={{
                            width: `${(count / maxCount) * 100}%`,
                          }}
                        />
                      </div>
                      <span className="text-xs text-slate-600 w-6 text-right">
                        {count}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </>
      )}

      <section>
        <h2 className="section-title mb-4">Personalized Recommendations</h2>
        <p className="text-xs text-slate-500 mb-4">
          Hybrid ensemble recommendations based on your rating history
        </p>
        <MovieGrid movies={recs} />
      </section>

      {profile && profile.recent_movies.length > 0 && (
        <section>
          <h2 className="section-title mb-4">Recently Rated</h2>
          <MovieGrid
            movies={profile.recent_movies
              .map((id) => {
                const m = getMovieById(id);
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
              .filter((m): m is NonNullable<typeof m> => m !== null)}
          />
        </section>
      )}
    </div>
  );
}
