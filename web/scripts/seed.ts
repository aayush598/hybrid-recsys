import { PrismaClient } from "@prisma/client";
import fs from "fs";
import path from "path";

const prisma = new PrismaClient();

const MODELS_DIR = path.join(process.cwd(), "public", "models");

interface MovieJSON {
  id: number;
  title: string;
  genres: string;
  year: number | null;
  overview: string;
  poster_url: string;
  vote_average: number | null;
  vote_count: number | null;
  popularity: number | null;
}

interface RatingJSON {
  user_id: string;
  movie_id: number;
  rating: number;
  timestamp: number;
}

async function main() {
  console.log("Seeding Neon PostgreSQL database...");

  const moviesRaw = fs.readFileSync(path.join(MODELS_DIR, "movies.json"), "utf-8");
  const movies: MovieJSON[] = JSON.parse(moviesRaw);
  console.log(`Found ${movies.length} movies to seed`);

  const BATCH = 500;
  for (let i = 0; i < movies.length; i += BATCH) {
    const batch = movies.slice(i, i + BATCH);
    await prisma.movie.createMany({
      data: batch.map((m) => ({
        id: m.id,
        title: m.title,
        genres: m.genres,
        year: m.year,
        overview: m.overview || null,
        posterUrl: m.poster_url || null,
        voteAverage: m.vote_average,
        voteCount: m.vote_count,
        popularity: m.popularity,
      })),
      skipDuplicates: true,
    });
    console.log(`  Movies: ${Math.min(i + BATCH, movies.length)}/${movies.length}`);
  }

  const movieIds = new Set(movies.map((m) => m.id));
  const ratingsRaw = fs.readFileSync(path.join(MODELS_DIR, "ratings.json"), "utf-8");
  const allRatings: RatingJSON[] = JSON.parse(ratingsRaw);
  const ratings = allRatings.filter((r) => movieIds.has(r.movie_id));
  console.log(`Found ${ratings.length} ratings to seed (filtered from ${allRatings.length})`);

  const userIds = new Set(ratings.map((r) => r.user_id));
  const userRecords = Array.from(userIds).map((uid) => ({
    id: `user-${uid}`,
    username: `user${uid}`,
    email: `user${uid}@hybrid-recsys.local`,
    hashedPassword: "not-a-real-hash",
    displayName: `User ${uid}`,
  }));

  await prisma.user.createMany({ data: userRecords, skipDuplicates: true });
  console.log(`  Created ${userRecords.length} users`);

  for (let i = 0; i < ratings.length; i += BATCH) {
    const batch = ratings.slice(i, i + BATCH);
    await prisma.rating.createMany({
      data: batch.map((r) => ({
        userId: `user-${r.user_id}`,
        movieId: r.movie_id,
        rating: r.rating,
        timestamp: new Date(r.timestamp * 1000),
      })),
      skipDuplicates: true,
    });
    console.log(`  Ratings: ${Math.min(i + BATCH, ratings.length)}/${ratings.length}`);
  }

  console.log("Seeding complete!");
  console.log(`  Movies: ${movies.length}`);
  console.log(`  Users: ${userRecords.length}`);
  console.log(`  Ratings: ${ratings.length}`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
