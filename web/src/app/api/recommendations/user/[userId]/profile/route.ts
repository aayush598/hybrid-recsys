import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ userId: string }> }
) {
  const { userId } = await params;

  const ratings = await prisma.rating.findMany({
    where: { userId },
    include: { movie: true },
    orderBy: { timestamp: "desc" },
  });

  if (ratings.length === 0) {
    return NextResponse.json({
      user_id: userId,
      total_ratings: 0,
      avg_rating: 0,
      genre_preferences: {},
      recent_movies: [],
    });
  }

  const genrePreferences: Record<string, number> = {};
  for (const r of ratings) {
    if (r.movie.genres) {
      for (const genre of r.movie.genres.split("|")) {
        const g = genre.trim();
        if (g) {
          genrePreferences[g] = (genrePreferences[g] || 0) + r.rating;
        }
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

  return NextResponse.json({
    user_id: userId,
    total_ratings: ratings.length,
    avg_rating: ratings.reduce((a, r) => a + r.rating, 0) / ratings.length,
    genre_preferences: Object.fromEntries(sorted),
    recent_movies: ratings.slice(0, 20).map((r) => r.movieId),
  });
}
