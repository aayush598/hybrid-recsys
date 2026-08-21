import fs from "fs";
import path from "path";

export interface Movie {
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

export interface Recommendation {
  movie_id: number;
  score: number;
}

export interface TrendingItem {
  movie_id: number;
  score: number;
}

let moviesCache: Movie[] | null = null;
let trendingCache: TrendingItem[] | null = null;
let genresCache: string[] | null = null;
let userRecsCache: Record<string, Recommendation[]> | null = null;
let hybridSimilarCache: Record<string, Recommendation[]> | null = null;
let hybridRecsCache: Record<string, Recommendation[]> | null = null;

function getModelsDir(): string {
  return path.join(process.cwd(), "data");
}

function loadJson<T>(filename: string): T {
  const filePath = path.join(getModelsDir(), filename);
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw) as T;
}

export function getMovies(): Movie[] {
  if (!moviesCache) {
    moviesCache = loadJson<Movie[]>("movies.json");
  }
  return moviesCache;
}

export function getMovieById(id: number): Movie | undefined {
  return getMovies().find((m) => m.id === id);
}

export function getTrending(): TrendingItem[] {
  if (!trendingCache) {
    trendingCache = loadJson<TrendingItem[]>("trending.json");
  }
  return trendingCache;
}

export function getGenres(): string[] {
  if (!genresCache) {
    genresCache = loadJson<string[]>("genres.json");
  }
  return genresCache;
}

export function getUserRecommendations(userId: string): Recommendation[] {
  if (!userRecsCache) {
    userRecsCache = loadJson<Record<string, Recommendation[]>>(
      "user_recommendations.json"
    );
  }
  return userRecsCache[userId] || [];
}

export function getHybridRecommendations(userId: string): Recommendation[] {
  if (!hybridRecsCache) {
    hybridRecsCache = loadJson<Record<string, Recommendation[]>>(
      "hybrid_recommendations.json"
    );
  }
  return hybridRecsCache[userId] || [];
}

export function getSimilarMovies(movieId: number): Recommendation[] {
  if (!hybridSimilarCache) {
    hybridSimilarCache = loadJson<Record<string, Recommendation[]>>(
      "hybrid_similar.json"
    );
  }
  return hybridSimilarCache[String(movieId)] || [];
}

export function searchMovies(
  query: string,
  genre?: string,
  yearFrom?: number,
  yearTo?: number,
  minRating?: number
): Movie[] {
  const q = query.toLowerCase();
  let results = getMovies().filter(
    (m) =>
      m.title.toLowerCase().includes(q) ||
      m.genres.toLowerCase().includes(q) ||
      (m.overview && m.overview.toLowerCase().includes(q))
  );

  if (genre) {
    results = results.filter((m) =>
      m.genres.split("|").map((g) => g.trim()).includes(genre)
    );
  }
  if (yearFrom) results = results.filter((m) => m.year && m.year >= yearFrom);
  if (yearTo) results = results.filter((m) => m.year && m.year <= yearTo);
  if (minRating)
    results = results.filter(
      (m) => m.vote_average !== null && m.vote_average >= minRating
    );

  return results;
}

export function getMoviesByGenre(genre: string): Movie[] {
  return getMovies().filter((m) =>
    m.genres.split("|").map((g) => g.trim()).includes(genre)
  );
}
