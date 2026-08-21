"""Advanced batch processing for recommendation pre-computation."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable


class AdvancedBatchProcessor:
    """Pre-compute and manage batch recommendation jobs."""

    def __init__(self):
        self._jobs: dict[str, dict] = {}
        self._results: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._counter = 0

    def precompute_recommendations(
        self, user_ids: list[str], model: Any, top_k: int = 20
    ) -> dict[str, list[tuple[int, float]]]:
        """Batch pre-compute recommendations for a set of users."""
        results = {}
        for uid in user_ids:
            try:
                recs = model.predict(uid, top_k=top_k) if hasattr(model, "predict") else []
                results[uid] = recs
            except Exception:
                results[uid] = []
        return results

    def schedule_batch_job(
        self, job_func: Callable, interval_seconds: int = 3600
    ) -> str:
        """Schedule a recurring batch job."""
        with self._lock:
            self._counter += 1
            job_id = f"batch_{self._counter}"

        def _run():
            while True:
                time.sleep(interval_seconds)
                with self._lock:
                    if job_id not in self._jobs or not self._jobs[job_id]["active"]:
                        break
                try:
                    result = job_func()
                    with self._lock:
                        self._results[job_id] = {
                            "result": result,
                            "last_run": datetime.now(timezone.utc).isoformat(),
                        }
                except Exception as e:
                    with self._lock:
                        self._results[job_id] = {
                            "error": str(e),
                            "last_run": datetime.now(timezone.utc).isoformat(),
                        }

        now = datetime.now(timezone.utc)
        with self._lock:
            self._jobs[job_id] = {
                "active": True,
                "interval_seconds": interval_seconds,
                "created_at": now.isoformat(),
                "next_run": now.isoformat(),
            }

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return job_id

    def get_job_status(self, job_id: str) -> dict:
        """Get status of a batch job."""
        with self._lock:
            if job_id not in self._jobs:
                return {"status": "not_found"}
            job = self._jobs[job_id].copy()
            job["last_result"] = self._results.get(job_id, {})
            return job

    def stop_job(self, job_id: str) -> bool:
        """Stop a running batch job."""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["active"] = False
                return True
            return False

    def incremental_update(
        self, existing_recs: dict, new_interactions: list[dict], model: Any
    ) -> dict:
        """Update recommendations based on new interactions."""
        updated_users = set()
        for interaction in new_interactions:
            uid = interaction.get("user_id")
            if uid:
                updated_users.add(uid)

        for uid in updated_users:
            try:
                new_recs = model.predict(uid, top_k=20) if hasattr(model, "predict") else []
                existing_recs[uid] = new_recs
            except Exception:
                pass

        return existing_recs
