import { NextRequest, NextResponse } from "next/server";
import { getMovieById, getSimilarMovies } from "@/lib/models";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const movieId = parseInt(id);

  if (isNaN(movieId)) {
    return NextResponse.json({ error: "Invalid movie ID" }, { status: 400 });
  }

  const movie = getMovieById(movieId);
  if (!movie) {
    return NextResponse.json({ error: "Movie not found" }, { status: 404 });
  }

  const similar = getSimilarMovies(movieId)
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
    .filter(Boolean);

  return NextResponse.json({
    id: movie.id,
    title: movie.title,
    genres: movie.genres,
    year: movie.year,
    overview: movie.overview,
    poster_url: movie.poster_url,
    vote_average: movie.vote_average,
    vote_count: movie.vote_count,
    popularity: movie.popularity,
    tags: [],
    similar_movies: similar,
  });
}
