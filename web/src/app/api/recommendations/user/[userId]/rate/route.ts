import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ userId: string }> }
) {
  const { userId } = await params;
  const body = await request.json();
  const { movie_id, rating } = body;

  if (!movie_id || rating === undefined) {
    return NextResponse.json({ error: "Missing movie_id or rating" }, { status: 400 });
  }

  await prisma.rating.upsert({
    where: { userId_movieId: { userId, movieId: movie_id } },
    update: { rating },
    create: { userId, movieId: movie_id, rating },
  });

  return NextResponse.json({ status: "rated", movie_id, rating });
}
