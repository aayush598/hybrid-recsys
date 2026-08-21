import { NextRequest, NextResponse } from "next/server";
import { getMovies } from "@/lib/models";

export async function GET(request: NextRequest) {
  const page = Number(request.nextUrl.searchParams.get("page") || 1);
  const pageSize = Number(request.nextUrl.searchParams.get("page_size") || 20);
  const genre = request.nextUrl.searchParams.get("genre") || undefined;

  let movies = getMovies();

  if (genre) {
    movies = movies.filter((m) =>
      m.genres.split("|").map((g) => g.trim()).includes(genre)
    );
  }

  const total = movies.length;
  const start = (page - 1) * pageSize;
  const paged = movies.slice(start, start + pageSize);

  return NextResponse.json({
    items: paged.map((m) => ({
      id: m.id,
      title: m.title,
      genres: m.genres,
      year: m.year,
      poster_url: m.poster_url,
      vote_average: m.vote_average,
      vote_count: m.vote_count,
      popularity: m.popularity,
    })),
    total,
    page,
    page_size: pageSize,
    total_pages: Math.ceil(total / pageSize),
  });
}
