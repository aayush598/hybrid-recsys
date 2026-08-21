export default function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-12 pb-16">
      <section className="space-y-4">
        <h1 className="text-3xl font-bold text-white tracking-tight">
          About Hybrid RecSys
        </h1>
        <p className="text-base text-slate-400 leading-relaxed">
          A production-grade hybrid recommendation system built for Orbo.ai&apos;s
          BeautyGPT use case. The system maps movie recommendations to beauty
          product recommendations, demonstrating how collaborative filtering,
          content-based analysis, and neural retrieval can work together.
        </p>
      </section>

      <section className="card p-6 space-y-4">
        <h2 className="text-lg font-semibold text-white">Domain Mapping</h2>
        <p className="text-sm text-slate-400 leading-relaxed">
          This system uses MovieLens movie data to demonstrate beauty product
          recommendation architecture. The mapping is:
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { from: "Movies", to: "Beauty Products" },
            { from: "Genres", to: "Categories (skincare, makeup, haircare)" },
            { from: "Ratings", to: "Purchase/Satisfaction Signals" },
            { from: "Movie Overviews", to: "Product Descriptions" },
            { from: "User Preferences", to: "Skin Type, Tone, Concerns" },
          ].map((item) => (
            <div key={item.from} className="flex items-center gap-3 p-3 bg-surface-2 rounded-lg">
              <span className="text-sm text-slate-300">{item.from}</span>
              <svg className="w-4 h-4 text-accent shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
              <span className="text-sm text-white">{item.to}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="card p-6 space-y-4">
        <h2 className="text-lg font-semibold text-white">System Architecture</h2>
        <div className="bg-surface-0 rounded-lg p-4 font-mono text-xs text-slate-400 overflow-x-auto">
          <pre>{`
  ┌─────────────────────────────────────────────────┐
  │              Client (Browser)                     │
  │  Next.js 14 SSR + React 18 + TailwindCSS        │
  └───────────────────┬─────────────────────────────┘
                      │
  ┌───────────────────▼─────────────────────────────┐
  │           Next.js API Routes                     │
  │  /api/recommendations  /api/movies  /api/users  │
  └──────┬──────────────┬──────────────┬────────────┘
         │              │              │
  ┌──────▼──────┐ ┌─────▼─────┐ ┌─────▼──────────┐
  │   Hybrid    │ │  Neon     │ │  Pre-computed  │
  │  Ensemble   │ │ PostgreSQL│ │  JSON Models   │
  │  (offline)  │ │ (users,   │ │  (recs, similar│
  │             │ │  ratings) │ │   movies)      │
  └──────┬──────┘ └───────────┘ └────────────────┘
         │
  ┌──────▼──────────────────────────────────────────┐
  │              ML Pipeline (Python)                │
  │  1. ALS Collaborative Filtering                 │
  │  2. TF-IDF Content Similarity                   │
  │  3. Hybrid Ensemble (60% CF + 5% trending)      │
  │  4. Pre-compute → JSON for serving               │
  └─────────────────────────────────────────────────┘
          `}</pre>
        </div>
      </section>

      <section className="card p-6 space-y-4">
        <h2 className="text-lg font-semibold text-white">Tech Stack</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            {
              category: "Frontend",
              items: ["Next.js 14 (App Router)", "TypeScript", "TailwindCSS 3", "React 18"],
            },
            {
              category: "Backend",
              items: ["Next.js API Routes", "Prisma ORM", "Neon PostgreSQL", "JSON Model Serving"],
            },
            {
              category: "ML Pipeline",
              items: ["Python 3.14", "implicit (ALS)", "FAISS", "NumPy"],
            },
            {
              category: "Deployment",
              items: ["Vercel (free tier)", "Neon PostgreSQL", "GitHub Actions", "Prisma Migrate"],
            },
          ].map((stack) => (
            <div key={stack.category} className="space-y-2">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                {stack.category}
              </h3>
              <ul className="space-y-1">
                {stack.items.map((item) => (
                  <li key={item} className="text-sm text-slate-300 flex items-center gap-2">
                    <span className="w-1 h-1 rounded-full bg-accent/50" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      <section className="card p-6 space-y-4">
        <h2 className="text-lg font-semibold text-white">ML Models</h2>
        <div className="space-y-4">
          {[
            {
              name: "Collaborative Filtering (ALS)",
              description:
                "Alternating Least Squares decomposes the user-item interaction matrix into latent factors (128 dimensions). Learns user preferences from similar users' behavior without needing content information.",
              weights: "60% of hybrid score",
            },
            {
              name: "Content-Based Similarity",
              description:
                "TF-IDF features extracted from movie genres and metadata. Cosine similarity identifies items with similar content characteristics.",
              weights: "Part of hybrid ensemble",
            },
            {
              name: "Hybrid Ensemble",
              description:
                "Late fusion combines collaborative filtering scores (60%) with trending boost (5%) and diversity-aware re-ranking. Pre-computed offline and served as JSON for sub-100ms latency.",
              weights: "Final score",
            },
          ].map((model) => (
            <div key={model.name} className="p-4 bg-surface-2 rounded-lg space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white">{model.name}</h3>
                <span className="badge-accent text-2xs">{model.weights}</span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                {model.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="card p-6 space-y-4">
        <h2 className="text-lg font-semibold text-white">Dataset</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Ratings", value: "100,960" },
            { label: "Movies", value: "9,786" },
            { label: "Users", value: "757" },
            { label: "Genres", value: "19" },
          ].map((stat) => (
            <div key={stat.label} className="text-center p-3 bg-surface-2 rounded-lg">
              <p className="text-xl font-bold text-white">{stat.value}</p>
              <p className="text-xs text-slate-500 mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-500 leading-relaxed">
          Based on MovieLens 25M dataset (GroupLens Research). Filtered to 757
          active users with 100K+ ratings across 9,786 movies. The full dataset
          contains 25M ratings from 162K users across 62K movies.
        </p>
      </section>

      <section className="card p-6 space-y-4">
        <h2 className="text-lg font-semibold text-white">How to Test</h2>
        <ol className="space-y-3 text-sm text-slate-400 list-decimal list-inside">
          <li>
            <span className="text-white font-medium">Switch users</span> — Use
            the user selector in the nav bar to switch between test users with
            different viewing histories.
          </li>
          <li>
            <span className="text-white font-medium">Rate movies</span> — Click
            on any movie, then use the star rating widget to rate it. Your
            rating is saved to the database.
          </li>
          <li>
            <span className="text-white font-medium">Get recommendations</span>{" "}
            — Each user&apos;s homepage shows personalized recommendations based on
            their rating history.
          </li>
          <li>
            <span className="text-white font-medium">Explore similar
            movies</span> — On any movie detail page, scroll down to see similar
            movies found using hybrid CF + content similarity.
          </li>
          <li>
            <span className="text-white font-medium">Search</span> — Use the
            search bar to find movies by title, genre, or keyword.
          </li>
        </ol>
      </section>
    </div>
  );
}
