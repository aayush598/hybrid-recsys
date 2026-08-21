"""Reproducibility utilities: seeding, environment snapshots, data hashing,
and full experiment state save/restore."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def set_seed(seed: int = 42) -> int:
    """Seed python, numpy, and torch RNGs for deterministic runs."""
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        logger.debug("torch not installed; skipped torch seeding")
    return seed


class EnvironmentSnapshot:
    """Capture the runtime environment (python, packages, env vars)."""

    def __init__(self, capture_env_vars: bool = True) -> None:
        self.capture_env_vars = capture_env_vars

    def capture(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of the current environment."""
        snapshot: dict[str, Any] = {
            "timestamp": time.time(),
            "python_version": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        }
        if self.capture_env_vars:
            snapshot["env_vars"] = {
                k: v for k, v in os.environ.items() if not k.upper().endswith(("KEY", "TOKEN", "SECRET", "PASSWORD"))
            }
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "freeze"],
                capture_output=True, text=True, timeout=60, check=False,
            )
            snapshot["pip_freeze"] = result.stdout.splitlines()
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("pip freeze failed: %s", exc)
            snapshot["pip_freeze"] = []
        return snapshot

    def save(self, path: str | Path) -> Path:
        """Persist the snapshot as JSON."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.capture(), indent=2))
        return path


class DataHasher:
    """Content hashes for dataframes — lightweight data versioning."""

    @staticmethod
    def hash_dataframe(df: pd.DataFrame, algorithm: str = "sha256") -> str:
        """Stable hash of dataframe contents (order-sensitive)."""
        serialized = pd.util.hash_pandas_object(df, index=True).to_numpy().tobytes()
        return hashlib.new(algorithm, serialized).hexdigest()

    @staticmethod
    def hash_file(path: str | Path, chunk_size: int = 1 << 20) -> str:
        """Hash a file on disk in chunks."""
        digest = hashlib.sha256()
        with open(path, "rb") as fh:
            while chunk := fh.read(chunk_size):
                digest.update(chunk)
        return digest.hexdigest()


class ExperimentReproducibility:
    """Save/restore the complete state needed to reproduce an experiment."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.snapshotter = EnvironmentSnapshot()
        self.hasher = DataHasher()

    def capture_state(
        self,
        params: dict[str, Any],
        data: pd.DataFrame | None = None,
        model_state: Any = None,
    ) -> dict[str, Any]:
        """Bundle seed, environment, data hash, params, and model state."""
        set_seed(self.seed)
        state: dict[str, Any] = {
            "seed": self.seed,
            "params": params,
            "environment": self.snapshotter.capture(),
            "captured_at": time.time(),
        }
        if data is not None:
            state["data_hash"] = self.hasher.hash_dataframe(data)
            state["data_columns"] = list(map(str, data.columns))
        if model_state is not None:
            state["model_state"] = self._serialize(model_state)
        return state

    def save(self, state: dict[str, Any], path: str | Path) -> Path:
        """Write experiment state to JSON."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2, default=str))
        logger.info("Saved experiment state to %s", path)
        return path

    @staticmethod
    def load(path: str | Path) -> dict[str, Any]:
        """Read experiment state back from JSON."""
        return json.loads(Path(path).read_text())

    def restore(self, state: dict[str, Any]) -> int:
        """Re-apply randomness controls from a saved state; returns seed."""
        seed = int(state.get("seed", self.seed))
        set_seed(seed)
        logger.info("Restored reproducibility state (seed=%d)", seed)
        return seed

    @staticmethod
    def _serialize(model_state: Any) -> Any:
        if isinstance(model_state, dict):
            return {k: ExperimentReproducibility._serialize(v) for k, v in model_state.items()}
        if isinstance(model_state, np.ndarray):
            return {"__ndarray__": model_state.tolist()}
        if isinstance(model_state, (int, float, str, bool, list, type(None))):
            return model_state
        return repr(model_state)

    @staticmethod
    def _deserialize(model_state: Any) -> Any:
        if isinstance(model_state, dict):
            if "__ndarray__" in model_state:
                return np.asarray(model_state["__ndarray__"])
            return {k: ExperimentReproducibility._deserialize(v) for k, v in model_state.items()}
        return model_state
