# ADR-005: Multi-Level Caching Strategy

## Status
Accepted

## Date
2025-01-01

## Context

Recommendation requests are frequent and expensive. We need to cache results without stale data.

## Decision

Three-level cache hierarchy:
- **L1**: In-memory LRU (50K items, 5min TTL) — microsecond reads
- **L2**: Disk-backed LRU (200K items, 1hr TTL) — millisecond reads
- **L3**: Database (source of truth) — tens of milliseconds

## Consequences

### Positive
- 95%+ cache hit rate for active users
- <1ms average cache read latency
- Automatic TTL expiration prevents stale data
- User interaction invalidates relevant cache entries

### Negative
- Cache consistency challenges
- Memory usage for L1 cache
- Cold start requires cache warming

### Mitigations
- Event-driven cache invalidation
- Cache warming on model update
- Memory budget monitoring

## Alternatives Considered

1. **Redis only**: Single point of failure, requires infrastructure
2. **In-memory only**: Limited by RAM
3. **No caching**: Too slow for repeated recommendations

## References

- Netflix: "EVCache" distributed caching
- Amazon: "DynamoDB Accelerator (DAX)"
