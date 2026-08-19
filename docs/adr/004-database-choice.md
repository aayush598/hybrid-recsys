# ADR-004: SQLite for Demo, PostgreSQL for Production

## Status
Accepted

## Date
2025-01-01

## Context

We need a database that works for both demo (zero-config) and production (high-scale).

## Decision

- **Demo/Development**: SQLite with aiosqlite (zero-config, file-based)
- **Production**: PostgreSQL with asyncpg (connection pooling, read replicas)

The code uses SQLAlchemy 2.0 async ORM which supports both transparently.

## Consequences

### Positive
- Demo: Zero setup, works immediately
- Production: Full ACID, connection pooling, read replicas
- Same code works with both (just change DATABASE_URL)

### Negative
- SQLite has limitations (no concurrent writes, no network access)
- Must test with both databases

### Mitigations
- CI/CD tests with both SQLite and PostgreSQL
- Feature flags for database-specific optimizations

## Alternatives Considered

1. **PostgreSQL only**: Adds setup complexity for demo
2. **MySQL**: Less feature-rich than PostgreSQL for our use case
3. **MongoDB**: Schema flexibility not needed for structured data

## References

- SQLAlchemy 2.0: https://docs.sqlalchemy.org/
- PostgreSQL: https://www.postgresql.org/
