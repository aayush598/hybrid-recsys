# BeautyRec — Production-Grade Hybrid Recommendation System

> AI-powered recommendation engine at FAANG-level engineering standards. Two-stage architecture, hybrid ensemble, neural retrieval, real-time streaming, A/B testing, and full observability — inspired by Netflix's architecture and Orbo.ai's BeautyGPT.

![Architecture](https://img.shields.io/badge/Architecture-Two--Stage%20Hybrid-blue)
![Python](https://img.shields.io/badge/Python-3.11-3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688)
![React](https://img.shields.io/badge/React-18-61DAFB)
![PyTorch](https://img.shields.io/badge/PyTorch-2.1-EE4C2C)
![Docker](https://img.shields.io/badge/Docker-24-2496ED)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Use Case & Motivation](#use-case--motivation)
3. [System Architecture](#system-architecture)
4. [Recommendation Methodology](#recommendation-methodology)
5. [Advanced ML Models](#advanced-ml-models)
6. [Infrastructure & Production Features](#infrastructure--production-features)
7. [Dataset](#dataset)
8. [Technologies](#technologies)
9. [API Documentation](#api-documentation)
10. [Setup & Installation](#setup--installation)
11. [Evaluation](#evaluation)
12. [Test Cases](#test-cases)
13. [Comparison with Existing Products](#comparison-with-existing-products)
14. [Known Limitations](#known-limitations)
15. [Future Improvements](#future-improvements)

---

## Problem Statement

Build a recommendation system that handles **millions of items** with **sub-100ms latency**, combining multiple AI signals while providing **explainable** and **diverse** recommendations — matching the engineering standards of Netflix, YouTube, Amazon, and Spotify.

---

## Use Case & Motivation

**Domain:** Entertainment / Product Recommendations

This system's architecture directly maps to **Orbo.ai's BeautyGPT** use case:
- Movies → Beauty Products
- Genres → Product Categories (skincare, makeup, haircare)
- Ratings → Purchase/Satisfaction Signals
- Movie Overviews → Product Descriptions
- User Preferences → Skin Type, Tone, Concerns

**Real-world impact:** Recommendations drive 35% of Amazon's revenue, 75% of Netflix viewing, and 80% of Spotify listening.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                                  │
│  React 18 + Vite + TailwindCSS (Netflix-inspired dark UI)          │
│  WebSocket real-time streaming + REST API                           │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────────────┐
│                        API GATEWAY                                   │
│  FastAPI (async) + Rate Limiting (Sliding Window)                   │
│  Circuit Breaker + Security Headers + Prometheus Metrics            │
│  CORS + Input Validation + Request ID Tracking                      │
└──────┬────────────┬────────────┬────────────┬───────────────────────┘
       │            │            │            │
┌──────▼──────┐ ┌──▼──────┐ ┌──▼───────┐ ┌──▼──────────┐
│ Recommend.  │ │ Movies  │ │  Users   │ │ WebSocket   │
│ Service     │ │ Service │ │ Service  │ │ Real-time   │
└──────┬──────┘ └────┬────┘ └────┬─────┘ └──────┬──────┘
       │             │           │               │
┌──────▼─────────────▼───────────▼───────────────▼────────────────────┐
│                        ML ENGINE                                     │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Collaborative │  │ Content-     │  │ Trending     │              │
│  │ Filtering     │  │ Based        │  │ (Time-Decay) │              │
│  │ (ALS + FAISS) │  │ (TF-IDF +   │  │              │              │
│  │              │  │  FAISS)      │  │              │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                  │                       │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐              │
│  │ Neural CF    │  │ Two-Tower    │  │ LightGBM     │              │
│  │ (GMF + MLP)  │  │ Retrieval    │  │ LTR Ranker   │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         └─────────────────┼─────────────────┘                       │
│                    ┌──────▼──────┐                                   │
│                    │   HYBRID    │                                   │
│                    │  ENSEMBLE   │                                   │
│                    │(Late Fusion)│                                   │
│                    └──────┬──────┘                                   │
│                    ┌──────▼──────┐                                   │
│                    │  Re-Ranking │                                   │
│                    │  (MMR +     │                                   │
│                    │  Diversity) │                                   │
│                    └─────────────┘                                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                        DATA LAYER                                    │
│  SQLite (metadata) + FAISS (ANN indices)                           │
│  Feature Store (online/offline) + In-Memory Cache                  │
│  Model Artifacts + Experiment Logs                                  │
└─────────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                    OBSERVABILITY                                     │
│  Prometheus (metrics) + Grafana (dashboards)                       │
│  Structured Logging (structlog) + Alert Rules                      │
│  Request Tracing + A/B Test Results                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Recommendation Methodology

### Two-Stage Architecture (Netflix/YouTube/Amazon Standard)

| Stage | Purpose | Latency Budget | Models |
|-------|---------|----------------|--------|
| **Candidate Generation** | Retrieve ~500 candidates from millions | <10ms | FAISS ANN, ALS, Content Index |
| **Ranking** | Score and rank candidates precisely | <50ms | Hybrid Ensemble, LTR |
| **Re-ranking** | Diversity, fairness, explanations | <5ms | MMR, Business Rules |

### 5 Recommendation Models

1. **Collaborative Filtering (ALS)** — Learns latent user/item factors from interaction matrix
2. **Content-Based (TF-IDF + FAISS)** — Recommends items similar to liked content
3. **Neural Collaborative Filtering** — GMF + MLP for non-linear interactions (PyTorch)
4. **Two-Tower Retrieval** — Neural embedding model for scalable retrieval
5. **Learning-to-Rank (LightGBM)** — LambdaMART for precise ranking

### Hybrid Ensemble (Late Fusion)

```
Final Score = 0.30 × CF_score + 0.25 × Content_score + 0.20 × NCF_score
            + 0.15 × Trending_score + 0.10 × Diversity_bonus
```

---

## Advanced ML Models

### Neural Collaborative Filtering (NCF)
- **Architecture:** GMF (Generalized Matrix Factorization) + MLP (Multi-Layer Perceptron)
- **Innovation:** Combines linear (MF) and non-linear (DNN) feature interactions
- **Training:** Binary cross-entropy with Adam optimizer, batch normalization
- **Reference:** He et al., "Neural Collaborative Filtering" (WWW 2017)

### Two-Tower Neural Retrieval
- **Architecture:** User Tower + Item Tower → Dot Product Score
- **Innovation:** Pre-computes item embeddings → FAISS index for O(log n) retrieval
- **Scale:** Handles millions of items with <10ms latency
- **Reference:** YouTube's recommendation system (Google)

### LightGBM Learning-to-Rank
- **Objective:** LambdaMART (listwise ranking)
- **Features:** User features + Item features + Cross features + Genre vectors
- **Output:** Precise relevance score for final ranking
- **Explainability:** Feature importance for each recommendation

---

## Infrastructure & Production Features

### A/B Testing Framework
- Deterministic hash-based user assignment
- Multi-variant experiments with traffic splitting
- Conversion tracking and statistical analysis
- Pre-configured experiments for algorithm comparison

### Circuit Breaker Pattern
- Prevents cascading failures
- Automatic recovery with HALF_OPEN state
- Per-service circuit breakers
- Fallback responses when services are down

### Rate Limiting
- Sliding window algorithm (prevents boundary burst)
- Per-user and global rate limits
- RFC 6585 compliant headers (X-RateLimit-*)
- Token bucket for burst handling

### Feature Store
- Online features with TTL support
- User features: avg_rating, favorite_genres, engagement_score, segment
- Item features: popularity, genre_vector, freshness
- Context features: time_of_day, device_type, session_length

### Real-Time WebSocket Streaming
- Push-based recommendation updates
- Subscribe/interact protocol
- Connection health monitoring (ping/pong)
- Room-based broadcasting

### Security
- Security headers (CSP, HSTS, X-Frame-Options)
- Input validation (Pydantic models)
- Request size limits
- Dangerous path blocking
- Request ID tracking

### Observability
- Prometheus metrics (request count, latency, active connections)
- Structured logging (JSON in production, human-readable in dev)
- Grafana dashboards (request rate, latency percentiles, error rate)
- Alert rules (high error rate, high latency, service down)
- Request tracing with correlation IDs

### CI/CD (GitHub Actions)
- Code quality (Ruff lint, MyPy type checking)
- Unit + Integration tests with coverage
- Docker build verification
- Security scanning (Bandit, Safety)

### Database Migrations (Alembic-ready)
- SQLAlchemy 2.0 async ORM
- Schema versioning support
- Seed data pipeline

---

## Dataset

**MovieLens 25M** (GroupLens Research)

| Metric | Value |
|--------|-------|
| Ratings | 25,000,009 |
| Movies | 62,423 |
| Users | 162,541 |
| Tags | 1,093,360 |
| Timespan | 1995-2019 |
| Rating Scale | 0.5 - 5.0 |

**Mapping to Beauty Products:**
- Movies → Products (items to recommend)
- Genres → Categories (skincare, makeup, haircare)
- Ratings → Purchase/Satisfaction signals
- Tags → Attributes (organic, vegan, SPF)
- Overview → Product descriptions

---

## Technologies

### Backend Stack
| Layer | Technology | Purpose |
|-------|-----------|---------|
| API | FastAPI 0.109 | Async HTTP framework |
| ORM | SQLAlchemy 2.0 | Async database access |
| Database | SQLite | Zero-config persistence |
| Cache | In-memory + Redis-ready | Sub-ms feature serving |
| ML | PyTorch, implicit, LightGBM | Model training/inference |
| ANN | FAISS | Fast similarity search |
| Logging | structlog | Structured observability |

### Frontend Stack
| Technology | Purpose |
|-----------|---------|
| React 18 | Component-based UI |
| Vite 5 | Fast build tooling |
| TailwindCSS 3 | Utility-first styling |
| Zustand | State management |
| React Router 6 | Client-side routing |
| Framer Motion | Smooth animations |

### DevOps Stack
| Technology | Purpose |
|-----------|---------|
| Docker + Compose | Container orchestration |
| Nginx | Reverse proxy + static serving |
| Prometheus | Metrics collection |
| Grafana | Dashboard visualization |
| GitHub Actions | CI/CD pipeline |
| Locust | Load testing |

---

## API Documentation

### Base URL: `http://localhost:8000/api/v1`

### Core Endpoints

```
POST   /recommendations/              — Get personalized recommendations
GET    /recommendations/similar/{id}  — Find similar items
GET    /recommendations/trending      — Get trending items
POST   /recommendations/interact      — Record user interaction
GET    /recommendations/user/{id}/profile — User preference profile
GET    /recommendations/debug/model-status — Model health

GET    /movies/                       — List movies (paginated)
GET    /movies/search/                — Full-text search
GET    /movies/{id}                   — Movie details
GET    /movies/genres/list            — All genres

POST   /users/                        — Register user
GET    /users/{id}                    — User profile
POST   /users/rate                    — Rate a movie

GET    /experiments/                  — List A/B experiments
POST   /experiments/{name}/assign     — Get variant assignment
GET    /experiments/{name}/results    — Experiment results

WS     /ws/recommendations/{user_id}  — Real-time recommendations

GET    /health                        — System health check
```

### Example: Get Recommendations
```bash
curl -X POST http://localhost:8000/api/v1/recommendations/ \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "num_recommendations": 10, "algorithm": "hybrid"}'
```

### Example: Real-Time WebSocket
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/recommendations/user123");
ws.send(JSON.stringify({type: "subscribe", algorithm: "hybrid", num_recommendations: 10}));
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

---

## Setup & Installation

### Prerequisites
- Python 3.11+ (we use 3.14)
- Node.js 18+
- MovieLens 25M dataset at `/path/to/ml-25m/` (or it will download)

### One-Command Start
```bash
git clone https://github.com/aayush598/hybrid-recsys.git
cd hybrid-recsys

# Create venv and install backend deps
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# Run (seeds data + trains models on first run, ~60s)
chmod +x start.sh
./start.sh
```

Open **http://localhost:3000** in your browser.

### Manual Start
```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..

# Seed data (100K ratings, ~9K movies)
cd backend && PYTHONPATH=. python seed_data.py --sample

# Train models (ALS + content index + trending)
PYTHONPATH=. python evaluate.py

# Start backend
PYTHONPATH=. python -m uvicorn app.main:app --reload --port 8000

# Start frontend (new terminal)
cd frontend && npm run dev
```

### Dataset Setup
The system expects MovieLens 25M data. Place it at `backend/data/raw/ml-25m/` or symlink:
```bash
ln -s /path/to/ml-25m backend/data/raw/ml-25m
```
If not found, it will download automatically (~250MB).

### Access Points
| Service | URL |
|---------|-----|
| Frontend (UI) | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/api/v1/health |

---

## Evaluation

### Metrics

| Metric | K=5 | K=10 | K=20 | Target |
|--------|-----|------|------|--------|
| Precision@K | — | — | — | >0.15 |
| Recall@K | — | — | — | >0.20 |
| NDCG@K | — | — | — | >0.25 |
| MAP@K | — | — | — | >0.15 |
| Hit Rate@K | — | — | — | >0.60 |
| Coverage | — | — | — | >0.30 |
| Diversity | — | — | — | >0.40 |
| Novelty | — | — | — | >0.50 |
| Avg Latency | — | — | — | <100ms |

### Evaluation Protocol
- **Split:** Temporal (train on older, test on newer ratings)
- **Relevance:** Rating >= 3.5
- **Test Users:** >= 10 ratings
- **Sample:** 500 users

### Run Evaluation
```bash
cd backend && python evaluate.py
# Results saved to data/evaluation/evaluation_results.json
```

---

## Test Cases

### Successful Scenarios
1. **Active user** with 50+ ratings → Personalized hybrid recommendations
2. **Content discovery** → Finds movies similar to liked genres
3. **Trending for cold start** → Popular movies for new users
4. **Similar items** → Genre-consistent recommendations
5. **Real-time updates** → WebSocket pushes after interaction

### Failure Scenarios
1. **Cold start (new user)** → Falls back to trending model
2. **Cold start (new item)** → Only recommended via content-based
3. **Popularity bias** → Over-represents popular items
4. **Sparse data** → Inaccurate with <5 ratings
5. **Service degradation** → Circuit breaker activates fallback

---

## Comparison with Existing Products

| Aspect | BeautyRec | Netflix | Spotify | Amazon |
|--------|-----------|---------|---------|--------|
| Architecture | Two-stage hybrid | Two-stage hybrid | Two-stage hybrid | Item-CF + DL |
| CF Model | ALS + NCF | Members-to-Members | WALS | Item-to-item CF |
| Content | TF-IDF + Genres | Member Portraits | Audio + NLP | Product embeddings |
| ANN | FAISS | Custom ANN | Annoy | Custom ANN |
| Ranking | LightGBM LTR | Custom DL | DL ranker | Wide & Deep |
| Real-time | WebSocket | Real-time | Real-time context | Real-time |
| Explainability | Per-item explanations | "Because you watched..." | "Because you listened..." | "Also bought..." |
| A/B Testing | Built-in framework | Thousands/year | Continuous | Continuous |
| Observability | Prometheus + Grafana | Internal | Internal | Internal |

### What We Share with Netflix
- Two-stage candidate generation + ranking
- Hybrid ensemble approach
- A/B testing for algorithm comparison
- Diversity-aware re-ranking

### What We Share with Spotify
- Content-based audio/genre features
- Session-based recommendations
- Cold-start handling via trending

### What We Share with Amazon
- Item-to-item similarity
- Collaborative filtering signals
- Real-time personalization

---

## Known Limitations

1. **Cold Start:** New users/items need interaction history
2. **Popularity Bias:** Popular items over-represented
3. **No Visual Features:** Product images not used (would add CLIP)
4. **No Sequential Modeling:** No session dynamics (would add SASRec/GRU4Rec)
5. **Static Model:** No online learning from real-time feedback
6. **Single Domain:** No cross-domain transfer learning
7. **No Knowledge Graph:** No external entity linking
8. **Simplified LTR:** LightGBM instead of deep ranker

---

## Future Improvements

### Short-term (1-2 weeks)
- [ ] GRU4Rec/SA4Rec for sequential recommendations
- [ ] Deep Learning ranker (DNN-based LTR)
- [ ] Redis cluster for distributed caching
- [ ] PostgreSQL for production database
- [ ] Kubernetes deployment manifests

### Medium-term (1-2 months)
- [ ] CLIP embeddings for visual similarity
- [ ] Knowledge graph (actors, directors, studios)
- [ ] Multi-objective optimization (relevance + diversity + fairness)
- [ ] Online learning (FTRL for real-time model updates)
- [ ] Feature store with Feast

### Long-term (3-6 months)
- [ ] Federated learning for privacy-preserving training
- [ ] Conversational AI for interactive recommendations
- [ ] Multi-modal recommendations (text + images + audio)
- [ ] Cross-domain transfer (movies → beauty products)
- [ ] SHAP/LIME for explainable AI

---

## Project Structure

```
beautyrec/
├── backend/
│   ├── app/
│   │   ├── api/v1/              # API routes (REST + WebSocket)
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic settings
│   │   │   ├── logging.py       # Structured logging (structlog)
│   │   │   ├── exceptions.py    # Custom exception hierarchy
│   │   │   ├── governance/      # Data catalog, lineage, PII handling
│   │   │   ├── monitoring/      # Model drift, distributed tracing
│   │   │   ├── validation/      # Data validation, anomaly detection
│   │   │   └── optimization/    # Chunked I/O, FAISS, compact structures
│   │   ├── db/                  # SQLAlchemy ORM models + async sessions
│   │   ├── features/            # Feature store (online/offline)
│   │   ├── middleware/           # Security headers, monitoring, rate limiting
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── serving/             # A/B testing, circuit breaker, cache, batch
│   │   └── services/            # Business logic (recommendations, model manager)
│   ├── ml/
│   │   ├── models/
│   │   │   ├── collaborative_filtering.py  # ALS + FAISS ANN
│   │   │   ├── content_based.py            # TF-IDF + genre features
│   │   │   ├── neural_cf.py                # PyTorch NCF (GMF + MLP)
│   │   │   ├── two_tower.py                # Neural retrieval model
│   │   │   ├── ltr_ranker.py               # LightGBM LambdaMART
│   │   │   ├── hybrid.py                   # Late fusion ensemble
│   │   │   ├── mab.py                      # Multi-armed bandit
│   │   │   └── session_based.py            # GRU4Rec session model
│   │   ├── scalable/             # Chunked processing, Parquet, streaming
│   │   ├── pipelines/            # ETL pipeline, feature engineering
│   │   └── evaluation/
│   │       ├── metrics.py        # Precision, Recall, NDCG, MAP, Coverage
│   │       └── bias_fairness.py  # Popularity bias, diversity, fairness
│   ├── tests/
│   │   ├── unit/                 # Unit tests (20+ test cases)
│   │   ├── integration/          # API integration tests
│   │   └── load/                 # Locust load tests
│   ├── evaluate.py               # Evaluation runner
│   └── seed_data.py              # Data ingestion
├── frontend/
│   └── src/
│       ├── components/           # Header, MovieCard
│       ├── pages/                # Home, Explore, MovieDetail
│       ├── services/api.ts       # Axios API client
│       ├── context/useAppStore.ts # Zustand state management
│       └── types/index.ts        # TypeScript types
├── infra/
│   ├── kubernetes/
│   │   ├── base/                 # Deployment, Service, HPA, Ingress, PDB
│   │   └── overlays/             # Dev, staging, prod Kustomize overlays
│   ├── terraform/
│   │   ├── modules/              # EKS, RDS, ElastiCache, S3
│   │   └── environments/         # Dev, prod Terraform configs
│   ├── docker/                   # Nginx reverse proxy config
│   ├── monitoring/               # Prometheus rules + Grafana dashboards
│   └── scripts/                  # Setup and deployment scripts
├── docs/
│   ├── adr/                      # 6 Architecture Decision Records
│   ├── architecture/             # System overview, microservices design
│   ├── data/                     # Engineering guide, governance
│   ├── ml/                       # Algorithms guide, training guide
│   ├── security/                 # Security guide
│   ├── deployment/               # Deployment guide
│   ├── evaluation/               # Evaluation guide
│   └── operations/               # Operations guide
├── CONTRIBUTING.md                # Contribution guidelines
├── CODE_OF_CONDUCT.md             # Community standards
├── SECURITY.md                    # Security policy
├── CHANGELOG.md                   # Version history
├── docker-compose.yml             # Full stack (backend + frontend + Redis + Prometheus + Grafana)
├── Dockerfile.backend             # Backend container
├── Dockerfile.frontend            # Frontend container
├── pyproject.toml                 # Python dependencies + tool config
└── README.md                      # This file
```

---

## License

MIT License

## Acknowledgments

- GroupLens Research for the MovieLens 25M dataset
- Netflix for the two-stage architecture pattern
- Orbo.ai for the BeautyGPT domain inspiration
- Facebook Research for FAISS
- Microsoft for LightGBM
- The implicit library for ALS implementation
