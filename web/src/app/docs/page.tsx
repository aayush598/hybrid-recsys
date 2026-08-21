const endpoints = [
  {
    method: "GET",
    path: "/api/health",
    description: "System health check with database and model status",
    response: '{\n  "status": "healthy",\n  "version": "1.0.0",\n  "database_connected": true,\n  "models_loaded": true,\n  "movie_count": 9786,\n  "rating_count": 100798,\n  "user_count": 761\n}',
  },
  {
    method: "POST",
    path: "/api/recommendations",
    description: "Get personalized recommendations for a user. Supports hybrid, collaborative, and trending algorithms.",
    body: '{\n  "user_id": "user-1",\n  "num_recommendations": 10,\n  "algorithm": "hybrid",\n  "exclude_seen": true\n}',
    response: '{\n  "user_id": "user-1",\n  "recommendations": [\n    {\n      "movie": { "id": 7361, "title": "...", "genres": "..." },\n      "score": 0.363,\n      "algorithm": "hybrid",\n      "explanation": "Matches your taste and is popular"\n    }\n  ],\n  "algorithm_used": "hybrid",\n  "latency_ms": 300\n}',
  },
  {
    method: "GET",
    path: "/api/recommendations/similar/{movieId}",
    description: "Find similar movies using hybrid CF + content similarity",
    params: "top_k (query): Number of similar movies to return (default: 10)",
    response: '{\n  "movie_id": 1,\n  "similar": [\n    { "movie": { ... }, "score": 0.85, "algorithm": "hybrid" }\n  ]\n}',
  },
  {
    method: "GET",
    path: "/api/recommendations/trending",
    description: "Get trending movies ranked by community engagement",
    params: "period (query): Time period filter (default: 30d)",
    response: '{\n  "trending": [\n    { "id": 1, "title": "...", "score": 0.95 }\n  ],\n  "period": "30d"\n}',
  },
  {
    method: "POST",
    path: "/api/recommendations/interact",
    description: "Record a user interaction (like, view, click)",
    body: '{\n  "user_id": "user-1",\n  "movie_id": 1,\n  "interaction_type": "like",\n  "intensity": 1.0\n}',
    response: '{ "status": "recorded" }',
  },
  {
    method: "GET",
    path: "/api/recommendations/user/{userId}/profile",
    description: "Get user preference profile with genre preferences and recent movies",
    response: '{\n  "user_id": "user-1",\n  "total_ratings": 71,\n  "avg_rating": 3.8,\n  "genre_preferences": { "Drama": 0.25, "Comedy": 0.18 }\n}',
  },
  {
    method: "POST",
    path: "/api/recommendations/user/{userId}/rate",
    description: "Rate a movie (upserts if already rated)",
    body: '{\n  "movie_id": 1,\n  "rating": 4.5\n}',
    response: '{\n  "status": "rated",\n  "movie_id": 1,\n  "rating": 4.5\n}',
  },
  {
    method: "GET",
    path: "/api/movies",
    description: "List movies with pagination and optional genre filter",
    params: "page (query), page_size (query), genre (query)",
    response: '{\n  "items": [{ "id": 1, "title": "Toy Story", "genres": "Animation|Children" }],\n  "total": 9786,\n  "page": 1,\n  "total_pages": 489\n}',
  },
  {
    method: "GET",
    path: "/api/movies/{id}",
    description: "Get movie details with similar movies",
    response: '{\n  "id": 1,\n  "title": "Toy Story (1995)",\n  "genres": "Animation|Children|Comedy",\n  "year": 1995,\n  "similar_movies": [...]\n}',
  },
  {
    method: "GET",
    path: "/api/movies/search",
    description: "Search movies by title, genre, or keyword",
    params: "q (query): search term, genre (query): genre filter",
    response: '{\n  "query": "Star",\n  "total": 71,\n  "results": [...]\n}',
  },
  {
    method: "GET",
    path: "/api/movies/genres",
    description: "List all available genres",
    response: '{\n  "genres": ["Action", "Adventure", "Animation", ...]\n}',
  },
  {
    method: "POST",
    path: "/api/users",
    description: "Create a new user account",
    body: '{\n  "username": "john",\n  "email": "john@example.com",\n  "password": "secure123"\n}',
    response: '{\n  "id": "...",\n  "username": "john"\n}',
  },
  {
    method: "GET",
    path: "/api/users/{userId}",
    description: "Get user profile with rating count",
    response: '{\n  "id": "...",\n  "username": "user1",\n  "rating_count": 71\n}',
  },
];

const methodColors: Record<string, string> = {
  GET: "bg-success/10 text-success border-success/20",
  POST: "bg-accent/10 text-accent border-accent/20",
  PUT: "bg-warning/10 text-warning border-warning/20",
  DELETE: "bg-danger/10 text-danger border-danger/20",
};

