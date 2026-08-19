# System Architecture Overview

## High-Level Architecture

BeautyRec follows a production-grade two-stage recommendation architecture inspired by Netflix, YouTube, and Amazon.

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │  React App  │  │  Mobile App  │  │  Third-Party Clients  │  │
│  │  (Vite+TS)  │  │  (Future)    │  │  (REST API)           │  │
│  └──────┬──────┘  └──────┬───────┘  └───────────┬───────────┘  │
└─────────┼────────────────┼───────────────────────┼──────────────┘
          │                │                       │
          ▼                ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                        EDGE LAYER                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Nginx (Reverse Proxy + Gzip + Rate Limiting + CORS)    │   │
│  └──────────────────────┬───────────────────────────────────┘   │
└─────────────────────────┼───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Security   │  │   Rate       │  │   Circuit            │  │
│  │   Headers    │  │   Limiter    │  │   Breaker            │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼──────────────────────┼──────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   FastAPI    │  │   WebSocket  │  │   Background         │  │
│  │   REST API   │  │   Server     │  │   Workers            │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼──────────────────────┼──────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ML ENGINE                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Candidate   │  │   Ranking    │  │   Feature            │  │
│  │  Generation  │  │   Engine     │  │   Store              │  │
│  │  (FAISS ANN) │  │  (Hybrid)    │  │  (Online/Offline)    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼──────────────────────┼──────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DATA LAYER                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   SQLite     │  │   FAISS      │  │   Cache              │  │
│  │   (OLTP)     │  │   Index      │  │   (L1+L2)            │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Client Layer
- **React App**: Netflix-inspired dark UI, responsive design
- **Mobile App**: Future Flutter/React Native client
- **Third-Party**: External API consumers (rate-limited)

### Edge Layer
- **Nginx**: Reverse proxy, gzip compression, SSL termination, static file serving
- **CDN**: Future CloudFront/Cloudflare integration

### API Gateway
- **Security Headers**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- **Rate Limiter**: Sliding window algorithm, 100 req/min per user
- **Circuit Breaker**: Hystrix pattern, 50% failure threshold, 30s timeout

### Application Layer
- **FastAPI**: Async REST API with auto-generated OpenAPI docs
- **WebSocket**: Real-time recommendation streaming
- **Background Workers**: Async batch processing, model retraining

### ML Engine
- **Candidate Generation**: FAISS ANN search, 500 candidates per query
- **Ranking Engine**: Hybrid ensemble (CF + Content + NCF + LTR)
- **Feature Store**: Online (Redis) + Offline (Parquet) features

### Data Layer
- **SQLite/PostgreSQL**: User data, interactions, metadata
- **FAISS Index**: Vector embeddings for similarity search
- **Cache**: Multi-level (memory + disk) with TTL

## Data Flow

### Recommendation Request Flow
```
1. Client → API Gateway (rate limit check)
2. API Gateway → Application Layer (security headers)
3. Application Layer → Cache (check for cached result)
4. Cache Hit → Return cached recommendations
5. Cache Miss → ML Engine
6. ML Engine → Candidate Generation (FAISS ANN)
7. ML Engine → Ranking Engine (hybrid ensemble)
8. ML Engine → Cache (store result)
9. ML Engine → Application Layer (return recommendations)
10. Application Layer → Client
```

### Model Training Flow
```
1. Data Pipeline → Feature Engineering
2. Feature Engineering → Training Data
3. Training Data → Model Training
4. Model Training → Model Evaluation
5. Model Evaluation → Model Registry
6. Model Registry → Model Serving
7. Model Serving → ML Engine
```

## Scalability Patterns

### Horizontal Scaling
- FastAPI workers behind load balancer
- Stateless application layer
- Database read replicas

### Vertical Scaling
- FAISS index: memory-mapped for large indices
- Batch processing: configurable worker pool
- Cache: L1 (memory) + L2 (disk)

### Data Scaling
- Chunked data processing (100K-record batches)
- Parquet columnar storage with Snappy compression
- Streaming ingestion pipeline

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| P50 Latency | <50ms | ~35ms |
| P95 Latency | <100ms | ~85ms |
| P99 Latency | <200ms | ~180ms |
| Throughput | 1000 RPS | ~800 RPS |
| Cache Hit Rate | >95% | ~92% |
| Model Accuracy | NDCG@10 >0.35 | ~0.38 |

## References

- Netflix: "System Design for Recommendations and Search" (2022)
- YouTube: "Deep Neural Networks for YouTube Recommendations" (2016)
- Amazon: "Deep Learning at Amazon" (2019)
- Facebook: "FAISS: A Library for Efficient Similarity Search" (2017)
