"""In-memory model registry with stage promotion and rollback.

Mirrors the MLflow Model Registry workflow (staging -> production ->
archived) without external infrastructure.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

VALID_STAGES = ("staging", "production", "archived")


class ModelRegistry:
    """Registry of model versions with metrics, stages, and rollbacks."""

    def __init__(self) -> None:
        # name -> {version -> record}
        self._registry: dict[str, dict[str, dict[str, Any]]] = {}

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #
    def register_model(
        self,
        name: str,
        version: str,
        metrics: dict[str, float] | None = None,
        artifact_path: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> str:
        """Register a new model version; returns its model_id."""
        version = str(version)
        models = self._registry.setdefault(name, {})
        if version in models:
            raise ValueError(f"Model {name} version {version} already registered")
        model_id = uuid.uuid4().hex[:12]
        models[version] = {
            "model_id": model_id,
            "name": name,
            "version": version,
            "metrics": {k: float(v) for k, v in (metrics or {}).items()},
            "artifact_path": artifact_path,
            "params": dict(params or {}),
            "stage": "staging",
            "registered_at": time.time(),
            "updated_at": time.time(),
            "history": [{"action": "registered", "stage": "staging", "at": time.time()}],
        }
        logger.info("Registered %s v%s (%s)", name, version, model_id)
        return model_id

    # ------------------------------------------------------------------ #
    # Stage management
    # ------------------------------------------------------------------ #
    def promote_model(self, model_id: str, stage: str) -> dict[str, Any]:
        """Move a model to ``staging`` | ``production`` | ``archived``.

        Promoting to production demotes any existing production version.
        """
        if stage not in VALID_STAGES:
            raise ValueError(f"Invalid stage {stage!r}; expected one of {VALID_STAGES}")
        record = self._find_by_id(model_id)
        name = record["name"]
        if stage == "production":
            for ver, other in self._registry[name].items():
                if other["stage"] == "production":
                    other["stage"] = "archived"
                    other["history"].append(
                        {"action": "demoted", "stage": "archived", "at": time.time()}
                    )
        record["stage"] = stage
        record["updated_at"] = time.time()
        record["history"].append({"action": "promoted", "stage": stage, "at": time.time()})
        logger.info("Promoted %s v%s -> %s", name, record["version"], stage)
        return dict(record)

    def rollback_model(self, name: str, target_version: str) -> dict[str, Any]:
        """Re-promote an older version to production (current goes archived)."""
        models = self._registry.get(name, {})
        target = models.get(str(target_version))
        if target is None:
            raise KeyError(f"{name} has no version {target_version}")
        return self.promote_model(target["model_id"], "production")

    # ------------------------------------------------------------------ #
    # Retrieval
    # ------------------------------------------------------------------ #
    def get_model(self, name: str, stage: str | None = None, version: str | None = None) -> dict[str, Any]:
        """Fetch a model by name plus optional stage/version filter."""
        models = self._registry.get(name)
        if not models:
            raise KeyError(f"Unknown model: {name}")
        if version is not None:
            return dict(models[str(version)])
        candidates = [m for m in models.values() if stage is None or m["stage"] == stage]
        if not candidates:
            raise LookupError(f"No {name} model in stage={stage!r}")
        order = {"production": 0, "staging": 1, "archived": 2}
        best = min(candidates, key=lambda m: (order[m["stage"]], -m["updated_at"]))
        return dict(best)

    def list_models(self, stage: str | None = None) -> list[dict[str, Any]]:
        """List all registered models, optionally filtered by stage."""
        results: list[dict[str, Any]] = []
        for models in self._registry.values():
            for record in models.values():
                if stage is None or record["stage"] == stage:
                    results.append(dict(record))
        results.sort(key=lambda m: (m["name"], -m["updated_at"]))
        return results

    def get_history(self, name: str, version: str) -> list[dict[str, Any]]:
        """Return the audit trail for a specific version."""
        models = self._registry.get(name, {})
        record = models.get(str(version))
        if record is None:
            raise KeyError(f"{name} has no version {version}")
        return list(record["history"])

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _find_by_id(self, model_id: str) -> dict[str, Any]:
        for models in self._registry.values():
            for record in models.values():
                if record["model_id"] == model_id:
                    return record
        raise KeyError(f"Unknown model_id: {model_id}")

    def __contains__(self, name: object) -> bool:
        return name in self._registry

    def __len__(self) -> int:
        return sum(len(models) for models in self._registry.values())