function CodeBlock({ code, title }: { code: string; title?: string }) {
  return (
    <div className="rounded-lg overflow-hidden">
      {title && (
        <div className="px-3 py-1.5 bg-surface-3 text-xs text-slate-500 font-mono">
          {title}
        </div>
      )}
      <pre className="p-3 bg-surface-0 text-xs text-slate-300 font-mono overflow-x-auto leading-relaxed">
        {code}
      </pre>
    </div>
  );
}

export default function DocsPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-10 pb-16">
      <section className="space-y-3">
        <h1 className="text-3xl font-bold text-white tracking-tight">
          API Documentation
        </h1>
        <p className="text-base text-slate-400 leading-relaxed">
          REST API for the Hybrid RecSys recommendation engine. All endpoints
          return JSON. Base URL is the deployment host.
        </p>
        <div className="flex items-center gap-3">
          <span className="badge-success">14 Endpoints</span>
          <span className="badge-accent">REST API</span>
          <span className="badge">JSON</span>
        </div>
      </section>

      <section className="card p-5 space-y-3">
        <h2 className="text-sm font-semibold text-white">Quick Start</h2>
        <CodeBlock
          title="Get recommendations for a user"
          code={`curl -X POST http://localhost:3000/api/recommendations \\
  -H "Content-Type: application/json" \\
  -d '{"user_id": "user-1", "num_recommendations": 5}'`}
        />
        <CodeBlock
          title="Search movies"
          code={`curl "http://localhost:3000/api/movies/search?q=Star+Wars"`}
        />
        <CodeBlock
          title="Rate a movie"
          code={`curl -X POST http://localhost:3000/api/recommendations/user/user-1/rate \\
  -H "Content-Type: application/json" \\
  -d '{"movie_id": 1, "rating": 4.5}'`}
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-white">Endpoints</h2>
        <div className="space-y-3">
          {endpoints.map((ep) => (
            <div key={`${ep.method}-${ep.path}`} className="card p-5 space-y-3">
              <div className="flex items-center gap-3 flex-wrap">
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold font-mono border ${methodColors[ep.method]}`}
                >
                  {ep.method}
                </span>
                <code className="text-sm text-white font-mono">{ep.path}</code>
              </div>
              <p className="text-sm text-slate-400">{ep.description}</p>
              {ep.params && (
                <div className="text-xs text-slate-500">
                  <span className="font-medium text-slate-400">Params:</span>{" "}
                  {ep.params}
                </div>
              )}
              {ep.body && <CodeBlock title="Request Body" code={ep.body} />}
              {ep.response && <CodeBlock title="Response" code={ep.response} />}
            </div>
          ))}
        </div>
      </section>

      <section className="card p-6 space-y-4">
        <h2 className="text-lg font-semibold text-white">Data Models</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            {
              name: "Movie",
              fields: ["id (Int)", "title (String)", "genres (String)", "year (Int?)", "voteAverage (Float?)"],
            },
            {
              name: "User",
              fields: ["id (UUID)", "username (String)", "email (String)", "createdAt (DateTime)"],
            },
            {
              name: "Rating",
              fields: ["userId (String)", "movieId (Int)", "rating (Float)", "timestamp (DateTime)"],
            },
            {
              name: "UserInteraction",
              fields: ["userId (String)", "movieId (Int)", "interactionType (String)", "intensity (Float)"],
            },
          ].map((model) => (
            <div key={model.name} className="p-4 bg-surface-2 rounded-lg space-y-2">
              <h3 className="text-sm font-semibold text-white">{model.name}</h3>
              <ul className="space-y-0.5">
                {model.fields.map((f) => (
                  <li key={f} className="text-xs text-slate-400 font-mono">
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      <section className="card p-6 space-y-4">
        <h2 className="text-lg font-semibold text-white">ML Pipeline</h2>
        <div className="space-y-3 text-sm text-slate-400 leading-relaxed">
          <p>
            The recommendation pipeline runs offline in Python and produces
            pre-computed JSON files that the Next.js API serves at runtime.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              {
                step: "1. Data Export",
                desc: "Export ALS model factors, movie data, and ratings from CSV/pickle to JSON",
                file: "export_models.py",
              },
              {
                step: "2. Pre-computation",
                desc: "Compute per-user recommendations (top-50) and per-movie similar items (top-20)",
                file: "precompute.py",
              },
              {
                step: "3. Hybrid Scoring",
                desc: "Combine CF (60%) + trending (5%) with seen-movie filtering",
                file: "precompute.py",
              },
              {
                step: "4. Database Seed",
                desc: "Load movies, users, and ratings into Neon PostgreSQL via Prisma",
                file: "seed.ts",
              },
            ].map((item) => (
              <div key={item.step} className="p-3 bg-surface-2 rounded-lg space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-white">
                    {item.step}
                  </span>
                  <span className="text-2xs font-mono text-slate-600">
                    {item.file}
                  </span>
                </div>
                <p className="text-xs text-slate-500">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
