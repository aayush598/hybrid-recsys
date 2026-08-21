"""Feature pipeline for computing and caching features."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from app.data.feature_engineering import FeatureEngineer


class FeaturePipeline:
    """End-to-end feature computation pipeline."""

    def __init__(self, cache_dir: str = "data/cache"):
        self.engineer = FeatureEngineer()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self, movies_df: pd.DataFrame, ratings_df: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
        """Run full feature pipeline and return (user_features, item_features, metadata)."""
        user_features = self.engineer.compute_user_features(ratings_df)
        item_features = self.engineer.compute_item_features(movies_df, ratings_df)

        metadata = {
            "num_users": len(user_features),
            "num_items": len(item_features),
            "num_ratings": len(ratings_df),
            "avg_rating": float(ratings_df["rating"].mean()) if not ratings_df.empty else 0.0,
        }

        return user_features, item_features, metadata

    def validate_features(self, features: dict[str, pd.DataFrame]) -> dict:
        """Validate computed features for quality issues."""
        results = {}
        for name, df in features.items():
            validation = {
                "num_rows": len(df),
                "num_columns": len(df.columns),
                "nan_counts": int(df.isna().sum().sum()),
                "inf_counts": int(np.isinf(df.select_dtypes(include=[np.number]).values).sum()) if not df.select_dtypes(include=[np.number]).empty else 0,
                "is_valid": True,
            }
            if validation["nan_counts"] > 0 or validation["inf_counts"] > 0:
                validation["is_valid"] = False
            results[name] = validation
        return results

    def cache_features(self, features: dict[str, pd.DataFrame], tag: str = "default") -> str:
        """Save features to cache directory."""
        cache_path = self.cache_dir / f"features_{tag}"
        cache_path.mkdir(parents=True, exist_ok=True)

        for name, df in features.items():
            df.to_parquet(cache_path / f"{name}.parquet", index=False)

        manifest = {"tag": tag, "files": list(features.keys())}
        with open(cache_path / "manifest.json", "w") as f:
            json.dump(manifest, f)

        return str(cache_path)

    def load_cached_features(self, tag: str = "default") -> dict[str, pd.DataFrame] | None:
        """Load cached features if available."""
        cache_path = self.cache_dir / f"features_{tag}"
        manifest_path = cache_path / "manifest.json"

        if not manifest_path.exists():
            return None

        with open(manifest_path) as f:
            manifest = json.load(f)

        features = {}
        for name in manifest["files"]:
            parquet_path = cache_path / f"{name}.parquet"
            if parquet_path.exists():
                features[name] = pd.read_parquet(parquet_path)

        return features if features else None

    def compute_data_hash(self, movies_df: pd.DataFrame, ratings_df: pd.DataFrame) -> str:
        """Compute hash of input data for change detection."""
        movies_hash = hashlib.md5(pd.util.hash_pandas_object(movies_df).values.tobytes()).hexdigest()
        ratings_hash = hashlib.md5(pd.util.hash_pandas_object(ratings_df).values.tobytes()).hexdigest()
        return f"{movies_hash}_{ratings_hash}"
