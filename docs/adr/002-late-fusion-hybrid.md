# ADR-002: Late Fusion Hybrid Ensemble

## Status
Accepted

## Date
2025-01-01

## Context

We have multiple recommendation signals: collaborative filtering, content-based, trending, and neural models. We need to combine them effectively.

## Decision

We use **late fusion**: each model generates independent scores, which are combined using weighted averaging.

```
Final Score = 0.30 × CF + 0.25 × Content + 0.20 × NCF + 0.15 × Trending + 0.10 × Diversity
```

## Consequences

### Positive
- Each model can be updated independently
- Easy to A/B test individual model contributions
- Better interpretability (we know which model contributed what)
- Graceful degradation (disable any model without affecting others)

### Negative
- Weights are hand-tuned (could be learned)
- No cross-model feature interactions
- Slightly lower accuracy than early fusion

### Mitigations
- Learned weights via LTR model
- Feature combination in LTR layer captures interactions

## Alternatives Considered

1. **Early fusion**: Concatenate all embeddings, train single model. More complex, harder to debug.
2. **Stacking**: Use a meta-learner. Requires held-out data, adds latency.
3. **Switching**: Use different models for different users. Loses ensemble benefits.

## References

- Netflix: "Artwork Personalization at Netflix" (late fusion)
- Spotify: "Discover Weekly" (late fusion with contextual signals)
