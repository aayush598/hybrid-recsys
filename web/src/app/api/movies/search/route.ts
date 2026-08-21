import { NextRequest, NextResponse } from "next/server";
import { searchMovies } from "@/lib/models";

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.get("q") || "";
  const page = Number(request.nextUrl.searchParams.get("page") || 1);
  const pageSize = Number(request.nextUrl.searchParams.get("page_size") || 20);
  const genre = request.nextUrl.searchParams.get("genre") || undefined;
  const yearFrom = request.nextUrl.searchParams.get("year_from")
    ? Number(request.nextUrl.searchParams.get("year_from"))
    : undefined;
  const yearTo = request.nextUrl.searchParams.get("year_to")
    ? Number(request.nextUrl.searchParams.get("year_to"))
    : undefined;
  const minRating = request.nextUrl.searchParams.get("min_rating")
    ? Number(request.nextUrl.searchParams.get("min_rating"))
    : undefined;

  if (!q) {
    return NextResponse.json({ error: "Query parameter 'q' is required" }, { status: 400 });
  }

  const results = searchMovies(q, genre, yearFrom, yearTo, minRating);
  const total = results.length;
  const start = (page - 1) * pageSize;
  const paged = results.slice(start, start + pageSize);

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
