import { NextResponse } from "next/server";
import { getGenres } from "@/lib/models";

export async function GET() {
  return NextResponse.json({ genres: getGenres() });
}
