"""Feature engineering pipeline: preprocessing, feature building, orchestration.

Complements :mod:`ml.pipelines.data_pipeline` (raw ETL) with reusable
feature transforms for model training and serving:

- :class:`DataPreprocessor`: missing values, outliers, scaling.
- :class:`FeatureEngineer`: user/item/interaction/temporal features.
- :class:`FeaturePipeline`: end-to-end fit/transform orchestration.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """DataFrame cleaner: imputation, outlier clipping, numeric scaling.

    Fits per-column statistics on ``fit`` and applies them on ``transform``.
    Numeric columns are imputed with the median (or mean), categorical
    columns with a constant, outliers are clipped to IQR fences, and
    numeric columns optionally standardized or min-max scaled.
    """

    def __init__(
        self,
        num_strategy: str = "median",
        cat_fill_value: Any = "unknown",
        clip_outliers: bool = True,
        iqr_factor: float = 1.5,
        scale: str | None = "standard",
    ):
        if num_strategy not in {"mean", "median", "zero"}:
            raise ValueError(f"Unsupported num_strategy: {num_strategy!r}")
        if scale not in {None, "standard", "minmax"}:
            raise ValueError(f"Unsupported scale: {scale!r}")
        self.num_strategy = num_strategy
        self.cat_fill_value = cat_fill_value
        self.clip_outliers = clip_outliers
        self.iqr_factor = iqr_factor
        self.scale = scale
        self.numeric_columns: list[str] = []
        self.categorical_columns: list[str] = []
        self.fill_values_: dict[str, float] = {}
        self.bounds_: dict[str, tuple[float, float]] = {}
        self.center_: dict[str, float] = {}
        self.spread_: dict[str, float] = {}
        self.is_fitted = False

    def fit(self, df: pd.DataFrame) -> DataPreprocessor:
        self.numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        self.categorical_columns = [
            c for c in df.columns if c not in self.numeric_columns
        ]
        for column in self.numeric_columns:
            values = df[column].dropna()
            fill = {
                "mean": values.mean() if len(values) else 0.0,
                "median": values.median() if len(values) else 0.0,
                "zero": 0.0,
            }[self.num_strategy]
            self.fill_values_[column] = float(fill)
            q1 = float(values.quantile(0.25)) if len(values) else 0.0
            q3 = float(values.quantile(0.75)) if len(values) else 0.0
            iqr = q3 - q1
            self.bounds_[column] = (
                float(q1 - self.iqr_factor * iqr),
                float(q3 + self.iqr_factor * iqr),
            )
            filled = df[column].fillna(fill)
            self.center_[column] = float(filled.mean())
            spread = float(filled.std()) if self.scale == "standard" else float(
                filled.max() - filled.min()
            )
            self.spread_[column] = spread if spread > 1e-12 else 1.0
        self.is_fitted = True
        logger.info(
            "DataPreprocessor fitted: %d numeric, %d categorical columns",
            len(self.numeric_columns),
            len(self.categorical_columns),
        )
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.is_fitted:
            raise RuntimeError("Call fit() before transform()")
        out = df.copy()
        for column in self.numeric_columns:
            if column not in out.columns:
                continue
            out[column] = out[column].fillna(self.fill_values_[column])
            if self.clip_outliers:
                low, high = self.bounds_[column]
                out[column] = out[column].clip(low, high)
            if self.scale == "standard":
                out[column] = (out[column] - self.center_[column]) / self.spread_[column]
            elif self.scale == "minmax":
                out[column] = (out[column] - self.center_[column]) / self.spread_[column]
        for column in self.categorical_columns:
            if column in out.columns:
                out[column] = out[column].fillna(self.cat_fill_value)
        return out

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).transform(df)


class FeatureEngineer:
    """Builds aggregate user, item, interaction, and temporal features."""

    def build_user_features(self, interactions: pd.DataFrame) -> pd.DataFrame:
        """Per-user behavioral aggregates keyed by ``user_id``."""
        grouped = interactions.groupby("user_id")["rating"]
        features = pd.DataFrame(
            {
                "user_rating_count": grouped.count(),
                "user_avg_rating": grouped.mean(),
                "user_rating_std": grouped.std().fillna(0.0),
            }
        ).reset_index()
        return features

    def build_item_features(self, interactions: pd.DataFrame) -> pd.DataFrame:
        """Per-item popularity aggregates keyed by ``item_id``."""
        grouped = interactions.groupby("item_id")["rating"]
        features = pd.DataFrame(
            {
                "item_popularity": grouped.count(),
                "item_avg_rating": grouped.mean(),
            }
        ).reset_index()
        return features

    @staticmethod
    def add_temporal_features(
        df: pd.DataFrame, timestamp_col: str = "timestamp"
    ) -> pd.DataFrame:
        """Add hour/day-of-week/weekend flags derived from a datetime column."""
        out = df.copy()
        stamps = pd.to_datetime(out[timestamp_col])
        out["hour"] = stamps.dt.hour
        out["day_of_week"] = stamps.dt.dayofweek
        out["is_weekend"] = (stamps.dt.dayofweek >= 5).astype(int)
        return out

    @staticmethod
    def build_interaction_features(interactions: pd.DataFrame) -> pd.DataFrame:
        """Attach the user's historical interaction count to every row."""
        counts = interactions.groupby("user_id").cumcount()
        out = interactions.copy()
        out["user_history_size"] = counts
        return out


class FeaturePipeline:
    """Orchestrates preprocessing and feature engineering into one transform."""

    def __init__(
        self,
        preprocessor: DataPreprocessor | None = None,
        engineer: FeatureEngineer | None = None,
        timestamp_col: str | None = "timestamp",
    ):
        self.preprocessor = preprocessor or DataPreprocessor(scale=None)
        self.engineer = engineer or FeatureEngineer()
        self.timestamp_col = timestamp_col
        self.user_features_: pd.DataFrame | None = None
        self.item_features_: pd.DataFrame | None = None
        self.is_fitted = False

    def fit(self, interactions: pd.DataFrame) -> FeaturePipeline:
        numeric = interactions.select_dtypes(include=[np.number])
        self.preprocessor.fit(numeric)
        self.user_features_ = self.engineer.build_user_features(interactions)
        self.item_features_ = self.engineer.build_item_features(interactions)
        self.is_fitted = True
        return self

    def transform(self, interactions: pd.DataFrame) -> pd.DataFrame:
        if not self.is_fitted:
            raise RuntimeError("Call fit() before transform()")
        out = interactions.copy()
        if self.timestamp_col and self.timestamp_col in out.columns:
            out = self.engineer.add_temporal_features(out, self.timestamp_col)
        out = self.engineer.build_interaction_features(out)
        for column in list(self.preprocessor.numeric_columns):
            if column in out.columns:
                values = out[[column]]
                values = self.preprocessor.transform(values)[column]
                out[column] = values.to_numpy()
        if self.user_features_ is not None:
            out = out.merge(self.user_features_, on="user_id", how="left")
        if self.item_features_ is not None:
            out = out.merge(self.item_features_, on="item_id", how="left")
        return out

    def fit_transform(self, interactions: pd.DataFrame) -> pd.DataFrame:
        return self.fit(interactions).transform(interactions)


__all__ = ["DataPreprocessor", "FeatureEngineer", "FeaturePipeline"]
