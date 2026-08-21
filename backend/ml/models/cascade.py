"""Multi-stage cascade recommendation pipeline.

Stage 1 (retrieve): cheap candidate generators produce a large pool.
Stage 2 (filter):   remove duplicates and already-seen items, apply
                    hard constraints.
Stage 3 (rank):     expensive rankers re-order the survivors.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)

Candidate = dict  # {"item_id": ..., "score": ...}
Generator = Callable[[str, int], list]
FilterFn = Callable[[list[Candidate], dict], list[Candidate]]
Ranker = Callable[[list[Candidate], int], list[Candidate]]


def _normalize(candidates) -> list[Candidate]:
    """Accept item ids, (item_id, score) tuples or dicts."""
    out: list[Candidate] = []
    for c in candidates or []:
        if isinstance(c, dict):
            out.append({"item_id": c.get("item_id"), "score": float(c.get("score", 0.0))})
        elif isinstance(c, (tuple, list)) and len(c) >= 2:
            out.append({"item_id": c[0], "score": float(c[1])})
        else:
            out.append({"item_id": c, "score": 0.0})
    return out


class CascadeRecommender:
    """Retrieve -> filter -> rank cascade."""

    def __init__(
        self,
        candidate_generators: list[Generator] | None = None,
        filters: list[FilterFn] | None = None,
        rankers: list[Ranker] | None = None,
    ):
        self.candidate_generators: list[Generator] = list(candidate_generators or [])
        self.filters: list[FilterFn] = list(filters or [])
        self.rankers: list[Ranker] = list(rankers or [])
        self.user_history: dict[str, set] = {}

    def add_generator(self, generator: Generator) -> None:
        self.candidate_generators.append(generator)

    def add_filter(self, filter_fn: FilterFn) -> None:
        self.filters.append(filter_fn)

    def add_ranker(self, ranker: Ranker) -> None:
        self.rankers.append(ranker)

    def retrieve(self, user_id: str, top_k: int = 100) -> list[Candidate]:
        """Stage 1: generate a broad candidate pool."""
        pool: dict = {}
        for generator in self.candidate_generators:
            try:
                for cand in _normalize(generator(user_id, top_k)):
                    item = cand["item_id"]
                    if item not in pool or cand["score"] > pool[item]["score"]:
                        pool[item] = cand
            except Exception:
                logger.exception("Candidate generator %r failed", generator)
        return list(pool.values())

    def filter(
        self,
        candidates: list[Candidate],
        constraints: dict | None = None,
    ) -> list[Candidate]:
        """Stage 2: deduplicate, drop already-seen items, apply constraints."""
        constraints = constraints or {}
        seen = set(constraints.get("seen_items", set())) | self.user_history.get(
            user_id := constraints.get("user_id", ""), set()
        )
        exclude = set(constraints.get("exclude_items", set()))

        unique: dict = {}
        for cand in candidates:
            item = cand["item_id"]
            if item in seen or item in exclude:
                continue
            if item not in unique or cand["score"] > unique[item]["score"]:
                unique[item] = cand

        filtered = list(unique.values())
        for filter_fn in self.filters:
            filtered = filter_fn(filtered, constraints)
        return filtered

    def rank(self, filtered_candidates: list[Candidate], top_k: int = 20) -> list[Candidate]:
        """Stage 3: re-rank with each registered ranker in order."""
        ranked = sorted(filtered_candidates, key=lambda c: c["score"], reverse=True)
        for ranker in self.rankers:
            try:
                ranked = ranker(ranked, top_k)
            except Exception:
                logger.exception("Ranker %r failed", ranker)
        return ranked[:top_k]

    def predict(self, user_id: str, top_k: int = 20) -> list[tuple]:
        """Run the full cascade and return ``[(item_id, score), ...]``."""
        candidates = self.retrieve(user_id, top_k=max(top_k * 5, 100))
        filtered = self.filter(candidates, constraints={"user_id": user_id})
        ranked = self.rank(filtered, top_k=top_k)
        return [(c["item_id"], c["score"]) for c in ranked]

    def record_interaction(self, user_id: str, item_id) -> None:
        """Track an interaction so the item is filtered in future runs."""
        self.user_history.setdefault(user_id, set()).add(item_id)


__all__ = ["CascadeRecommender"]
