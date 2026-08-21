import Link from "next/link";

export default function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto space-y-12 pb-16">
      <div>
        <h1 className="page-title">About Hybrid RecSys</h1>
        <p className="text-secondary mt-3 leading-relaxed">
          A production-grade hybrid recommendation system built for Orbo.ai&apos;s BeautyGPT use case.
          Maps movie data to beauty product recommendations using collaborative filtering,
          content-based analysis, and ensemble methods.
        </p>
      </div>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-primary">Domain Mapping</h2>
        <p className="text-sm text-secondary">
          This system demonstrates how movie recommendation patterns translate to beauty product discovery:
        </p>
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-neutral-50">
                <th className="text-left px-4 py-3 font-medium text-secondary">Movie Domain</th>
                <th className="text-left px-4 py-3 font-medium text-secondary">Beauty Product Domain</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              <tr><td className="px-4 py-2.5 text-primary">Movies</td><td className="px-4 py-2.5 text-secondary">Products (skincare, makeup, haircare)</td></tr>
              <tr><td className="px-4 py-2.5 text-primary">Genres</td><td className="px-4 py-2.5 text-secondary">Categories</td></tr>
              <tr><td className="px-4 py-2.5 text-primary">Ratings</td><td className="px-4 py-2.5 text-secondary">Purchase / satisfaction signals</td></tr>
              <tr><td className="px-4 py-2.5 text-primary">Movie Overviews</td><td className="px-4 py-2.5 text-secondary">Product descriptions</td></tr>
              <tr><td className="px-4 py-2.5 text-primary">User Preferences</td><td className="px-4 py-2.5 text-secondary">Skin type, tone, concerns</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-primary">Architecture</h2>
        <div className="card p-6 font-mono text-xs leading-relaxed text-secondary space-y-2 overflow-x-auto">
          <p><span className="text-primary font-medium">Browser</span> (Next.js 14 SSR + React 18)</p>
          <p className="text-muted">|</p>
          <p><span className="text-primary font-medium">Next.js API Routes</span> (14 endpoints)</p>
          <p className="text-muted">|</p>
          <p><span className="text-primary font-medium">Pre-computed JSON</span> (18MB models) + <span className="text-primary font-medium">Neon PostgreSQL</span> (Prisma ORM)</p>
          <p className="text-muted">|</p>
          <p><span className="text-primary font-medium">ML Pipeline</span> (Python, offline) -&gt; ALS + TF-IDF + Hybrid Ensemble</p>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-primary">Tech Stack</h2>
        <div className="grid grid-cols-2 gap-3">
          {[
            ["Frontend", "Next.js 14, React 18, TypeScript, TailwindCSS"],
            ["Backend", "Next.js API Routes, Prisma ORM"],
            ["Database", "Neon PostgreSQL (serverless, free tier)"],
            ["ML Pipeline", "Python, implicit (ALS), FAISS, NumPy"],
            ["Deployment", "Vercel (free tier)"],
            ["Dataset", "MovieLens 25M (100K sample)"],
          ].map(([layer, tech]) => (
            <div key={layer} className="card p-4">
              <span className="text-xs font-medium text-muted uppercase tracking-wider">{layer}</span>
              <p className="text-sm text-primary mt-1">{tech}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-primary">ML Models</h2>
        <div className="space-y-3">
          {[
            ["Collaborative Filtering", "ALS (implicit)", "128-dim latent factors", "60%"],
            ["Content Similarity", "TF-IDF cosine similarity", "Genre + overview features", "Part of hybrid"],
            ["Trending", "Avg rating x log(count)", "Cold-start fallback", "5% boost"],
            ["Hybrid Ensemble", "Late fusion + re-ranking", "Final recommendation", "100%"],
          ].map(([model, algo, role, weight]) => (
            <div key={model} className="card p-4 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-primary">{model}</p>
                <p className="text-xs text-muted mt-0.5">{algo} - {role}</p>
              </div>
              <span className="badge text-2xs">{weight}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-primary">Dataset</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            ["Ratings", "100,960"],
            ["Movies", "9,786"],
            ["Users", "757"],
            ["Genres", "19"],
          ].map(([label, value]) => (
            <div key={label} className="stat-card">
              <span className="stat-label">{label}</span>
              <span className="stat-value text-xl">{value}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-primary">How to Test</h2>
        <div className="space-y-3 text-sm text-secondary">
          <div className="card p-4">
            <p className="font-medium text-primary mb-1">1. Switch users</p>
            <p>Use the user selector in the navigation bar to switch between 4 test users. Each has different rating histories and will see different recommendations.</p>
          </div>
          <div className="card p-4">
            <p className="font-medium text-primary mb-1">2. Rate movies</p>
            <p>Go to any movie detail page and click the star rating widget. Your ratings are saved to the database.</p>
          </div>
          <div className="card p-4">
            <p className="font-medium text-primary mb-1">3. Explore recommendations</p>
            <p>Visit the homepage or your profile to see personalized recommendations powered by the hybrid ensemble.</p>
          </div>
        </div>
      </section>

      <div className="pt-4 border-t border-border flex items-center gap-4">
        <Link href="/docs" className="btn btn-secondary btn-sm">
          API Documentation
        </Link>
        <a href="https://github.com/aayush598/hybrid-recsys" target="_blank" rel="noopener noreferrer" className="btn btn-secondary btn-sm">
          GitHub
        </a>
      </div>
    </div>
  );
}
