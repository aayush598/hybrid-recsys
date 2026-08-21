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

    if name == "BPRModel":
        from ml.models.bpr import BPRModel
        return BPRModel

    if name == "SVDCollaborativeFiltering":
        from ml.models.svd import SVDCollaborativeFiltering
        return SVDCollaborativeFiltering

    if name in ("SessionRecommender", "get_session_recommender"):
        from ml.models.session_based import SessionRecommender, get_session_recommender
        return {"SessionRecommender": SessionRecommender, "get_session_recommender": get_session_recommender}[name]

    if name in ("RecommendationBandit", "get_recommendation_bandit"):
        from ml.models.mab import RecommendationBandit, get_recommendation_bandit
        return {"RecommendationBandit": RecommendationBandit, "get_recommendation_bandit": get_recommendation_bandit}[name]

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
    "BPRModel",
    "SVDCollaborativeFiltering",
    "SessionRecommender",
    "RecommendationBandit",
]
