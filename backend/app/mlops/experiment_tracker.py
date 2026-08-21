"""Lightweight in-memory experiment tracking.

Provides an MLflow-like interface for logging experiments, parameters,
metrics (with step history), and artifacts without any external service
dependency. Useful for local development, tests, and notebooks.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class ExperimentTracker:
    """In-memory experiment tracker with metric/param/artifact logging."""

    def __init__(self) -> None:
        self._experiments: dict[str, dict[str, Any]] = {}
        self._metric_history: dict[str, dict[str, list[tuple[int, float]]]] = defaultdict(
            lambda: defaultdict(list)
        )

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #
    def log_experiment(
        self,
        name: str,
        params: dict[str, Any] | None = None,
        metrics: dict[str, float] | None = None,
        artifacts: list[str] | None = None,
        tags: dict[str, str] | None = None,
    ) -> str:
        """Create a new experiment and return its id."""
        experiment_id = uuid.uuid4().hex[:12]
        self._experiments[experiment_id] = {
            "experiment_id": experiment_id,
            "name": name,
            "params": dict(params or {}),
            "metrics": {k: float(v) for k, v in (metrics or {}).items()},
            "artifacts": list(artifacts or []),
            "tags": dict(tags or {}),
            "created_at": time.time(),
            "updated_at": time.time(),
            "status": "finished",
        }
        for key, value in (metrics or {}).items():
            self._metric_history[experiment_id][key].append((0, float(value)))
        logger.info("Logged experiment %s (%s)", name, experiment_id)
        return experiment_id

    def log_metric(
        self, experiment_id: str, key: str, value: float, step: int | None = None
    ) -> None:
        """Append a metric value to an experiment's history."""
        exp = self._require(experiment_id)
        if step is None:
            history = self._metric_history[experiment_id][key]
            step = history[-1][0] + 1 if history else 0
        self._metric_history[experiment_id][key].append((int(step), float(value)))
        exp["metrics"][key] = float(value)
        exp["updated_at"] = time.time()

    def log_params(self, experiment_id: str, params: dict[str, Any]) -> None:
        """Merge additional hyperparameters into an experiment."""
        exp = self._require(experiment_id)
        exp["params"].update(params)
        exp["updated_at"] = time.time()

    def log_artifacts(self, experiment_id: str, artifacts: list[str]) -> None:
        """Attach artifact paths to an experiment."""
        exp = self._require(experiment_id)
        exp["artifacts"].extend(artifacts)
        exp["updated_at"] = time.time()

    # ------------------------------------------------------------------ #
    # Retrieval
    # ------------------------------------------------------------------ #
    def get_experiment(self, experiment_id: str) -> dict[str, Any]:
        """Return full experiment record including metric history."""
        exp = self._require(experiment_id)
        record = dict(exp)
        record["metric_history"] = {
            key: [(step, val) for step, val in steps]
            for key, steps in self._metric_history.get(experiment_id, {}).items()
        }
        return record

    def get_metric_history(
        self, experiment_id: str, key: str
    ) -> list[tuple[int, float]]:
        """Return the (step, value) series logged for one metric."""
        self._require(experiment_id)
        return list(self._metric_history[experiment_id].get(key, []))

    def list_experiments(self, name_filter: str | None = None) -> list[dict[str, Any]]:
        """List all experiments, newest first, optionally filtered by name."""
        experiments = [
            {k: v for k, v in exp.items() if k != "params" or True}
            for exp in self._experiments.values()
        ]
        experiments.sort(key=lambda e: e["created_at"], reverse=True)
        if name_filter:
            experiments = [e for e in experiments if name_filter in e["name"]]
        return experiments

    # ------------------------------------------------------------------ #
    # Comparison
    # ------------------------------------------------------------------ #
    def compare_experiments(self, ids: list[str]) -> dict[str, Any]:
        """Build a comparison table across experiments.

        Returns a dict with per-experiment rows plus best-value highlights
        for each shared metric.
        """
        records = [self.get_experiment(i) for i in ids]
        all_metrics: set[str] = set()
        all_params: set[str] = set()
        for rec in records:
            all_metrics.update(rec["metrics"])
            all_params.update(rec["params"])

        table: list[dict[str, Any]] = []
        for rec in records:
            row: dict[str, Any] = {"experiment_id": rec["experiment_id"], "name": rec["name"]}
            for metric in sorted(all_metrics):
                row[f"metric.{metric}"] = rec["metrics"].get(metric)
            for param in sorted(all_params):
                row[f"param.{param}"] = rec["params"].get(param)
            table.append(row)

        best: dict[str, Any] = {}
        for metric in sorted(all_metrics):
            values = {
                rec["experiment_id"]: rec["metrics"][metric]
                for rec in records
                if metric in rec["metrics"]
            }
            if values:
                best_id = max(values, key=values.get)
                best[metric] = {"experiment_id": best_id, "value": values[best_id]}

        return {"table": table, "best_per_metric": best, "n_experiments": len(records)}

    def delete_experiment(self, experiment_id: str) -> None:
        """Remove an experiment from the tracker."""
        self._require(experiment_id)
        del self._experiments[experiment_id]
        self._metric_history.pop(experiment_id, None)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _require(self, experiment_id: str) -> dict[str, Any]:
        if experiment_id not in self._experiments:
            raise KeyError(f"Unknown experiment_id: {experiment_id}")
        return self._experiments[experiment_id]

    @staticmethod
    def summarize(values: list[float]) -> dict[str, float]:
        """Convenience stats helper used by callers comparing runs."""
        arr = np.asarray(values, dtype=float)
        return {
            "mean": float(arr.mean()),
            "std": float(arr.std()),
            "min": float(arr.min()),
            "max": float(arr.max()),
        }

    def __len__(self) -> int:
        return len(self._experiments)

    def __contains__(self, experiment_id: object) -> bool:
        return experiment_id in self._experiments
