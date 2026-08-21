# ADR-003: FAISS for ANN Search

## Status
Accepted

## Date
2025-01-01

## Context

We need to retrieve similar items from 62K+ items in <10ms. Brute-force search is O(n) and too slow.

## Decision

We use Facebook's FAISS library with IVF (Inverted File Index) for items >10K and IVF+PQ (Product Quantization) for items >1M.

## Consequences

### Positive
- Sub-linear search: O(√n) for IVF, O(1) for IVF+PQ
- Memory-mapped indices: supports indices larger than RAM
- GPU acceleration available for very large scales
- Battle-tested at Facebook/Instagram scale

### Negative
- IVF requires training step
- PQ introduces approximation error
- Index must be rebuilt when items are added/removed

### Mitigations
- Periodic index rebuilding (daily for production)
- Flat fallback for small catalogs
- Quantization error <2% for our use case

## Alternatives Considered

1. **Annoy (Spotify)**: No IVF support, less flexible
2. **Milvus**: More features but heavier dependency
3. **pgvector**: Good for PostgreSQL but slower than FAISS
4. **Brute-force**: Too slow for >10K items

## References

- FAISS: https://github.com/facebookresearch/faiss
- IVF: "Efficient and robust approximate nearest neighbor search using HNSW graphs" (2016)
