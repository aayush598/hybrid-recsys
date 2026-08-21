"""Unit tests for MLOps: experiment tracking, HPO, registry, seeding."""

from __future__ import annotations

import numpy as np
import pytest


class TestExperimentTracker:
    def test_log_and_retrieve_experiment(self):
        from app.mlops.experiment_tracker import ExperimentTracker

        tracker = ExperimentTracker()
        experiment_id = tracker.log_experiment(
            "baseline-v1",
            params={"factors": 64},
            metrics={"recall_at_10": 0.42},
            artifacts=["model.pkl"],
        )
        record = tracker.get_experiment(experiment_id)
        assert record["name"] == "baseline-v1"
        assert record["params"]["factors"] == 64
        assert record["metrics"]["recall_at_10"] == 0.42

    def test_metric_history_steps(self):
        from app.mlops.experiment_tracker import ExperimentTracker

        tracker = ExperimentTracker()
        experiment_id = tracker.log_experiment("training-run")
        for step, value in enumerate([0.1, 0.3, 0.6]):
            tracker.log_metric(experiment_id, "ndcg", value, step=step)
        history = tracker.get_metric_history(experiment_id, "ndcg")
        assert [step for step, _ in history] == [0, 1, 2]
        assert [value for _, value in history] == [0.1, 0.3, 0.6]

    def test_compare_experiments_highlights_best(self):
        from app.mlops.experiment_tracker import ExperimentTracker

        tracker = ExperimentTracker()
        worse = tracker.log_experiment("worse", metrics={"map": 0.2})
        better = tracker.log_experiment("better", metrics={"map": 0.8})
        comparison = tracker.compare_experiments([worse, better])
        assert comparison["best_per_metric"]["map"]["experiment_id"] == better
        assert comparison["n_experiments"] == 2

    def test_delete_unknown_experiment_raises(self):
        from app.mlops.experiment_tracker import ExperimentTracker

        tracker = ExperimentTracker()
        with pytest.raises(KeyError):
            tracker.delete_experiment("does-not-exist")


class TestHyperparameterOptimizer:
    @staticmethod
    def _objective(X, y, params):
        """Quadratic in alpha so the optimum is known."""
        return -((params["alpha"] - 0.7) ** 2)

    def test_grid_search_finds_best_cell(self):
        from app.mlops.hpo import HyperparameterOptimizer

        optimizer = HyperparameterOptimizer(seed=42)
        best = optimizer.grid_search(
            {"alpha": [0.1, 0.5, 0.9], "beta": [1]},
            self._objective,
            X=None,
            y=None,
        )
        assert best["alpha"] == pytest.approx(0.5)  # closest grid point to 0.7
        assert len(optimizer.history) == 3

    def test_random_search_respects_trial_count(self):
        from app.mlops.hpo import HyperparameterOptimizer

        optimizer = HyperparameterOptimizer(seed=42)
        best = optimizer.random_search(
            {"alpha": (0.0, 1.0)},
            self._objective,
            X=None,
            y=None,
            n_trials=10,
        )
        assert 0.0 <= best["alpha"] <= 1.0
        assert len(optimizer.history) == 10

    def test_result_exposes_best_trial(self):
        from app.mlops.hpo import HyperparameterOptimizer

        optimizer = HyperparameterOptimizer(seed=42)
        optimizer.grid_search({"alpha": [0.2, 0.4, 0.6]}, self._objective, None, None)
        result = optimizer.result()
        assert result.best_score == max(trial.score for trial in result.trials)


class TestModelRegistry:
    def test_register_defaults_to_staging(self):
        from app.mlops.model_registry import ModelRegistry

        registry = ModelRegistry()
        model_id = registry.register_model("hybrid", "v1", metrics={"ndcg": 0.31})
        record = registry.get_model("hybrid", version="v1")
        assert record["stage"] == "staging"
        assert record["model_id"] == model_id

    def test_promote_to_production_demotes_previous(self):
        from app.mlops.model_registry import ModelRegistry

        registry = ModelRegistry()
        v1 = registry.register_model("ranker", "1.0")
        v2 = registry.register_model("ranker", "2.0")
        registry.promote_model(v1, "production")
        registry.promote_model(v2, "production")
        assert registry.get_model("ranker", version="2.0")["stage"] == "production"
        assert registry.get_model("ranker", version="1.0")["stage"] == "archived"

    def test_duplicate_version_rejected(self):
        from app.mlops.model_registry import ModelRegistry

        registry = ModelRegistry()
        registry.register_model("cf", "v1")
        with pytest.raises(ValueError):
            registry.register_model("cf", "v1")

    def test_rollback_restores_old_version(self):
        from app.mlops.model_registry import ModelRegistry

        registry = ModelRegistry()
        v1 = registry.register_model("two_tower", "v1")
        v2 = registry.register_model("two_tower", "v2")
        registry.promote_model(v2, "production")
        registry.rollback_model("two_tower", "v1")
        assert registry.get_model("two_tower", version="v1")["stage"] == "production"

    def test_history_audit_trail(self):
        from app.mlops.model_registry import ModelRegistry

        registry = ModelRegistry()
        model_id = registry.register_model("bpr", "v9")
        registry.promote_model(model_id, "production")
        actions = [entry["action"] for entry in registry.get_history("bpr", "v9")]
        assert actions == ["registered", "promoted"]

    def test_invalid_stage_rejected(self):
        from app.mlops.model_registry import ModelRegistry

        registry = ModelRegistry()
        model_id = registry.register_model("x", "v1")
        with pytest.raises(ValueError):
            registry.promote_model(model_id, "limbo")


class TestSetSeed:
    def test_returns_seed_and_sets_pythonhashseed(self):
        from app.mlops.reproducibility import set_seed

        assert set_seed(123) == 123
        import os

        assert os.environ["PYTHONHASHSEED"] == "123"

    def test_numpy_random_is_reproducible_after_seeding(self):
        from app.mlops.reproducibility import set_seed

        set_seed(99)
        first = np.random.rand(5)
        set_seed(99)
        second = np.random.rand(5)
        np.testing.assert_array_equal(first, second)

    def test_torch_seeded_when_available(self):
        torch = pytest.importorskip("torch")
        from app.mlops.reproducibility import set_seed

        set_seed(7)
        first = torch.rand(4)
        set_seed(7)
        second = torch.rand(4)
        assert torch.equal(first, second)
