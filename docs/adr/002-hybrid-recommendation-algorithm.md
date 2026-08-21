# ADR 002: Hybrid Recommendation Algorithm

- **Status:** Accepted
- **Date:** 2026-08-21
- **Deciders:** ML engineering team

## Context

BeautyRec recommends beauty products where interaction data is sparse,
the catalog changes frequently, and trends shift fast (viral products).
No single algorithm covers all regimes:

| Regime | Problem for pure approaches |
| --- | --- |
| Cold-start users | Collaborative filtering has no signal |
| Cold-start items | CF needs interactions; new SKUs have none |
| Long tail | Content features still describe rare items |
| Trending/viral | Both CF and content lag behind sudden popularity spikes |

## Decision

We use a **hybrid recommender** combining three signals with a late-fusion
scoring layer:

1. **Collaborative filtering** (matrix factorization / embeddings) as the
   primary personalization signal for users with sufficient history.
2. **Content-based similarity** over product attributes (category, brand,
   ingredients, price band) to cover cold-start items and long-tail catalog.
3. **Trending/popularity score** computed over recent interaction windows to
   capture viral dynamics and provide a robust fallback.

Final score = weighted blend of normalized component scores, with weights
adapted by user history depth (new users lean on trending + content;
established users lean on CF).

## Alternatives Considered

- **Pure collaborative filtering** — best offline accuracy for heavy users,
  but fails completely on cold start and degrades as catalog churns.
- **Pure content-based** — solves cold start but produces homogeneous,
  low-serendipity recommendations ("more of the same").
- **Pure popularity/trending** — trivially robust but not personalized.
- **Deep sequential models (transformer-based)** — promising accuracy gains,
  rejected for now due to training/serving cost and data volume below the
  threshold where they clearly win.

## Consequences

- Positive: graceful degradation across all user/item regimes; each signal
  can be tuned or retrained independently.
- Negative: more moving parts — three pipelines to train, monitor, and serve;
  fusion weights need periodic re-tuning via offline evaluation.
- Follow-up: track per-signal contribution metrics to justify weight changes.
