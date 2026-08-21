"""Hyperparameter optimization: grid, random, and Bayesian search.

Bayesian search uses a simplified surrogate-model approach (Gaussian
Process regression from scikit-learn) with Expected Improvement
acquisition — no Optuna dependency required.
"""

from __future__ import annotations

import itertools
import logging
import math
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
from scipy import stats
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern

logger = logging.getLogger(__name__)

ObjectiveFn = Callable[[Any, Any, dict[str, Any]], float]


@dataclass
class Trial:
    """A single hyperparameter evaluation."""
    params: dict[str, Any]
    score: float
    trial_number: int = 0


@dataclass
class HPOResult:
    """Result of an optimization run."""
    best_params: dict[str, Any]
    best_score: float
    trials: list[Trial] = field(default_factory=list)

    def top_n(self, n: int = 5) -> list[Trial]:
        return sorted(self.trials, key=lambda t: t.score, reverse=True)[:n]


class HyperparameterOptimizer:
    """Grid / random / Bayesian hyperparameter search utilities.

    ``objective_fn`` signature: ``(X, y, params) -> score`` where a higher
    score is better.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.history: list[Trial] = []

    # ------------------------------------------------------------------ #
    # Grid search
    # ------------------------------------------------------------------ #
    def grid_search(
        self,
        param_grid: dict[str, list[Any]],
        objective_fn: ObjectiveFn,
        X: Any,
        y: Any,
    ) -> dict[str, Any]:
        """Exhaustive search over the cartesian product of the grid."""
        keys = list(param_grid.keys())
        combos = list(itertools.product(*(param_grid[k] for k in keys)))
        logger.info("Grid search over %d combinations", len(combos))

        best_params: dict[str, Any] | None = None
        best_score = -math.inf
        self.history.clear()
        for i, values in enumerate(combos):
            params = dict(zip(keys, values))
            score = self._evaluate(objective_fn, X, y, params, i)
            if score > best_score:
                best_score, best_params = score, params
        logger.info("Grid search best score %.4f with %s", best_score, best_params)
        return best_params or {}

    # ------------------------------------------------------------------ #
    # Random search
    # ------------------------------------------------------------------ #
    def random_search(
        self,
        param_space: dict[str, Any],
        objective_fn: ObjectiveFn,
        X: Any,
        y: Any,
        n_trials: int = 50,
    ) -> dict[str, Any]:
        """Sample ``n_trials`` configurations from the parameter space.

        Each value may be a fixed constant, a scipy frozen distribution,
        a ``(low, high)`` tuple (uniform), or a list to sample uniformly.
        """
        best_params: dict[str, Any] | None = None
        best_score = -math.inf
        self.history.clear()
        for i in range(n_trials):
            params = {k: self._sample(v) for k, v in param_space.items()}
            score = self._evaluate(objective_fn, X, y, params, i)
            if score > best_score:
                best_score, best_params = score, params
        logger.info("Random search best score %.4f with %s", best_score, best_params)
        return best_params or {}

    # ------------------------------------------------------------------ #
    # Bayesian search (simplified GP + Expected Improvement)
    # ------------------------------------------------------------------ #
    def bayesian_search(
        self,
        param_space: dict[str, Any],
        objective_fn: ObjectiveFn,
        X: Any,
        y: Any,
        n_trials: int = 30,
        n_startup: int = 5,
        n_candidates: int = 200,
    ) -> dict[str, Any]:
        """Sequential model-based optimization with a GP surrogate.

        The first ``n_startup`` trials are random; afterwards candidates are
        drawn from the space and scored by Expected Improvement under the
        surrogate. Only numeric parameters participate in the surrogate;
        categorical values fall back to random sampling.
        """
        keys = sorted(param_space.keys())
        observed_X: list[list[float]] = []
        observed_y: list[float] = []
        best_params: dict[str, Any] | None = None
        best_score = -math.inf
        self.history.clear()

        for i in range(n_trials):
            if i < n_startup or not observed_X:
                params = {k: self._sample(param_space[k]) for k in keys}
            else:
                gp = GaussianProcessRegressor(
                    kernel=Matern(nu=2.5), alpha=1e-6, normalize_y=True,
                    random_state=self.seed,
                )
                gp.fit(np.asarray(observed_X), np.asarray(observed_y))
                candidates = np.column_stack(
                    [self._sample_array(param_space[k], n_candidates) for k in keys]
                )
                mean, std = gp.predict(candidates, return_std=True)
                z = (mean - best_score - 0.01) / np.maximum(std, 1e-9)
                ei = (mean - best_score - 0.01) * stats.norm.cdf(z) + std * stats.norm.pdf(z)
                params = {
                    k: self._from_float(param_space[k], candidates[int(np.argmax(ei))][j])
                    for j, k in enumerate(keys)
                }

            score = self._evaluate(objective_fn, X, y, params, i)
            numeric = [self._to_float(params[k]) for k in keys]
            if all(np.isfinite(v) for v in numeric):
                observed_X.append(numeric)
                observed_y.append(score)
            if score > best_score:
                best_score, best_params = score, params

        logger.info("Bayesian search best score %.4f with %s", best_score, best_params)
        return best_params or {}

    # ------------------------------------------------------------------ #
    # Sampling helpers
    # ------------------------------------------------------------------ #
    def _sample(self, spec: Any) -> Any:
        if hasattr(spec, "rvs"):
            # scipy frozen distribution (scipy >= 1.15 removed the public
            # ``stats.rv_frozen`` name, so duck-type instead).
            return float(spec.rvs(random_state=self.rng))
        if isinstance(spec, tuple) and len(spec) == 2 and all(
            isinstance(b, (int, float)) for b in spec
        ):
            low, high = spec
            if isinstance(low, int) and isinstance(high, int):
                return int(self.rng.integers(low, high + 1))
            return float(self.rng.uniform(low, high))
        if isinstance(spec, (list, tuple)):
            return spec[int(self.rng.integers(0, len(spec)))]
        return spec

    def _sample_array(self, spec: Any, n: int) -> np.ndarray:
        vals = [self._to_float(self._sample(spec)) for _ in range(n)]
        return np.asarray(vals, dtype=float)

    @staticmethod
    def _to_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(hash(str(value)) % 1000)

    @staticmethod
    def _from_float(spec: Any, value: float) -> Any:
        if isinstance(spec, tuple) and len(spec) == 2 and all(
            isinstance(b, int) for b in spec
        ):
            return int(round(value))
        if isinstance(spec, (list, tuple)):
            return spec[int(np.clip(round(value), 0, len(spec) - 1))]
        if isinstance(spec, bool):
            return bool(value >= 0.5)
        return value

    def _evaluate(
        self, objective_fn: ObjectiveFn, X: Any, y: Any, params: dict[str, Any], idx: int
    ) -> float:
        try:
            score = float(objective_fn(X, y, params))
        except Exception as exc:  # noqa: BLE001 - failed trials get worst score
            logger.warning("Trial %d failed (%s); assigning -inf", idx, exc)
            score = -math.inf
        self.history.append(Trial(params=params, score=score, trial_number=idx))
        return score

    def result(self) -> HPOResult:
        """Return the accumulated history as an :class:`HPOResult`."""
        valid = [t for t in self.history if math.isfinite(t.score)]
        best = max(valid, key=lambda t: t.score) if valid else None
        return HPOResult(
            best_params=dict(best.params) if best else {},
            best_score=best.score if best else -math.inf,
            trials=list(self.history),
        )
