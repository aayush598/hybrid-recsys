"""Unit tests for the feature engineering data pipeline (ml/pipelines/features)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _interactions() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "user_id": [f"u{i % 4}" for i in range(20)],
            "item_id": [f"i{i % 5}" for i in range(20)],
            "rating": rng.uniform(1, 5, size=20).round(2),
            "timestamp": pd.date_range("2026-01-01", periods=20, freq="6h"),
        }
    )


class TestDataPreprocessor:
    def test_fit_transform_imputes_and_scales(self):
        from ml.pipelines.features import DataPreprocessor

        df = pd.DataFrame({"value": [1.0, 2.0, np.nan, 4.0], "tag": ["a", None, "b", "a"]})
        preprocessor = DataPreprocessor(num_strategy="median", scale="standard")
        transformed = preprocessor.fit_transform(df)

        assert not transformed["value"].isna().any()
        assert not transformed["tag"].isna().any()
        assert transformed["tag"].iloc[1] == "unknown"
        assert transformed["value"].mean() == pytest.approx(0.0, abs=1e-9)
        assert preprocessor.is_fitted

    def test_outlier_clipping(self):
        from ml.pipelines.features import DataPreprocessor

        df = pd.DataFrame({"x": list(range(20)) + [10_000]})
        preprocessor = DataPreprocessor(clip_outliers=True, iqr_factor=1.5, scale=None)
        clipped = preprocessor.fit_transform(df)["x"]
        assert clipped.max() < 10_000

    def test_transform_before_fit_raises(self):
        from ml.pipelines.features import DataPreprocessor

        with pytest.raises(RuntimeError):
            DataPreprocessor().transform(pd.DataFrame({"x": [1]}))

    def test_invalid_strategy_rejected(self):
        from ml.pipelines.features import DataPreprocessor

        with pytest.raises(ValueError):
            DataPreprocessor(num_strategy="mode")
        with pytest.raises(ValueError):
            DataPreprocessor(scale="robust")


class TestFeatureEngineer:
    def test_user_features_aggregates(self):
        from ml.pipelines.features import FeatureEngineer

        features = FeatureEngineer().build_user_features(_interactions())
        assert set(features.columns) >= {"user_id", "user_rating_count", "user_avg_rating"}
        assert features["user_rating_count"].sum() == 20
        assert len(features) == _interactions()["user_id"].nunique()

    def test_item_features_popularity(self):
        from ml.pipelines.features import FeatureEngineer

        features = FeatureEngineer().build_item_features(_interactions())
        assert {"item_id", "item_popularity", "item_avg_rating"} <= set(features.columns)
        assert (features["item_popularity"] > 0).all()

    def test_temporal_features(self):
        from ml.pipelines.features import FeatureEngineer

        enriched = FeatureEngineer.add_temporal_features(_interactions())
        assert {"hour", "day_of_week", "is_weekend"} <= set(enriched.columns)
        assert enriched["is_weekend"].isin([0, 1]).all()

    def test_interaction_history_size(self):
        from ml.pipelines.features import FeatureEngineer

        enriched = FeatureEngineer.build_interaction_features(_interactions())
        first_user_rows = enriched[enriched["user_id"] == "u0"]["user_history_size"]
        assert first_user_rows.tolist() == sorted(first_user_rows.tolist())


class TestFeaturePipeline:
    def test_fit_transform_end_to_end(self):
        from ml.pipelines.features import FeaturePipeline

        pipeline = FeaturePipeline()
        result = pipeline.fit_transform(_interactions())

        assert pipeline.is_fitted
        expected_columns = {
            "rating", "hour", "day_of_week", "is_weekend",
            "user_history_size", "user_rating_count", "item_popularity",
        }
        assert expected_columns <= set(result.columns)
        assert len(result) == 20

    def test_transform_requires_fit(self):
        from ml.pipelines.features import FeaturePipeline

        with pytest.raises(RuntimeError):
            FeaturePipeline().transform(_interactions())

    def test_merge_produces_consistent_aggregates(self):
        from ml.pipelines.features import FeaturePipeline

        result = FeaturePipeline().fit_transform(_interactions())
        user_row = result[result["user_id"] == "u1"]
        assert user_row["user_rating_count"].nunique() == 1
