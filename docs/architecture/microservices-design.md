# Microservices Design

## Service Decomposition

BeautyRec is designed as a modular monolith that can be decomposed into microservices as needed:

### Current Modular Monolith

```
┌─────────────────────────────────────────────────────────┐
│                   BeautyRec Application                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │    API       │  │     ML       │  │    Data      │  │
│  │   Service    │  │   Service    │  │   Service    │  │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤  │
│  │ - Endpoints  │  │ - Models     │  │ - ETL        │  │
│  │ - Auth       │  │ - Training   │  │ - Features   │  │
│  │ - WebSocket  │  │ - Inference  │  │ - Quality    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Future Microservices Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Rate Limiting + Auth + Load Balancing          │   │
│  └──────────────────────┬──────────────────────────┘   │
└─────────────────────────┼───────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Recommendation│  │ User         │  │ Content      │
│ Service       │  │ Service      │  │ Service      │
├──────────────┤  ├──────────────┤  ├──────────────┤
│ - Candidates │  │ - Profiles   │  │ - Metadata   │
│ - Ranking    │  │ - History    │  │ - Similarity │
│ - A/B Tests  │  │ - Preferences│  │ - Embeddings │
└──────────────┘  └──────────────┘  └──────────────┘
          │               │               │
          ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ ML Training  │  │ Analytics    │  │ Feature      │
│ Service      │  │ Service      │  │ Store        │
├──────────────┤  ├──────────────┤  ├──────────────┤
│ - Training   │  │ - Metrics    │  │ - Online     │
│ - Evaluation │  │ - Dashboards │  │ - Offline    │
│ - Deployment │  │ - Alerts     │  │ - Streaming  │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Service Communication Patterns

### Synchronous (Request-Response)
- **HTTP/REST**: Client → API Gateway → Services
- **WebSocket**: Real-time recommendation updates
- **gRPC**: Internal service communication (future)

### Asynchronous (Event-Driven)
- **Message Queue**: Model training events, data updates
- **Event Bus**: User interaction events, recommendation logs
- **Streaming**: Real-time feature updates, model predictions

### Circuit Breaker Pattern
```python
# Protects against cascading failures
@CircuitBreaker(failure_threshold=5, timeout=30)
async def get_recommendations(user_id: int):
    return await recommendation_service.get(user_id)
```

## Data Isolation

Each service owns its data:
- **Recommendation Service**: FAISS indices, cached recommendations
- **User Service**: User profiles, interaction history
- **Content Service**: Movie metadata, embeddings, genres
- **Analytics Service**: Metrics, logs, experiment results
- **Feature Store**: Feature definitions, online/offline stores

## API Versioning

```
/api/v1/recommendations/  # Current stable
/api/v2/recommendations/  # Next version
```

## References

- Microservices Patterns: Chris Richardson
- "Building Microservices" by Sam Newman
- Netflix: "Microservices at Netflix Scale" (2017)
