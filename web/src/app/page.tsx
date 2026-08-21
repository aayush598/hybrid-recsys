import MovieGrid from "@/components/movies/MovieGrid";
import SearchBar from "@/components/ui/SearchBar";
import StatsBar from "@/components/ui/StatsBar";
import AlgorithmExplainer from "@/components/home/AlgorithmExplainer";
import Link from "next/link";
import { getHybridRecommendations, getMovieById, getTrending } from "@/lib/models";

async function getRecommendations() {
  try {
    const recs = getHybridRecommendations("1");
    return recs
      .slice(0, 12)
      .map((r) => {
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
      })
      .filter((m): m is NonNullable<typeof m> => m !== null);
  } catch {
    return [];
  }
}

async function getTrendingData() {
  try {
    return getTrending()
      .slice(0, 12)
      .map((t) => {
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
      })
      .filter((m): m is NonNullable<typeof m> => m !== null);
  } catch {
    return [];
  }
}

const features = [
  {
    title: "Sub-50ms Retrieval",
    description: "Pre-computed model JSONs with in-memory lookups for instant response times.",
    icon: "M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z",
  },
  {
    title: "Hybrid ML Pipeline",
    description: "ALS + TF-IDF + cosine similarity fused with diversity-aware re-ranking.",
    icon: "M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z",
  },
  {
    title: "BeautyGPT Ready",
    description: "Same architecture adapts from movies to skincare products, routines, and preferences.",
    icon: "M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z",
  },
];

export default async function HomePage() {
  const [recs, trending] = await Promise.all([
    getRecommendations(),
    getTrendingData(),
  ]);

  return (
    <div>
      <section className="hero-bg pt-20 pb-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto text-center space-y-6 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-neutral-100/80 backdrop-blur-sm border border-border text-secondary text-xs font-medium animate-fadeIn">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
            </svg>
            Orbo.ai BeautyGPT Use Case
          </div>
          <h1
            className="text-4xl sm:text-5xl lg:text-6xl font-bold text-primary tracking-tight leading-[1.1]"
            style={{ animation: "slideUp 0.7s cubic-bezier(0.16,1,0.3,1) forwards", opacity: 0 }}
          >
            Hybrid Recommendation
            <br />
            <span className="text-neutral-400">Engine</span>
          </h1>
          <p
            className="text-base sm:text-lg text-secondary leading-relaxed max-w-xl mx-auto"
            style={{ animation: "slideUp 0.7s cubic-bezier(0.16,1,0.3,1) 0.1s forwards", opacity: 0 }}
          >
            Collaborative filtering, content-based analysis, and hybrid ensemble.
            <br className="hidden sm:block" />
            9,786 movies, 100K+ ratings, personalized for every user.
          </p>
          <div
            className="max-w-lg mx-auto"
            style={{ animation: "slideUp 0.7s cubic-bezier(0.16,1,0.3,1) 0.2s forwards", opacity: 0 }}
          >
            <SearchBar placeholder="Search for movies to get recommendations..." size="large" />
          </div>
          <div
            className="flex items-center justify-center gap-6 text-xs text-muted pt-2"
            style={{ animation: "fadeIn 0.8s ease 0.4s forwards", opacity: 0 }}
          >
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              System Online
            </span>
            <span>9,786 Movies</span>
            <span>100K+ Ratings</span>
            <span>Hybrid ML</span>
          </div>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 -mt-8 mb-16 space-y-6">
        <StatsBar />

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <div className="lg:col-span-3">
            <AlgorithmExplainer />
          </div>
          <div className="lg:col-span-2">
            <div className="card p-6 h-full flex flex-col">
              <div className="flex items-center gap-2 mb-5">
                <svg className="w-4 h-4 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                </svg>
                <h2 className="section-title">Key Features</h2>
              </div>
              <div className="space-y-3 flex-1">
                {features.map((f, i) => (
                  <div
                    key={f.title}
                    className="flex gap-3 p-3 rounded-lg hover:bg-neutral-50 transition-all duration-300 group cursor-default"
                  >
                    <div className="shrink-0 w-9 h-9 rounded-lg bg-neutral-100 flex items-center justify-center group-hover:bg-primary transition-colors duration-300">
                      <svg className="w-4 h-4 text-secondary group-hover:text-white transition-colors duration-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d={f.icon} />
                      </svg>
                    </div>
                    <div className="space-y-0.5">
                      <h3 className="text-sm font-semibold text-primary">{f.title}</h3>
                      <p className="text-xs text-secondary leading-relaxed">{f.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 mb-16">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="section-title">Recommended for You</h2>
            <p className="text-xs text-muted mt-1">
              Hybrid ensemble based on your viewing history
            </p>
          </div>
          <Link
            href="/movies"
            className="text-sm text-secondary hover:text-primary transition-colors font-medium"
          >
            View All
          </Link>
        </div>
        <MovieGrid movies={recs} />
      </section>

      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 mb-16">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="section-title">Trending Now</h2>
            <p className="text-xs text-muted mt-1">Popular across all users</p>
          </div>
          <Link
            href="/trending"
            className="text-sm text-secondary hover:text-primary transition-colors font-medium"
          >
            View All
          </Link>
        </div>
        <MovieGrid movies={trending} />
      </section>

      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 mb-16">
        <div className="card p-8 text-center space-y-4">
          <h2 className="text-xl font-bold text-primary">
            Built for Orbo.ai BeautyGPT
          </h2>
          <p className="text-sm text-secondary max-w-md mx-auto leading-relaxed">
            This recommendation engine demonstrates production-grade ML architecture
            that maps directly to skincare product discovery, routine personalization,
            and beauty preference matching.
          </p>
          <div className="flex items-center justify-center gap-3 pt-2">
            <Link href="/about" className="btn-primary btn-sm">
              Read the Docs
            </Link>
            <Link href="/movies" className="btn-secondary btn-sm">
              Explore Movies
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
