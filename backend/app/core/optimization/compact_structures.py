from __future__ import annotations

import hashlib
import math
from array import array


class BloomFilter:
    """Space-efficient probabilistic data structure for set membership.

    Used for:
    - Checking if a user has already seen an item (O(1) lookup)
    - Deduplication of events
    - Quick negative checks before expensive DB lookups

    Memory: ~10 bits per element for 1% false positive rate.
    For 10M items: ~12.5MB vs ~400MB for a set of IDs.
    """

    def __init__(self, expected_items: int = 1_000_000, fp_rate: float = 0.01):
        self.size = self._optimal_size(expected_items, fp_rate)
        self.hash_count = self._optimal_hash_count(self.size, expected_items)
        self.bits = array("b", [0] * ((self.size + 7) // 8))
        self._count = 0

    @staticmethod
    def _optimal_size(n: int, p: float) -> int:
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return int(math.ceil(m))

    @staticmethod
    def _optimal_hash_count(m: int, n: int) -> int:
        k = (m / n) * math.log(2)
        return int(math.ceil(k))

    def _hashes(self, item: str) -> list[int]:
        """Double hashing for k independent hash functions."""
        h1 = int(hashlib.md5(item.encode()).hexdigest(), 16)
        h2 = int(hashlib.sha1(item.encode()).hexdigest(), 16)
        return [(h1 + i * h2) % self.size for i in range(self.hash_count)]

    def add(self, item: str) -> None:
        """Add an item to the filter."""
        for pos in self._hashes(item):
            byte_idx = pos // 8
            bit_idx = pos % 8
            self.bits[byte_idx] |= (1 << bit_idx)
        self._count += 1

    def contains(self, item: str) -> bool:
        """Check if an item might be in the set (may have false positives)."""
        return all(
            (self.bits[pos // 8] >> (pos % 8)) & 1
            for pos in self._hashes(item)
        )

    def __contains__(self, item: str) -> bool:
        return self.contains(item)

    @property
    def estimated_count(self) -> int:
        return self._count

    @property
    def memory_bytes(self) -> int:
        return len(self.bits)


class HyperLogLog:
    """Probabilistic cardinality estimator.

    Estimates the number of distinct elements in a stream
    using O(log(log(n))) memory.

    For 10M distinct users: ~12KB memory vs ~400MB for a set.
    Accuracy: ~2% standard error with default precision.
    """

    def __init__(self, precision: int = 14):
        self.precision = precision
        self.num_registers = 1 << precision
        self.registers = array("b", [0] * self.num_registers)
        self._alpha = self._compute_alpha()

    @staticmethod
    def _compute_alpha() -> float:
        return 0.7213 / (1 + 1.079 / 64)

    def _hash(self, item: str) -> int:
        return int(hashlib.sha256(item.encode()).hexdigest(), 16)

    def add(self, item: str) -> None:
        """Add an element to the estimator."""
        h = self._hash(item)
        register_idx = h & (self.num_registers - 1)
        w = h >> self.precision
        self.registers[register_idx] = max(
            self.registers[register_idx],
            self._leading_zeros(w) + 1,
        )

    def _leading_zeros(self, value: int) -> int:
        if value == 0:
            return 64 - self.precision
        count = 0
        for i in range(64 - self.precision, -1, -1):
            if (value >> i) & 1:
                break
            count += 1
        return count

    def count(self) -> int:
        """Estimate the cardinality."""
        raw = self._alpha * self.num_registers ** 2 / sum(
            2.0 ** -reg for reg in self.registers
        )

        if raw <= 2.5 * self.num_registers:
            zeros = self.registers.count(0)
            if zeros > 0:
                return int(self.num_registers * math.log(self.num_registers / zeros))

        return int(raw)

    def merge(self, other: HyperLogLog) -> None:
        """Merge another HLL into this one."""
        for i in range(self.num_registers):
            self.registers[i] = max(self.registers[i], other.registers[i])

    @property
    def memory_bytes(self) -> int:
        return len(self.registers)


class CuckooFilter:
    """Space-efficient alternative to Bloom filter with deletion support.

    Unlike Bloom filter:
    - Supports deletion
    - Better performance for high load factors
    - Similar memory usage

    Used for tracking "already recommended" items per user
    where deletion is needed when items expire.
    """

    def __init__(self, capacity: int = 1_000_000, fp_rate: float = 0.01, bucket_size: int = 4):
        self.capacity = capacity
        self.bucket_size = bucket_size
        self.num_buckets = math.ceil(capacity / bucket_size)
        self.buckets = [array("I", [0] * bucket_size) for _ in range(self.num_buckets)]
        self._count = 0
        self.max_kicks = 500

    def _hash(self, item: str) -> tuple[int, int]:
        h = int(hashlib.md5(item.encode()).hexdigest(), 16)
        fingerprint = (h >> 32) & 0xFFFFFFFF
        if fingerprint == 0:
            fingerprint = 1
        idx1 = h % self.num_buckets
        idx2 = (idx1 ^ (fingerprint % self.num_buckets)) % self.num_buckets
        return fingerprint, idx1 if idx1 != idx2 else (idx1 + 1) % self.num_buckets

    def add(self, item: str) -> bool:
        """Add item to filter. Returns False if full."""
        if self._count >= self.capacity:
            return False

        fp, idx1 = self._hash(item)

        for i in range(self.bucket_size):
            if self.buckets[idx1][i] == 0:
                self.buckets[idx1][i] = fp
                self._count += 1
                return True

        idx2 = (idx1 ^ (fp % self.num_buckets)) % self.num_buckets
        for i in range(self.bucket_size):
            if self.buckets[idx2][i] == 0:
                self.buckets[idx2][i] = fp
                self._count += 1
                return True

        victim_bucket = idx1
        for _ in range(self.max_kicks):
            slot = int.from_bytes(b"\x00" * 4, "little") % self.bucket_size
            victim_fp = self.buckets[victim_bucket][slot]
            self.buckets[victim_bucket][slot] = fp
            fp = victim_fp

            victim_bucket = (victim_bucket ^ (fp % self.num_buckets)) % self.num_buckets
            for i in range(self.bucket_size):
                if self.buckets[victim_bucket][i] == 0:
                    self.buckets[victim_bucket][i] = fp
                    self._count += 1
                    return True

        return False

    def contains(self, item: str) -> bool:
        """Check if item might be in the filter."""
        fp, idx1 = self._hash(item)
        idx2 = (idx1 ^ (fp % self.num_buckets)) % self.num_buckets

        for i in range(self.bucket_size):
            if self.buckets[idx1][i] == fp or self.buckets[idx2][i] == fp:
                return True
        return False

    def __contains__(self, item: str) -> bool:
        return self.contains(item)

    @property
    def memory_bytes(self) -> int:
        return sum(b.nbytes for b in self.buckets)


class CompactUserHistory:
    """Memory-efficient user interaction history using compact structures.

    Instead of storing full interaction objects, uses:
    - Bloom filter for O(1) "has user seen item?" checks
    - HyperLogLog for distinct item count estimation
    - Compact arrays for recent interactions

    Memory per user: ~200 bytes vs ~2KB for full objects.
    For 1M users: ~200MB vs ~2GB.
    """

    def __init__(self, user_id: str, history_size: int = 100):
        self.user_id = user_id
        self.seen_filter = BloomFilter(expected_items=1000, fp_rate=0.05)
        self.distinct_counter = HyperLogLog(precision=10)
        self.recent_items: list[int] = []
        self.history_size = history_size
        self._rating_sum = 0.0
        self._rating_count = 0

    def record_interaction(self, movie_id: int, rating: float | None = None) -> None:
        """Record a user interaction compactly."""
        key = f"{self.user_id}:{movie_id}"
        self.seen_filter.add(key)
        self.distinct_counter.add(str(movie_id))

        self.recent_items.append(movie_id)
        if len(self.recent_items) > self.history_size:
            self.recent_items.pop(0)

        if rating is not None:
            self._rating_sum += rating
            self._rating_count += 1

    def has_seen(self, movie_id: int) -> bool:
        """Check if user has seen an item (may have false positives)."""
        return self.seen_filter.contains(f"{self.user_id}:{movie_id}")

    @property
    def estimated_distinct_count(self) -> int:
        return self.distinct_counter.count()

    @property
    def avg_rating(self) -> float:
        return self._rating_sum / max(self._rating_count, 1)

    @property
    def memory_bytes(self) -> int:
        return (
            self.seen_filter.memory_bytes
            + self.distinct_counter.memory_bytes
            + len(self.recent_items) * 8
        )
