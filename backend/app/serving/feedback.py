"""Feedback loop for continuous model improvement."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger("serving.feedback")


class FeedbackLoop:
    """Collect user feedback and trigger model retraining."""

    def __init__(self):
        self._feedback: dict[str, list[dict]] = {}
        self._feedback_counts: dict[str, dict] = {}

    def record_feedback(
        self,
        user_id: str | int,
        item_id: int,
        feedback_type: str,
        value: float,
        timestamp: datetime | None = None,
    ) -> None:
        """Record user feedback on a recommendation."""
        ts = timestamp or datetime.now(timezone.utc)
        entry = {
            "user_id": str(user_id),
            "item_id": item_id,
            "feedback_type": feedback_type,
            "value": value,
            "timestamp": ts.isoformat(),
        }

        key = str(item_id)
        if key not in self._feedback:
            self._feedback[key] = []
        self._feedback[key].append(entry)

        if key not in self._feedback_counts:
            self._feedback_counts[key] = {"total": 0, "positive": 0, "negative": 0}
        self._feedback_counts[key]["total"] += 1
        if value > 0.5:
            self._feedback_counts[key]["positive"] += 1
        elif value < 0.5:
            self._feedback_counts[key]["negative"] += 1

        logger.info(
            "feedback_recorded",
            user_id=str(user_id),
            item_id=item_id,
            feedback_type=feedback_type,
            value=value,
        )

    def get_item_feedback(self, item_id: int) -> dict[str, Any]:
        """Get aggregated feedback for an item."""
        key = str(item_id)
        counts = self._feedback_counts.get(key, {"total": 0, "positive": 0, "negative": 0})
        entries = self._feedback.get(key, [])

        avg_rating = 0.0
        if entries:
            ratings = [e["value"] for e in entries if e["feedback_type"] == "rating"]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

        return {
            "item_id": item_id,
            "total_feedback": counts["total"],
            "positive_count": counts["positive"],
            "negative_count": counts["negative"],
            "avg_rating": round(avg_rating, 3),
            "sentiment_ratio": round(counts["positive"] / counts["total"], 3) if counts["total"] > 0 else 0.5,
        }

    def get_user_feedback_summary(self, user_id: str | int) -> dict[str, Any]:
        """Get feedback summary for a user."""
        uid = str(user_id)
        all_feedback = []
        for entries in self._feedback.values():
            all_feedback.extend([e for e in entries if e["user_id"] == uid])

        if not all_feedback:
            return {
                "user_id": uid,
                "total_feedback": 0,
                "avg_rating": 0.0,
                "top_items": [],
            }

        ratings = [e["value"] for e in all_feedback if e["feedback_type"] == "rating"]
        item_counts = {}
        for e in all_feedback:
            iid = e["item_id"]
            item_counts[iid] = item_counts.get(iid, 0) + 1

        top_items = sorted(item_counts.items(), key=lambda x: -x[1])[:10]

        return {
            "user_id": uid,
            "total_feedback": len(all_feedback),
            "avg_rating": round(sum(ratings) / len(ratings), 3) if ratings else 0.0,
            "top_items": [iid for iid, _ in top_items],
        }

    def should_retrain(
        self, model_metrics: dict[str, float], threshold: float = 0.1
    ) -> bool:
        """Check if model should be retrained based on metric degradation."""
        baseline_keys = ["precision_at_k", "recall_at_k", "ndcg_at_k"]
        for key in baseline_keys:
            current = model_metrics.get(f"current_{key}", 0.0)
            baseline = model_metrics.get(f"baseline_{key}", 0.0)
            if baseline > 0 and (baseline - current) / baseline > threshold:
                logger.warning(
                    "retraining_triggered",
                    metric=key,
                    baseline=baseline,
                    current=current,
                    degradation=f"{((baseline - current) / baseline) * 100:.1f}%",
                )
                return True
        return False

    def apply_feedback(
        self, model: Any, feedback_batch: list[dict]
    ) -> dict[str, Any]:
        """Apply a batch of feedback to update model metrics."""
        updated_count = 0
        for fb in feedback_batch:
            self.record_feedback(
                user_id=fb.get("user_id", "unknown"),
                item_id=fb.get("item_id", 0),
                feedback_type=fb.get("feedback_type", "implicit"),
                value=fb.get("value", 0.5),
            )
            updated_count += 1

        return {
            "updated_count": updated_count,
            "total_stored": sum(len(v) for v in self._feedback.values()),
        }
