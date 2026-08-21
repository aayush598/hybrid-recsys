import { NextRequest, NextResponse } from "next/server";
import { getTrending, getMovieById } from "@/lib/models";

export async function GET(request: NextRequest) {
  const period = request.nextUrl.searchParams.get("period") || "30d";
  const trending = getTrending().slice(0, 20);

  const movies = trending
    .map((t) => {
      const movie = getMovieById(t.movie_id);
      if (!movie) return null;
      return {
        id: movie.id,
        title: movie.title,
        genres: movie.genres,
        year: movie.year,
        poster_url: movie.poster_url,
        vote_average: movie.vote_average,
        vote_count: movie.vote_count,
        popularity: movie.popularity,
        score: t.score,
      };
    })
    .filter(Boolean);

  return NextResponse.json({
    trending: movies,
    period,
    generated_at: new Date().toISOString(),
  });
}
