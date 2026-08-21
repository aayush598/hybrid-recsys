import { NextRequest, NextResponse } from "next/server";
import { getSimilarMovies, getMovieById } from "@/lib/models";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ movieId: string }> }
) {
  const { movieId } = await params;
  const topK = Number(request.nextUrl.searchParams.get("top_k") || 10);
  const mid = parseInt(movieId);

  if (isNaN(mid)) {
    return NextResponse.json({ error: "Invalid movie ID" }, { status: 400 });
  }

  const movie = getMovieById(mid);
  if (!movie) {
    return NextResponse.json({ error: "Movie not found" }, { status: 404 });
  }

  const similar = getSimilarMovies(mid).slice(0, topK);
  const results = similar
    .map((s) => {
      const m = getMovieById(s.movie_id);
      if (!m) return null;
      return {
        movie: {
          id: m.id,
          title: m.title,
          genres: m.genres,
          year: m.year,
          poster_url: m.poster_url,
          vote_average: m.vote_average,
        },
        score: s.score,
        algorithm: "hybrid",
        explanation: "Similar movies you might enjoy",
      };
    })
    .filter(Boolean);

  return NextResponse.json({ movie_id: mid, similar: results });
}
