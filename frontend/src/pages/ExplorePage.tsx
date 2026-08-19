import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search, SlidersHorizontal, X } from "lucide-react";
import { movieApi } from "../services/api";
import MovieCard from "../components/recommendations/MovieCard";
import { useAppStore } from "../context/useAppStore";
import type { Movie } from "../types";

export default function ExplorePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { searchQuery, setSearchQuery } = useAppStore();
  const [movies, setMovies] = useState<Movie[]>([]);
  const [genres, setGenres] = useState<string[]>([]);
  const [selectedGenre, setSelectedGenre] = useState<string>("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [localSearch, setLocalSearch] = useState(searchQuery);

  const query = searchParams.get("q") || "";

  useEffect(() => {
    movieApi.getGenres().then((data) =>
      setGenres(data.genres.filter((g) => g !== "(no genres listed)"))
    );
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        let result;
        if (query) {
          result = await movieApi.searchMovies(
            query,
            page,
            24,
            selectedGenre || undefined
          );
        } else {
          result = await movieApi.listMovies(
            page,
            24,
            selectedGenre || undefined
          );
        }
        setMovies(result.items);
        setTotalPages(result.total_pages);
        setTotal(result.total);
      } catch (err) {
        console.error("Failed to fetch movies:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [query, page, selectedGenre]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(localSearch);
    if (localSearch.trim()) {
      setSearchParams({ q: localSearch });
    } else {
      setSearchParams({});
    }
    setPage(1);
  };

  const clearSearch = () => {
    setLocalSearch("");
    setSearchQuery("");
    setSearchParams({});
    setPage(1);
  };

  const selectGenre = (genre: string) => {
    setSelectedGenre(selectedGenre === genre ? "" : genre);
    setPage(1);
  };

  return (
    <div className="min-h-screen max-w-6xl mx-auto px-4 sm:px-6 py-8">
      {/* Search */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500" />
          <input
            type="text"
            value={localSearch}
            onChange={(e) => setLocalSearch(e.target.value)}
            placeholder="Search movies by title, genre, or keyword..."
            className="input-base pl-12 pr-24 py-3.5 text-base rounded-xl"
          />
          {localSearch && (
            <button
              type="button"
              onClick={clearSearch}
              className="absolute right-24 top-1/2 -translate-y-1/2 p-1 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.06] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <button
            type="submit"
            className="absolute right-2 top-1/2 -translate-y-1/2 btn-primary py-2 px-4"
          >
            Search
          </button>
        </div>
      </form>

      {/* Genre Filters */}
      <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-1 scrollbar-hide">
        <SlidersHorizontal className="w-4 h-4 text-zinc-500 flex-shrink-0" />
        <button
          onClick={() => {
            setSelectedGenre("");
            setPage(1);
          }}
          className={`flex-shrink-0 px-3 py-1.5 rounded-md text-2xs font-medium transition-all ${
            !selectedGenre
              ? "bg-white/[0.1] text-white border border-white/[0.12]"
              : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04] border border-transparent"
          }`}
        >
          All
        </button>
        {genres.slice(0, 18).map((genre) => (
          <button
            key={genre}
            onClick={() => selectGenre(genre)}
            className={`flex-shrink-0 px-3 py-1.5 rounded-md text-2xs font-medium transition-all ${
              selectedGenre === genre
                ? "bg-white/[0.1] text-white border border-white/[0.12]"
                : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04] border border-transparent"
            }`}
          >
            {genre}
          </button>
        ))}
      </div>

      {/* Results Header */}
      <div className="flex items-center justify-between mb-5">
        <p className="text-sm text-zinc-500">
          {query ? (
            <>
              Results for{" "}
              <span className="text-zinc-300 font-medium">"{query}"</span>
            </>
          ) : (
            "All movies"
          )}
        </p>
        <span className="text-2xs text-zinc-600 tabular-nums">
          {total.toLocaleString()} movies
        </span>
      </div>

      {/* Loading Grid */}
      {loading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 sm:gap-4">
          {Array.from({ length: 24 }).map((_, i) => (
            <div key={i} className="surface-card overflow-hidden">
              <div className="aspect-[2/3] shimmer" />
              <div className="p-3 space-y-2">
                <div className="h-3.5 shimmer w-3/4 rounded" />
                <div className="h-3 shimmer w-1/2 rounded" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Results Grid */}
      {!loading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 sm:gap-4">
          {movies.map((movie, idx) => (
            <MovieCard key={movie.id} movie={movie} index={idx} />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && movies.length === 0 && (
        <div className="surface-card p-16 text-center">
          <div className="w-14 h-14 rounded-2xl bg-surface-750 flex items-center justify-center mx-auto mb-4">
            <Search className="w-6 h-6 text-zinc-600" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-1.5">
            No results found
          </h3>
          <p className="text-sm text-zinc-500">
            Try a different search term or genre filter.
          </p>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && !loading && (
        <div className="flex items-center justify-center gap-2 mt-10">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="btn-secondary px-4 py-2 text-sm disabled:opacity-30"
          >
            Previous
          </button>
          <span className="text-sm text-zinc-500 tabular-nums px-3">
            {page} / {totalPages.toLocaleString()}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            className="btn-secondary px-4 py-2 text-sm disabled:opacity-30"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
