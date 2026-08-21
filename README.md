# Hybrid RecSys

Production-grade hybrid recommendation system combining collaborative filtering, content-based analysis, and neural retrieval. Built for the Orbo.ai BeautyGPT use case.

![Next.js](https://img.shields.io/badge/Next.js-14-000000)
![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6)
![Prisma](https://img.shields.io/badge/Prisma-5.20-2D3748)
![Neon](https://img.shields.io/badge/Neon-PostgreSQL-00E599)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-06B6D4)
![Python](https://img.shields.io/badge/Python-3.14-3776AB)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Architecture

```
+------------------------------------------------------+
|                  Browser (SSR)                        |
|  Next.js 14 App Router + React 18 + TailwindCSS     |
|  Server Components + Client Interactivity            |
+-------------------+----------------------------------+
                    |
+-------------------v----------------------------------+
|              Next.js API Routes                       |
|  14 endpoints: recs, movies, users, health           |
+------+---------------+--------------+----------------+
       |               |              |
+------v------+  +-----v-----+  +----v--------------+
| Pre-computed|  |   Neon    |  |  Prisma ORM       |
| JSON Models |  | PostgreSQL|  |  (type-safe DB)   |
| (18MB)      |  | (users,   |  |                    |
|             |  |  ratings) |  |                    |
+------+------+  +-----------+  +-------------------+
       |
+------v------------------------------------------------+
|             ML Pipeline (Python, offline)              |
|  1. ALS Collaborative Filtering (128-dim factors)    |
|  2. TF-IDF Content Similarity                        |
|  3. Hybrid Ensemble (60% CF + trending boost)        |
|  4. Pre-compute -> JSON -> served at runtime          |
+-------------------------------------------------------+
```

---

## How It Works

### Recommendation Pipeline

1. **Candidate Generation** - ALS collaborative filtering retrieves top candidates from 9,786 movies using latent factor dot products (128-dimensional embeddings)

2. **Content Similarity** - TF-IDF features + genre vectors compute cosine similarity for content-based candidates

3. **Hybrid Ensemble** - Late fusion combines CF scores (60%) with trending boost (5%) and diversity-aware re-ranking

4. **Pre-computation** - All ML inferences are computed offline in Python and exported as JSON. The Next.js server loads these at startup for sub-100ms warm response times.

### Domain Mapping (BeautyGPT)

This system maps movie data to beauty product recommendations for Orbo.ai:

| Movie Domain | Beauty Product Domain |
|---|---|
| Movies | Products |
| Genres | Categories (skincare, makeup, haircare) |
| Ratings | Purchase/Satisfaction Signals |
| Movie Overviews | Product Descriptions |
| User Preferences | Skin Type, Tone, Concerns |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14 (App Router), React 18, TypeScript, TailwindCSS |
| **Backend** | Next.js API Routes (14 endpoints), Prisma ORM |
| **Database** | Neon PostgreSQL (serverless, free tier) |
| **ML Pipeline** | Python 3.14, implicit (ALS), FAISS, NumPy |
| **Deployment** | Vercel (free tier), Neon PostgreSQL |
| **Data** | MovieLens 25M (100K sample) |

---

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+ (for ML pipeline regeneration)
- Neon PostgreSQL account (free)

### Quick Start

```bash
git clone https://github.com/aayush598/hybrid-recsys.git
cd hybrid-recsys/web

# Install dependencies
npm install

# Set up database
cp .env.example .env.local
# Add your Neon DATABASE_URL to .env.local

# Seed database
npx prisma db push
npx tsx scripts/seed.ts

# Start dev server
npm run dev
```

Open http://localhost:3000

### Regenerating ML Models (Optional)

```bash
source ../.venv/bin/activate
python scripts/export_models.py
# Filter movies to model subset (see scripts/precompute.py)
python scripts/precompute.py
```

---

## API Reference

### Health Check
```bash
curl http://localhost:3000/api/health
```

### Get Recommendations
```bash
curl -X POST http://localhost:3000/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-1", "num_recommendations": 10}'
```

### Find Similar Movies
```bash
curl "http://localhost:3000/api/recommendations/similar/1?top_k=5"
```

### Rate a Movie
```bash
curl -X POST http://localhost:3000/api/recommendations/user/user-1/rate \
  -H "Content-Type: application/json" \
  -d '{"movie_id": 1, "rating": 4.5}'
```

### Search Movies
```bash
curl "http://localhost:3000/api/movies/search?q=Star"
```

**All 14 endpoints:**

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | System health check |
| POST | `/api/recommendations` | Get personalized recommendations |
| GET | `/api/recommendations/similar/{movieId}` | Find similar movies |
| GET | `/api/recommendations/trending` | Get trending movies |
| POST | `/api/recommendations/interact` | Record user interaction |
| GET | `/api/recommendations/user/{userId}/profile` | User preference profile |
| POST | `/api/recommendations/user/{userId}/rate` | Rate a movie |
| GET | `/api/movies` | List movies (paginated) |
| GET | `/api/movies/{id}` | Movie details |
| GET | `/api/movies/search` | Search movies |
| GET | `/api/movies/genres` | List genres |
| POST | `/api/users` | Create user |
| GET | `/api/users/{userId}` | Get user profile |

---

## ML Pipeline

### Models

| Model | Algorithm | Role | Weight |
|---|---|---|---|
| Collaborative Filtering | ALS (implicit) | Learns latent user/item factors | 60% |
| Content Similarity | TF-IDF cosine similarity | Recommends similar content | Part of hybrid |
| Trending | Score = avg_rating * log(count) | Cold-start fallback | 5% boost |
| Hybrid Ensemble | Late fusion + re-ranking | Final recommendation | 100% |

### Pre-computed Data Files

| File | Size | Content |
|---|---|---|
| `hybrid_recommendations.json` | 1.3 MB | Per-user top-50 recommendations |
| `hybrid_similar.json` | 6.9 MB | Per-movie top-20 similar movies |
| `movies.json` | 1.8 MB | Movie metadata (9,786 movies) |
| `ratings.json` | 7.5 MB | 100K user ratings |
| `cf_mappings.json` | 0.3 MB | ALS model ID mappings |
| `trending.json` | 0.02 MB | Top-500 trending movies |
| `genres.json` | 0.2 KB | 19 genre labels |

### Pipeline Scripts

| Script | Purpose |
|---|---|
| `export_models.py` | Export ALS model + CSV data to JSON |
| `precompute.py` | Pre-compute recommendations + similar movies |
| `seed.ts` | Seed Neon PostgreSQL from JSON files |

---

## Dataset

MovieLens 25M (GroupLens Research), filtered to active users:

| Metric | Value |
|---|---|
| Ratings | 100,960 |
| Movies | 9,786 |
| Users | 757 |
| Genres | 19 |
| Source | [MovieLens 25M](https://grouplens.org/datasets/movielens/25m/) |

---

## Project Structure

```
hybrid-recsys/
  web/                          # Next.js 14 full-stack app
    src/
      app/
        layout.tsx              # Root layout + nav + footer
        page.tsx                # Homepage (recs + trending)
        about/page.tsx          # Project documentation
        docs/page.tsx           # API documentation
        movies/
          page.tsx              # Browse/search movies
          [id]/page.tsx         # Movie detail + similar
        trending/page.tsx       # Ranked trending list
        profile/[userId]/page.tsx  # User dashboard
        api/                    # 14 API routes
      components/
        layout/                 # Nav, Footer
        movies/                 # MovieGrid, MovieCard
        ui/                     # SearchBar, RatingWidget, etc.
      lib/
        db.ts                   # Prisma client
        models.ts               # JSON model loader
    data/                       # Pre-computed ML models (JSON)
    prisma/schema.prisma        # Database schema
    scripts/                    # Export, precompute, seed
  backend/                      # Python ML training pipeline
    ml/models/                  # ALS, content, hybrid models
    data/                       # Raw MovieLens data + trained models
    tests/                      # 210 backend tests
```

---

## Deployment

### Vercel (Free Tier)

```bash
cd web
npx vercel --prod
```

Set environment variable:
```
DATABASE_URL=postgresql://...@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
```

---

## License

MIT
