# ADR 003: Technology Stack — Python, FastAPI, React

- **Status:** Accepted
- **Date:** 2026-08-21
- **Deciders:** Engineering team

## Context

We needed a stack for an ML-heavy recommendation service with a web UI that a
small team could build, ship, and maintain quickly. Requirements: strong ML
ecosystem, async I/O for low-latency APIs, fast iteration, type safety, and a
large hiring pool.

## Decision

- **Backend: Python 3.12+ with FastAPI.** Pydantic-based request/response
  validation, native async, automatic OpenAPI docs.
- **ML: scikit-learn / implicit-style libraries** with NumPy/pandas; models
  serialized as artifacts loaded in-process (see ADR 005).
- **Frontend: React with Vite + TypeScript**, consuming the REST API.
- **Infra: Docker + Kubernetes (Helm/Kustomize), Terraform on AWS.**

## Alternatives Considered

- **Django/Flask** — mature but either heavier than needed (Django ORM/admin
  unused) or too minimal (Flask lacks validation/OpenAPI out of the box).
  FastAPI gives async + validation + docs with less ceremony.
- **Node.js/NestJS backend** — good API ergonomics, but forces a second
  language boundary to the ML layer; model inference would need a Python
  sidecar anyway, adding operational complexity.
- **Go backend** — excellent performance, but the ML ecosystem is far weaker;
  training pipelines would still be Python.
- **Vue/Svelte frontend** — viable; React chosen for ecosystem maturity,
  component library availability, and team familiarity.

## Consequences

- Positive: one language across API and ML code; typed contracts end-to-end
  (Pydantic ↔ TypeScript types); fast onboarding due to mainstream choices.
- Negative: Python's raw throughput is below Go/Rust — mitigated by async
  FastAPI, caching (Redis), and horizontal autoscaling.
- Follow-up: generate TypeScript clients from the OpenAPI schema to keep
  contracts in sync.
