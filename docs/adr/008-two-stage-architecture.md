# ADR-001: Two-Stage Recommendation Architecture

## Status
Accepted

## Date
2025-01-01

## Context

We need to recommend items from a catalog of 62,000+ movies to 162,000+ users. The system must serve recommendations in <100ms while maintaining high quality.

Single-stage approaches face a fundamental tradeoff:
- Brute-force scoring of all items: O(n) per query, too slow
- Pre-filtering then scoring: loses important signals
- Single neural model: cannot balance speed and accuracy

## Decision

We adopt a two-stage architecture:
1. **Candidate Generation**: Fast retrieval of ~500 candidates using FAISS ANN search
2. **Ranking**: Precise scoring of candidates using hybrid ensemble model

This is the same architecture used by Netflix, YouTube, Amazon, and TikTok.

## Consequences

### Positive
- Candidate generation: <10ms (FAISS ANN)
- Ranking: <50ms (500 items only)
- Total latency: <100ms (well within budget)
- Each stage can be optimized independently
- Easy to A/B test different models at each stage

### Negative
- More complex than single-model approach
- Two separate systems to maintain
- Candidate generation quality affects ranking ceiling

### Mitigations
- Comprehensive test coverage for each stage
- Circuit breaker for graceful degradation
- Fallback to trending when models are unavailable

## Alternatives Considered

1. **Single neural model**: Too slow for 62K items
2. **Pre-filtering + scoring**: Loses serendipity
3. **Content-based only**: No collaborative signals
4. **Collaborative only**: Cold start problem

## References

- YouTube: "Deep Neural Networks for YouTube Recommendations" (2016)
- Netflix: "System Design for Recommendations and Search" (2022)
- Amazon: "Deep Learning at Amazon" (2019)
