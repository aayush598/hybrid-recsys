import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { user_id, movie_id, interaction_type, intensity = 1.0 } = body;

  if (!user_id || !movie_id || !interaction_type) {
    return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
  }

  await prisma.userInteraction.create({
    data: {
      userId: user_id,
      movieId: movie_id,
      interactionType: interaction_type,
      intensity,
    },
  });

  return NextResponse.json({ status: "recorded" });
}
