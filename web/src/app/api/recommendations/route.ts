import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import {
  getHybridRecommendations,
  getUserRecommendations,
  getMovieById,
  getTrending,
} from "@/lib/models";

function resolveRecKey(userId: string): string {
  if (userId.startsWith("user-")) return userId.substring(5);
  return userId;
}

export async function POST(request: NextRequest) {
  const start = Date.now();
  const body = await request.json();
  const {
    user_id,
    session_id,
    num_recommendations = 10,
    algorithm,
    exclude_seen = true,
  } = body;

  let rawRecs: { movie_id: number; score: number }[] = [];
  let algoUsed = "hybrid";

  if (algorithm === "trending") {
    rawRecs = getTrending();
    algoUsed = "trending";
  } else if (algorithm === "collaborative" && user_id) {
    rawRecs = getUserRecommendations(resolveRecKey(user_id));
    algoUsed = "collaborative";
  } else if (user_id) {
    rawRecs = getHybridRecommendations(resolveRecKey(user_id));
    algoUsed = "hybrid";
  } else {
    rawRecs = getTrending();
    algoUsed = "trending";
  }

  let excludeIds: Set<number> = new Set();
  if (exclude_seen && user_id) {
    const ratings = await prisma.rating.findMany({
      where: { userId: user_id },
      select: { movieId: true },
    });
    excludeIds = new Set(ratings.map((r) => r.movieId));
  }

  const items = [];
  for (const rec of rawRecs) {
    if (excludeIds.has(rec.movie_id)) continue;
    const movie = getMovieById(rec.movie_id);
    if (!movie) continue;

    let explanation = "Recommended for you";
    if (algoUsed === "trending") explanation = "Currently trending in the community";
    else if (algoUsed === "collaborative") explanation = "Users with similar taste enjoyed this";
    else explanation = "Matches your taste and is popular in the community";

    items.push({
      movie: {
        id: movie.id,
        title: movie.title,
        genres: movie.genres,
        year: movie.year,
        poster_url: movie.poster_url,
        vote_average: movie.vote_average,
      },
      score: Math.min(rec.score, 1.0),
      algorithm: algoUsed,
      explanation,
      confidence: Math.min(rec.score * 1.2, 1.0),
    });

    if (items.length >= num_recommendations) break;
  }

  const latencyMs = Date.now() - start;

  if (user_id) {
    try {
      await prisma.recommendationLog.create({
        data: {
          userId: user_id,
          sessionId: session_id || null,
          algorithm: algoUsed,
          recommendedMovieIds: JSON.stringify(items.map((i) => i.movie.id)),
          latencyMs,
        },
      });
    } catch {}
  }

  return NextResponse.json({
    user_id,
    session_id,
    recommendations: items,
    algorithm_used: algoUsed,
    latency_ms: latencyMs,
  });
}
