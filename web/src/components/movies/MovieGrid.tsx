"use client";

import Link from "next/link";

interface Movie {
  id: number;
  title: string;
  genres?: string;
  year?: number | null;
  poster_url?: string;
  vote_average?: number | null;
}

export default function MovieGrid({ movies }: { movies: Movie[] }) {
  if (!movies || movies.length === 0) {
    return <p className="text-gray-500">No movies to display.</p>;
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
      {movies.map((movie) => (
        <Link key={movie.id} href={`/movies/${movie.id}`}>
          <div className="bg-gray-900 rounded-lg overflow-hidden hover:ring-2 hover:ring-purple-500 transition-all cursor-pointer group">
            <div className="aspect-[2/3] bg-gray-800 flex items-center justify-center">
              <span className="text-4xl group-hover:scale-110 transition-transform">🎬</span>
            </div>
            <div className="p-2">
              <h3 className="text-sm font-medium truncate" title={movie.title}>
                {movie.title}
              </h3>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-gray-500">
                  {movie.year || "N/A"}
                </span>
                {movie.vote_average && (
                  <span className="text-xs text-yellow-400">
                    ★ {movie.vote_average.toFixed(1)}
                  </span>
                )}
              </div>
              {movie.genres && (
                <p className="text-xs text-gray-500 truncate mt-1">
                  {movie.genres.split("|").slice(0, 2).join(", ")}
                </p>
              )}
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}
