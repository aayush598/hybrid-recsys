import Link from "next/link";

function EndpointBlock({ method, path, description, requestExample, responseExample }: {
  method: string;
  path: string;
  description: string;
  requestExample?: string;
  responseExample: string;
}) {
  const methodColors: Record<string, string> = {
    GET: "bg-green-50 text-green-700 border-green-200",
    POST: "bg-blue-50 text-blue-700 border-blue-200",
  };
  return (
    <div className="card p-5 space-y-3">
      <div className="flex items-center gap-3">
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold border ${methodColors[method] || "bg-neutral-100 text-secondary border-border"}`}>
          {method}
        </span>
        <code className="text-sm font-mono text-primary">{path}</code>
      </div>
      <p className="text-sm text-secondary">{description}</p>
      {requestExample && (
        <div>
          <p className="text-xs font-medium text-muted uppercase tracking-wider mb-1">Request</p>
          <pre className="bg-neutral-50 border border-border rounded-lg p-3 text-xs font-mono text-secondary overflow-x-auto">{requestExample}</pre>
        </div>
      )}
      <div>
        <p className="text-xs font-medium text-muted uppercase tracking-wider mb-1">Response</p>
        <pre className="bg-neutral-50 border border-border rounded-lg p-3 text-xs font-mono text-secondary overflow-x-auto">{responseExample}</pre>
      </div>
    </div>
  );
}

export default function DocsPage() {
  return (
    <div className="max-w-3xl mx-auto space-y-10 pb-16">
      <div>
        <h1 className="page-title">API Documentation</h1>
        <p className="text-secondary mt-3">
          14 REST endpoints powering the recommendation engine. All endpoints accept and return JSON.
        </p>
      </div>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-primary">System</h2>
        <EndpointBlock
          method="GET"
          path="/api/health"
          description="Returns system health status with counts of movies, ratings, and users."
          responseExample={`{
  "status": "healthy",
  "movie_count": 9786,
  "rating_count": 100798,
  "user_count": 5
}`}
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-primary">Recommendations</h2>
        <EndpointBlock
          method="POST"
          path="/api/recommendations"
          description="Get personalized recommendations for a user using the hybrid ensemble algorithm."
          requestExample={`{
  "user_id": "user-1",
  "num_recommendations": 10
}`}
          responseExample={`{
  "user_id": "1",
  "recommendations": [
    { "movie_id": 1, "score": 0.92, "algorithm": "hybrid" }
  ],
  "algorithm_used": "hybrid",
  "count": 10,
  "latency_ms": 312
}`}
        />
        <EndpointBlock
          method="GET"
          path="/api/recommendations/similar/{movieId}"
          description="Find movies similar to a given movie using hybrid CF + content similarity scoring."
          responseExample={`{
  "movie_id": 1,
  "similar": [
    { "movie": { "id": 2, "title": "..." }, "score": 0.85 }
  ],
  "count": 5
}`}
        />
        <EndpointBlock
          method="GET"
          path="/api/recommendations/trending"
          description="Get top trending movies ranked by community engagement score (avg rating x log count)."
          responseExample={`{
  "trending": [
    { "movie_id": 1, "title": "...", "score": 0.95 }
  ]
}`}
        />
        <EndpointBlock
          method="POST"
          path="/api/recommendations/interact"
          description="Record a user interaction (like, unlike, view, etc.) with a movie."
          requestExample={`{
  "user_id": "user-1",
  "movie_id": 42,
  "interaction_type": "like"
}`}
          responseExample={`{
  "status": "recorded",
  "interaction_type": "like",
  "movie_id": 42
}`}
        />
        <EndpointBlock
          method="GET"
          path="/api/recommendations/user/{userId}/profile"
          description="Get a user's preference profile including genre preferences, rating history, and stats."
          responseExample={`{
  "user_id": "user-1",
  "total_ratings": 71,
  "avg_rating": 3.5,
  "favorite_genres": ["Drama", "Comedy"],
  "recent_activity": [...]
}`}
        />
        <EndpointBlock
          method="POST"
          path="/api/recommendations/user/{userId}/rate"
          description="Rate a movie for a specific user. Saves to the database."
          requestExample={`{
  "movie_id": 1,
  "rating": 4.5
}`}
          responseExample={`{
  "status": "rated",
  "movie_id": 1,
  "rating": 4.5
}`}
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-primary">Movies</h2>
        <EndpointBlock
          method="GET"
          path="/api/movies"
          description="List all movies with pagination. Supports optional genre and search query filters."
          responseExample={`{
  "movies": [
    { "id": 1, "title": "Toy Story", "genres": "Animation|Comedy", "year": 1995 }
  ],
  "total": 9786,
  "page": 1,
  "per_page": 20
}`}
        />
        <EndpointBlock
          method="GET"
          path="/api/movies/{id}"
          description="Get detailed information about a single movie."
          responseExample={`{
  "id": 1,
  "title": "Toy Story",
  "genres": "Animation|Comedy",
  "year": 1995,
  "overview": "A story of...",
  "vote_average": 7.7,
  "vote_count": 5415
}`}
        />
        <EndpointBlock
          method="GET"
          path="/api/movies/search?q={query}"
          description="Search movies by title. Optionally filter by genre."
          responseExample={`{
  "query": "Star",
  "genre": null,
  "total": 71,
  "results": [...]
}`}
        />
        <EndpointBlock
          method="GET"
          path="/api/movies/genres"
          description="List all available genres."
          responseExample={`{
  "genres": ["Action", "Adventure", "Animation", ...],
  "count": 19
}`}
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-primary">Users</h2>
        <EndpointBlock
          method="POST"
          path="/api/users"
          description="Create a new user account."
          requestExample={`{
  "username": "jane",
  "email": "jane@example.com",
  "password": "securepass"
}`}
          responseExample={`{
  "id": "user-123",
  "username": "jane",
  "email": "jane@example.com"
}`}
        />
        <EndpointBlock
          method="GET"
          path="/api/users/{userId}"
          description="Get a user's profile information."
          responseExample={`{
  "id": "user-1",
  "username": "user1",
  "total_ratings": 71
}`}
        />
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold text-primary">Data Models</h2>
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-neutral-50">
                <th className="text-left px-4 py-3 font-medium text-secondary">Model</th>
                <th className="text-left px-4 py-3 font-medium text-secondary">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              <tr><td className="px-4 py-2.5 font-mono text-xs text-primary">Movie</td><td className="px-4 py-2.5 text-secondary">9,786 movies with title, genres, year, overview, ratings</td></tr>
              <tr><td className="px-4 py-2.5 font-mono text-xs text-primary">User</td><td className="px-4 py-2.5 text-secondary">User accounts with username, email, password</td></tr>
              <tr><td className="px-4 py-2.5 font-mono text-xs text-primary">Rating</td><td className="px-4 py-2.5 text-secondary">User-movie ratings (1-5 scale) with timestamps</td></tr>
              <tr><td className="px-4 py-2.5 font-mono text-xs text-primary">UserInteraction</td><td className="px-4 py-2.5 text-secondary">Likes, views, and other user interactions</td></tr>
              <tr><td className="px-4 py-2.5 font-mono text-xs text-primary">RecommendationLog</td><td className="px-4 py-2.5 text-secondary">Logged recommendations for analytics</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <div className="pt-4 border-t border-border flex items-center gap-4">
        <Link href="/about" className="btn btn-secondary btn-sm">About</Link>
        <a href="https://github.com/aayush598/hybrid-recsys" target="_blank" rel="noopener noreferrer" className="btn btn-secondary btn-sm">GitHub</a>
      </div>
    </div>
  );
}
