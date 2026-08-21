import MovieGrid from "@/components/movies/MovieGrid";
import SearchBar from "@/components/ui/SearchBar";
import StatsBar from "@/components/ui/StatsBar";
import AlgorithmExplainer from "@/components/home/AlgorithmExplainer";
import Link from "next/link";
import { getHybridRecommendations, getMovieById, getTrending } from "@/lib/models";

async function getRecommendations() {
  try {
    const recs = getHybridRecommendations("1");
    return recs.slice(0, 12).map((r) => {
      const movie = getMovieById(r.movie_id);
      if (!movie) return null;
      return {
        id: movie.id,
        title: movie.title,
        genres: movie.genres,
        year: movie.year,
        poster_url: movie.poster_url,
        vote_average: movie.vote_average,
      };
    }).filter((m): m is NonNullable<typeof m> => m !== null);
  } catch {
    return [];
  }
}

async function getTrendingData() {
  try {
    return getTrending().slice(0, 12).map((t) => {
      const movie = getMovieById(t.movie_id);
      if (!movie) return null;
      return {
        id: movie.id,
        title: movie.title,
        genres: movie.genres,
        year: movie.year,
        poster_url: movie.poster_url,
        vote_average: movie.vote_average,
      };
    }).filter((m): m is NonNullable<typeof m> => m !== null);
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const [recs, trending] = await Promise.all([
    getRecommendations(),
    getTrendingData(),
  ]);

  return (
    <div className="space-y-16 pb-16">
      <section className="pt-12 pb-4">
        <div className="max-w-3xl mx-auto text-center space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 border border-accent/20 text-accent text-xs font-medium">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
            Orbo.ai BeautyGPT Use Case
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold text-white tracking-tight leading-tight">
            Hybrid Recommendation Engine
          </h1>
          <p className="text-base text-slate-400 leading-relaxed max-w-2xl mx-auto">
            Collaborative filtering + content-based analysis + hybrid ensemble.
            9,786 movies, 100K+ ratings, personalized for every user.
          </p>
          <div className="max-w-xl mx-auto">
            <SearchBar placeholder="Search for movies to get recommendations..." size="large" />
          </div>
        </div>
      </section>

      <section>
        <StatsBar />
      </section>

      <section>
        <AlgorithmExplainer />
      </section>

      <section>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="section-title">Recommended for You</h2>
            <p className="text-xs text-slate-500 mt-1">Hybrid ensemble based on your viewing history</p>
          </div>
          <Link href="/movies" className="text-sm text-accent hover:text-accent-hover transition-colors">
            View All
          </Link>
        </div>
        <MovieGrid movies={recs} />
      </section>

      <section>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="section-title">Trending Now</h2>
            <p className="text-xs text-slate-500 mt-1">Popular across all users</p>
          </div>
          <Link href="/trending" className="text-sm text-accent hover:text-accent-hover transition-colors">
            View All
          </Link>
        </div>
        <MovieGrid movies={trending} />
      </section>
    </div>
  );
}
