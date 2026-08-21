import MovieGrid from "@/components/movies/MovieGrid";
import SearchBar from "@/components/ui/SearchBar";
import { getMovies as getAllMovies, getGenres as getAllGenres, searchMovies } from "@/lib/models";

function getMoviesData(page: number = 1, genre?: string) {
  let movies = getAllMovies();
  if (genre) {
    movies = movies.filter((m) =>
      m.genres.split("|").map((g) => g.trim()).includes(genre)
    );
  }
  const total = movies.length;
  const start = (page - 1) * 30;
  return { items: movies.slice(start, start + 30), total, total_pages: Math.ceil(total / 30) };
}

export default async function MoviesPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; genre?: string; q?: string }>;
}) {
  const sp = await searchParams;
  const page = Number(sp.page || 1);
  const genre = sp.genre;
  const query = sp.q;

  let data;
  if (query) {
    const results = searchMovies(query, genre);
    const total = results.length;
    const start = (page - 1) * 30;
    data = { items: results.slice(start, start + 30), total, total_pages: Math.ceil(total / 30) };
  } else {
    data = getMoviesData(page, genre);
  }

  const genres = getAllGenres();

  return (
    <div className="space-y-6 pb-16">
      <div className="space-y-4">
        <div>
          <h1 className="page-title">
            {query ? "Search Results" : genre ? genre : "Explore Movies"}
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            {data.total.toLocaleString()} movies
            {query && <> matching &ldquo;{query}&rdquo;</>}
          </p>
        </div>
        <SearchBar defaultValue={query || ""} placeholder="Search by title, genre, or keyword..." />
      </div>

      <div className="flex flex-wrap gap-2">
        <a href="/movies" className={!genre ? "genre-pill-active" : "genre-pill"}>
          All
        </a>
        {genres.map((g: string) => (
          <a
            key={g}
            href={`/movies?genre=${encodeURIComponent(g)}${query ? `&q=${query}` : ""}`}
            className={genre === g ? "genre-pill-active" : "genre-pill"}
          >
            {g}
          </a>
        ))}
      </div>

      <MovieGrid
        movies={data.items}
        emptyMessage={query ? `No movies found for "${query}"` : "No movies in this genre"}
      />

      {data.total_pages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4">
          {page > 1 && (
            <a
              href={`/movies?page=${page - 1}${genre ? `&genre=${genre}` : ""}${query ? `&q=${query}` : ""}`}
              className="btn btn-secondary btn-sm"
            >
              Previous
            </a>
          )}
          <span className="text-sm text-slate-500 px-3">
            Page {page} of {data.total_pages}
          </span>
          {page < data.total_pages && (
            <a
              href={`/movies?page=${page + 1}${genre ? `&genre=${genre}` : ""}${query ? `&q=${query}` : ""}`}
              className="btn btn-secondary btn-sm"
            >
              Next
            </a>
          )}
        </div>
      )}
    </div>
  );
}
