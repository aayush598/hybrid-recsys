from __future__ import annotations

import pickle

import lightgbm as lgb
import numpy as np
import pandas as pd

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class LearningToRankModel:
    """LightGBM Learning-to-Rank model.

    Implements LambdaMART ranking objective for precise item ranking.

    Architecture:
    - Features: user features + item features + interaction features
    - Objective: LambdaMART (listwise ranking)
    - Output: relevance score for ranking

    This is the "secret sauce" in production systems — while CF and
    content-based models generate candidates, the LTR model learns
    the optimal ranking from human-labeled data (clicks, purchases).
    """

    def __init__(
        self,
        n_estimators: int = 500,
        learning_rate: float = 0.05,
        max_depth: int = 6,
        num_leaves: int = 31,
        min_child_samples: int = 20,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        reg_alpha: float = 0.1,
        reg_lambda: float = 1.0,
    ):
        self.params = {
            "objective": "lambdarank",
            "metric": "ndcg",
            "eval_at": [5, 10, 20],
            "boosting_type": "gbdt",
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "max_depth": max_depth,
            "num_leaves": num_leaves,
            "min_child_samples": min_child_samples,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "reg_alpha": reg_alpha,
            "reg_lambda": reg_lambda,
            "verbose": -1,
            "n_jobs": -1,
            "random_state": 42,
        }
        self.model: lgb.LGBMRanker | None = None
        self.feature_names: list[str] = []
        self.is_trained = False

    def _build_features(
        self,
        user_features: dict[str, float],
        item_features: dict[str, float],
    ) -> dict[str, float]:
        """Build feature vector for a user-item pair."""
        features = {}

        for k, v in user_features.items():
            features[f"user_{k}"] = v

        for k, v in item_features.items():
            features[f"item_{k}"] = v

        # Cross features
        for u_key in ["avg_rating", "rating_count"]:
            for i_key in ["avg_rating", "popularity"]:
                if u_key in user_features and i_key in item_features:
                    features[f"cross_{u_key}_{i_key}"] = (
                        user_features[u_key] * item_features[i_key]
                    )

        genre_vector = item_features.get("genre_vector", {})
        if isinstance(genre_vector, dict):
            for genre, val in genre_vector.items():
                features[f"genre_{genre}"] = val

        return features

    def prepare_training_data(
        self,
        user_item_pairs: list[dict],
        labels: list[float],
        group_sizes: list[int],
    ) -> tuple[pd.DataFrame, list[int]]:
        """Prepare training data for LambdaMART."""
        all_features = []
        for pair in user_item_pairs:
            features = self._build_features(
                pair["user_features"], pair["item_features"]
            )
            all_features.append(features)

        df = pd.DataFrame(all_features)
        df = df.fillna(0)

        self.feature_names = list(df.columns)
        return df, group_sizes

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        group_train: list[int],
        X_val: pd.DataFrame | None = None,
        y_val: np.ndarray | None = None,
        group_val: list[int] | None = None,
    ) -> dict:
        """Train the LTR model."""
        self.model = lgb.LGBMRanker(**self.params)

        eval_set = [(X_train, y_train)]
        eval_group = [group_train]

        if X_val is not None and y_val is not None and group_val is not None:
            eval_set.append((X_val, y_val))
            eval_group.append(group_val)

        self.model.fit(
            X_train,
            y_train,
            group=group_train,
            eval_set=eval_set,
            eval_group=eval_group,
        )

        self.is_trained = True

        metrics = {}
        if self.model.evals_result_:
            for metric_name, values in self.model.evals_result_["valid_0"].items():
                metrics[f"train_{metric_name}"] = values[-1] if values else None

        logger.info(f"LTR model trained: {len(self.feature_names)} features")
        return metrics

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Predict relevance scores."""
        if not self.is_trained or self.model is None:
            return np.zeros(len(features))
        return self.model.predict(features)

    def rank_candidates(
        self,
        candidates: list[dict],
        user_features: dict[str, float],
    ) -> list[tuple[int, float]]:
        """Rank a list of candidate items for a user."""
        if not self.is_trained:
            return [(c["item_id"], 0.0) for c in candidates]

        feature_rows = []
        for candidate in candidates:
            features = self._build_features(user_features, candidate["item_features"])
            feature_rows.append(features)

        df = pd.DataFrame(feature_rows).reindex(columns=self.feature_names, fill_value=0)
        scores = self.predict(df)

        ranked = sorted(
            zip([c["item_id"] for c in candidates], scores),
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked

    def get_feature_importance(self) -> dict[str, float]:
        """Get feature importance for explainability."""
        if self.model is None:
            return {}
        importance = self.model.feature_importances_
        return dict(sorted(
            zip(self.feature_names, importance),
            key=lambda x: x[1],
            reverse=True,
        ))

    def save(self) -> None:
        """Save model to disk."""
        if self.model is None:
            return
        path = settings.MODEL_DIR
        path.mkdir(parents=True, exist_ok=True)
        with open(path / "ltr_model.pkl", "wb") as f:
            pickle.dump({"model": self.model, "feature_names": self.feature_names}, f)
        logger.info("LTR model saved")

    def load(self) -> bool:
        """Load model from disk."""
        path = settings.MODEL_DIR / "ltr_model.pkl"
        if not path.exists():
            return False
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            self.model = data["model"]
            self.feature_names = data["feature_names"]
            self.is_trained = True
            logger.info("LTR model loaded")
            return True
        except Exception as e:
            logger.error(f"Failed to load LTR model: {e}")
            return False
