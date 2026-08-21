# ADR 005: Model Serving Strategy — In-Process Serving

- **Status:** Accepted
- **Date:** 2026-08-21
- **Deciders:** ML engineering team

## Context

Recommendation models must be served with low latency (< 100 ms p95) behind
the FastAPI backend. Options ranged from loading models inside the API
process to running a dedicated model server (e.g., TF Serving, TorchServe,
Seldon) or a serverless inference endpoint.

Current scale: moderate traffic, models are lightweight (matrix factorization
embeddings + content similarity indexes), retraining happens on a schedule,
not continuously.

## Decision

We serve models **in-process** within the FastAPI backend:

1. Trained artifacts (model binaries + feature stores + ANN indexes) are
   versioned under `backend/data/models/` and shipped via the container image
   or pulled from object storage at startup.
2. Each backend worker loads the active model version into memory at boot;
   a `/models/reload` hook swaps versions atomically without restarts.
3. The model registry records which version is active; rollback = repointing
   the alias and reloading.

## Alternatives Considered

- **Dedicated model server (TorchServe/Seldon/KServe)** — clean separation
  and independent scaling, but adds a service to deploy/monitor, network hop
  latency (~5–20 ms), serialization overhead, and duplicated auth/observability
  plumbing. Not justified while models fit comfortably in API pod memory.
- **Serverless inference (SageMaker endpoints / Lambda)** — pay-per-use is
  attractive for spiky traffic, but cold starts violate our latency budget
  and per-invocation cost exceeds always-on pods at steady traffic.
- **Client-side inference** — would leak proprietary embeddings and features;
  rejected outright.

## Consequences

- Positive: minimal latency (no network hop), simplest possible deployment
  topology, one artifact pipeline, fewer services to secure and monitor.
- Negative: model memory shares pod resources with API work (mitigated by
  resource limits and HPA); scaling API scales models too even when only one
  is needed; heavy future models may force re-architecture.
- Trigger to revisit: if model load time exceeds ~30 s, memory per pod
  exceeds ~2 GiB, or GPU inference becomes necessary → move to a dedicated
  model server (documented in a superseding ADR).
