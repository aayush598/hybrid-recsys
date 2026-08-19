# ADR-006: Compact Data Structures for Scalability

## Status
Accepted

## Date
2025-01-01

## Context

With 162K users and 62K items, storing full user interaction histories in memory is expensive (~2GB for full objects).

## Decision

Use probabilistic data structures:
- **Bloom Filter**: O(1) "has user seen item?" checks (~10 bits/element)
- **HyperLogLog**: Distinct item count estimation (~12KB total)
- **Cuckoo Filter**: With deletion support for item deduplication

## Consequences

### Positive
- Memory per user: ~200 bytes (vs ~2KB full objects)
- Total for 1M users: ~200MB (vs ~2GB)
- O(1) lookup time
- Configurable false positive rate

### Negative
- False positives possible (Bloom filter)
- No exact counts (HyperLogLog ~2% error)
- Cannot enumerate elements

### Mitigations
- False positive rate tuned to 1-5%
- Database fallback for exact counts
- Combined with exact storage for recent items

## References

- Bloom Filter: "Space/Time Trade-offs in Hash Coding" (1970)
- HyperLogLog: "HyperLogLog" (2007)
- Cuckoo Filter: "Cuckoo Filter" (2014)
