from __future__ import annotations

from ml.models.classic import (
    CollaborativeFilteringModel,
    ContentBasedModel,
    HybridEnsemble,
    TrendingModel,
)


def __getattr__(name: str):
    """Lazy imports for torch-dependent models."""
    if name in ("NeuralCollaborativeFiltering", "NCFTrainer"):
        from ml.models.neural_cf import NCFTrainer, NeuralCollaborativeFiltering
        return {"NeuralCollaborativeFiltering": NeuralCollaborativeFiltering, "NCFTrainer": NCFTrainer}[name]

    if name in ("TwoTowerModel", "TwoTowerIndex"):
        from ml.models.two_tower import TwoTowerIndex, TwoTowerModel
        return {"TwoTowerModel": TwoTowerModel, "TwoTowerIndex": TwoTowerIndex}[name]

    if name == "LearningToRankModel":
        from ml.models.ltr_ranker import LearningToRankModel
        return LearningToRankModel

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CollaborativeFilteringModel",
    "ContentBasedModel",
    "TrendingModel",
    "HybridEnsemble",
    "NeuralCollaborativeFiltering",
    "NCFTrainer",
    "TwoTowerModel",
    "TwoTowerIndex",
    "LearningToRankModel",
]
