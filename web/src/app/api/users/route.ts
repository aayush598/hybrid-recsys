import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { username, email, password, display_name } = body;

  if (!username || !email || !password) {
    return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
  }

  const hashed_password = await hashPassword(password);

  try {
    const user = await prisma.user.create({
      data: {
        username,
        email,
        hashedPassword: hashed_password,
        displayName: display_name || null,
      },
    });

    return NextResponse.json({
      id: user.id,
      username: user.username,
      email: user.email,
      display_name: user.displayName,
    });
  } catch (e: any) {
    if (e.code === "P2002") {
      return NextResponse.json({ error: "Username or email already exists" }, { status: 409 });
    }
    throw e;
  }
}

async function hashPassword(password: string): Promise<string> {
  const { createHash } = await import("crypto");
  return createHash("sha256").update(password).digest("hex");
}
