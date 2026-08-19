import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search } from "lucide-react";
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

  const query = searchParams.get("q") || "";

  useEffect(() => {
    movieApi.getGenres().then((data) => setGenres(data.genres));
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        let result;
        if (query) {
          result = await movieApi.searchMovies(query, page, 24, selectedGenre || undefined);
        } else {
          result = await movieApi.listMovies(page, 24, selectedGenre || undefined);
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
    if (searchQuery.trim()) {
      setSearchParams({ q: searchQuery });
    }
    setPage(1);
  };

  return (
    <div className="min-h-screen max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Search Bar */}
      <form onSubmit={handleSearch} className="mb-8">
        <div className="glass-card p-4 flex items-center gap-3">
          <Search className="w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search movies by title, genre, or keyword..."
            className="flex-1 bg-transparent text-white placeholder-gray-500 focus:outline-none text-sm"
          />
          <button
            type="submit"
            className="bg-brand-500 text-white px-6 py-2 rounded-xl text-sm font-medium hover:bg-brand-600 transition-colors"
          >
            Search
          </button>
        </div>
      </form>

      {/* Genre Filters */}
      <div className="flex flex-wrap gap-2 mb-6">
        <button
          onClick={() => {
            setSelectedGenre("");
            setPage(1);
          }}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            !selectedGenre
              ? "bg-brand-500 text-white"
              : "bg-surface-700 text-gray-300 hover:bg-surface-600 border border-white/5"
          }`}
        >
          All
        </button>
        {genres.slice(0, 15).map((genre) => (
          <button
            key={genre}
            onClick={() => {
              setSelectedGenre(selectedGenre === genre ? "" : genre);
              setPage(1);
            }}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              selectedGenre === genre
                ? "bg-brand-500 text-white"
                : "bg-surface-700 text-gray-300 hover:bg-surface-600 border border-white/5"
            }`}
          >
            {genre}
          </button>
        ))}
      </div>

      {/* Results Info */}
      <div className="flex items-center justify-between mb-6">
        <p className="text-sm text-gray-400">
          {query ? `Search results for "${query}"` : "All Movies"} — {total.toLocaleString()} results
        </p>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {Array.from({ length: 24 }).map((_, i) => (
            <div key={i} className="glass-card overflow-hidden animate-pulse">
              <div className="aspect-[2/3] shimmer" />
              <div className="p-3">
                <div className="h-4 shimmer rounded w-3/4 mb-2" />
                <div className="h-3 shimmer rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Results Grid */}
      {!loading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {movies.map((movie, idx) => (
            <MovieCard key={movie.id} movie={movie} index={idx} />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && movies.length === 0 && (
        <div className="glass-card p-12 text-center">
          <Search className="w-12 h-12 text-gray-500 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No results found</h3>
          <p className="text-gray-400">
            Try adjusting your search or filter criteria.
          </p>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-8">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-4 py-2 rounded-xl text-sm font-medium bg-surface-700 text-gray-300 hover:bg-surface-600 disabled:opacity-30 disabled:cursor-not-allowed border border-white/5"
          >
            Previous
          </button>
          <span className="text-sm text-gray-400 px-4">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            className="px-4 py-2 rounded-xl text-sm font-medium bg-surface-700 text-gray-300 hover:bg-surface-600 disabled:opacity-30 disabled:cursor-not-allowed border border-white/5"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
