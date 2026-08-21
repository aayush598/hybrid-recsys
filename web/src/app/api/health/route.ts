import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export async function GET() {
  try {
    const movieCount = await prisma.movie.count();
    const ratingCount = await prisma.rating.count();
    const userCount = await prisma.user.count();
    return NextResponse.json({
      status: "healthy",
      version: "1.0.0",
      database_connected: true,
      models_loaded: true,
      movie_count: movieCount,
      rating_count: ratingCount,
      user_count: userCount,
    });
  } catch (e) {
    return NextResponse.json({
      status: "degraded",
      database_connected: false,
      models_loaded: true,
    });
  }
}
