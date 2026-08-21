# ADR 004: Database Choice — SQLite for Dev, PostgreSQL for Prod

- **Status:** Accepted
- **Date:** 2026-08-21
- **Deciders:** Engineering team

## Context

The recommendation system needs transactional storage for users, products,
interactions, and feedback. Development happens mostly on laptops (and CI),
while production runs on AWS with high availability requirements.

## Decision

- **Development & tests:** SQLite via SQLAlchemy's `sqlite+aiosqlite` driver.
  Zero setup, file-based, trivially resettable; the entire test suite runs
  without any external services.
- **Production:** PostgreSQL on RDS (Multi-AZ, encrypted, automated backups —
  see `infra/terraform/modules/rds`). Chosen for concurrency under load,
  rich indexing, JSONB support for flexible product attributes, and mature
  operational tooling (read replicas, PITR, Performance Insights).

All data access goes through SQLAlchemy ORM models so the dialect swap is a
connection-string change (`DATABASE_URL`), never a code change.

## Alternatives Considered

- **SQLite everywhere** — unacceptable in production: single-writer locking,
  no network access, no managed HA/backups.
- **PostgreSQL everywhere including dev/tests** — better parity, but forces
  every contributor and CI runner to provision Postgres; slows iteration and
  flaky local setups outweigh parity gains at current scale.
- **MongoDB** — flexible documents, but our core relations (users → orders →
  items) are strongly relational; we would lose transactions/joins without
  gaining anything material.
- **MySQL/MariaDB** — workable, but JSONB, richer index types, and extension
  ecosystem favor Postgres.

## Consequences

- Positive: frictionless local development; production-grade durability and
  scalability; ORM keeps portability.
- Negative: minor dev/prod dialect differences (e.g., JSON operators,
  constraint behaviors) — mitigated by integration tests against real
  Postgres in staging before releases.
- Follow-up: keep migrations dialect-neutral (Alembic); run the migration
  suite against both engines in CI.
