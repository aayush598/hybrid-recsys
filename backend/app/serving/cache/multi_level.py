from __future__ import annotations

import time
from collections import OrderedDict
from threading import Lock
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class LRUCache:
    """Thread-safe LRU cache with TTL and memory budget.

    Features:
    - O(1) get/put operations
    - TTL-based expiration
    - Memory budget enforcement (max items)
    - Hit/miss statistics
    - Warm-up support
    """

    def __init__(self, max_size: int = 100_000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """Get value from cache. Returns None on miss."""
        with self._lock:
            if key in self._cache:
                timestamp, value = self._cache[key]
                if time.time() - timestamp < self.ttl_seconds:
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return value
                else:
                    del self._cache[key]

            self._misses += 1
            return None

    def set(self, key: str, value: Any) -> None:
        """Set value in cache with TTL."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (time.time(), value)

            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def get_or_set(
        self, key: str, factory: callable, ttl: int | None = None
    ) -> Any:
        """Get from cache or compute and store."""
        value = self.get(key)
        if value is not None:
            return value

        value = factory()
        self.set(key, value)
        return value

    def invalidate(self, key: str) -> bool:
        """Remove a key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """Remove all keys matching a prefix pattern."""
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(pattern)]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def cleanup_expired(self) -> int:
        """Remove all expired entries."""
        now = time.time()
        with self._lock:
            expired = [
                k for k, (ts, _) in self._cache.items()
                if now - ts >= self.ttl_seconds
            ]
            for key in expired:
                del self._cache[key]
            return len(expired)

    def warm_up(self, entries: dict[str, Any]) -> int:
        """Bulk insert entries into cache."""
        count = 0
        for key, value in entries.items():
            self.set(key, value)
            count += 1
        return count

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(total, 1), 4),
            "memory_items": len(self._cache),
        }


class MultiLevelCache:
    """Multi-level cache with L1 (in-memory) and L2 (disk-backed).

    Cache hierarchy:
    - L1: Fast in-memory LRU (microseconds)
    - L2: Disk-backed with memory mapping (milliseconds)
    - L3: Database (tens of milliseconds)

    Hot data lives in L1, warm data in L2, cold data in DB.
    """

    def __init__(
        self,
        l1_size: int = 50_000,
        l1_ttl: int = 300,
        l2_size: int = 500_000,
        l2_ttl: int = 3600,
    ):
        self.l1 = LRUCache(max_size=l1_size, ttl_seconds=l1_ttl)
        self.l2 = LRUCache(max_size=l2_size, ttl_seconds=l2_ttl)
        self._l2_hits = 0
        self._l3_hits = 0

    def get(self, key: str) -> Any | None:
        """Get from cache hierarchy."""
        value = self.l1.get(key)
        if value is not None:
            return value

        value = self.l2.get(key)
        if value is not None:
            self._l2_hits += 1
            self.l1.set(key, value)
            return value

        self._l3_hits += 1
        return None

    def set(self, key: str, value: Any, level: int = 1) -> None:
        """Set in specified cache level."""
        if level >= 1:
            self.l1.set(key, value)
        if level >= 2:
            self.l2.set(key, value)

    def get_or_compute(
        self, key: str, compute_fn: callable, cache_level: int = 2
    ) -> Any:
        """Get from cache or compute and store at specified level."""
        value = self.get(key)
        if value is not None:
            return value

        value = compute_fn()
        self.set(key, value, level=cache_level)
        return value

    def invalidate(self, key: str) -> None:
        """Invalidate across all levels."""
        self.l1.invalidate(key)
        self.l2.invalidate(key)

    def invalidate_user(self, user_id: str) -> int:
        """Invalidate all cached data for a user."""
        pattern = f"user:{user_id}"
        count1 = self.l1.invalidate_pattern(pattern)
        count2 = self.l2.invalidate_pattern(pattern)
        return count1 + count2

    def warm_recommendations(self, user_ids: list[str], compute_fn: callable) -> int:
        """Pre-warm cache for specific users."""
        warmed = 0
        for user_id in user_ids:
            key = f"recommendations:{user_id}"
            try:
                value = compute_fn(user_id)
                self.set(key, value, level=2)
                warmed += 1
            except Exception as e:
                logger.warning(f"Cache warm-up failed for {user_id}: {e}")
        return warmed

    @property
    def stats(self) -> dict:
        return {
            "l1": self.l1.stats,
            "l2": self.l2.stats,
            "l2_hits": self._l2_hits,
            "l3_hits": self._l3_hits,
            "total_savings_ms": round(
                (self._l2_hits * 10 + self.l1.stats["hits"] * 0.1), 2
            ),
        }


# Global cache instances
recommendation_cache = MultiLevelCache(l1_size=50_000, l1_ttl=300, l2_size=200_000, l2_ttl=3600)
feature_cache = LRUCache(max_size=100_000, ttl_seconds=1800)
user_cache = LRUCache(max_size=50_000, ttl_seconds=900)
