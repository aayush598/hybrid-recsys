import MovieGrid from "@/components/movies/MovieGrid";
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
  const paged = movies.slice(start, start + 30);

  return { items: paged, total, total_pages: Math.ceil(total / 30) };
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">
          {query ? `Search: "${query}"` : genre ? `${genre} Movies` : "Explore Movies"}
        </h1>
        <span className="text-gray-500">{data.total} movies</span>
      </div>

      <div className="flex flex-wrap gap-2">
        <a
          href="/movies"
          className={`px-3 py-1 rounded-full text-sm ${
            !genre ? "bg-purple-600 text-white" : "bg-gray-800 text-gray-300 hover:bg-gray-700"
          }`}
        >
          All
        </a>
        {genres.map((g: string) => (
          <a
            key={g}
            href={`/movies?genre=${encodeURIComponent(g)}`}
            className={`px-3 py-1 rounded-full text-sm ${
              genre === g ? "bg-purple-600 text-white" : "bg-gray-800 text-gray-300 hover:bg-gray-700"
            }`}
          >
            {g}
          </a>
        ))}
      </div>

      <MovieGrid movies={data.items} />

      {data.total_pages > 1 && (
        <div className="flex justify-center gap-2 mt-8">
          {page > 1 && (
            <a
              href={`/movies?page=${page - 1}${genre ? `&genre=${genre}` : ""}${query ? `&q=${query}` : ""}`}
              className="px-4 py-2 bg-gray-800 rounded hover:bg-gray-700"
            >
              Previous
            </a>
          )}
          <span className="px-4 py-2 text-gray-500">
            Page {page} of {data.total_pages}
          </span>
          {page < data.total_pages && (
            <a
              href={`/movies?page=${page + 1}${genre ? `&genre=${genre}` : ""}${query ? `&q=${query}` : ""}`}
              className="px-4 py-2 bg-gray-800 rounded hover:bg-gray-700"
            >
              Next
            </a>
          )}
        </div>
      )}
    </div>
  );
}
