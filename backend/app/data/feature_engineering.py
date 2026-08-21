"""Feature engineering for user/item/interaction features."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd


class FeatureEngineer:
    """Compute user, item, interaction, and temporal features."""

    def compute_user_features(self, interactions_df: pd.DataFrame) -> pd.DataFrame:
        """Compute user-level features from interaction history."""
        if interactions_df.empty:
            return pd.DataFrame(columns=["user_id", "avg_rating", "num_ratings", "rating_std", "activity_level"])

        user_groups = interactions_df.groupby("user_id")

        features = pd.DataFrame()
        features["user_id"] = user_groups.groups.keys()
        features = features.set_index("user_id")

        agg = user_groups["rating"].agg(["mean", "count", "std"]).rename(
            columns={"mean": "avg_rating", "count": "num_ratings", "std": "rating_std"}
        )
        features = features.join(agg, how="left")
        features["rating_std"] = features["rating_std"].fillna(0.0)

        if "timestamp" in interactions_df.columns:
            now = datetime.now(timezone.utc)
            last = user_groups["timestamp"].max()
            last_dt = pd.to_datetime(last, utc=True)
            features["recency_days"] = (now - last_dt).dt.total_seconds() / 86400
            features["recency_days"] = features["recency_days"].fillna(features["recency_days"].max())
        else:
            features["recency_days"] = 0.0

        if "genres" in interactions_df.columns:
            def _top_genres(group):
                all_genres = [g.strip() for gs in group.dropna() for g in str(gs).split("|")]
                if not all_genres:
                    return ""
                counts = pd.Series(all_genres).value_counts()
                return "|".join(counts.head(3).index.tolist())

            features["favorite_genres"] = user_groups.get("genres", pd.Series()).apply(_top_genres) if "genres" in interactions_df.columns else ""
        else:
            features["favorite_genres"] = ""

        features["activity_level"] = pd.cut(
            features["num_ratings"],
            bins=[0, 5, 20, 100, float("inf")],
            labels=["new", "casual", "active", "power"],
            right=True,
        ).astype(str)

        features = features.reset_index()
        return features

    def compute_item_features(
        self, movies_df: pd.DataFrame, ratings_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Compute item-level features from movie metadata and ratings."""
        features = movies_df[["id", "title"]].copy() if "id" in movies_df.columns else pd.DataFrame()
        if features.empty:
            return features

        features = features.rename(columns={"id": "item_id"})

        if not ratings_df.empty:
            item_agg = ratings_df.groupby("movie_id")["rating"].agg(["mean", "count", "std"]).rename(
                columns={"mean": "avg_rating", "count": "num_ratings", "std": "rating_std"}
            )
            features = features.merge(item_agg, left_on="item_id", right_index=True, how="left")
            features["rating_std"] = features["rating_std"].fillna(0.0)

            max_count = features["num_ratings"].max()
            if max_count > 0:
                features["popularity_score"] = features["num_ratings"] / max_count
            else:
                features["popularity_score"] = 0.0
        else:
            features["avg_rating"] = 0.0
            features["num_ratings"] = 0
            features["rating_std"] = 0.0
            features["popularity_score"] = 0.0

        if "genres" in movies_df.columns:
            all_genres = set()
            for g in movies_df["genres"].dropna():
                all_genres.update(genre.strip() for genre in str(g).split("|"))
            all_genres = sorted(all_genres)
            genre_map = {g: i for i, g in enumerate(all_genres)}

            def _genre_vector(genres_str):
                vec = np.zeros(len(all_genres))
                for g in str(genres_str).split("|"):
                    g = g.strip()
                    if g in genre_map:
                        vec[genre_map[g]] = 1.0
                return vec

            genre_vectors = movies_df["genres"].apply(_genre_vector)
            genre_df = pd.DataFrame(
                genre_vectors.tolist(), columns=[f"genre_{g}" for g in all_genres], index=movies_df.index
            )
            features = pd.concat([features, genre_df], axis=1)

        return features

    def compute_interaction_features(
        self, user_id: str | int, interactions_df: pd.DataFrame
    ) -> dict:
        """Compute interaction-level features for a specific user."""
        user_interactions = interactions_df[interactions_df["user_id"] == user_id]

        if user_interactions.empty:
            return {"co_occurrence_count": 0, "session_length": 0, "avg_dwell_time": 0.0, "interaction_recency": 0.0}

        result = {
            "co_occurrence_count": len(user_interactions),
            "session_length": len(user_interactions),
            "avg_dwell_time": float(user_interactions.get("dwell_time", pd.Series([0.0])).mean()),
            "interaction_recency": 0.0,
        }

        if "timestamp" in user_interactions.columns:
            now = datetime.now(timezone.utc)
            last_ts = pd.to_datetime(user_interactions["timestamp"].max(), utc=True)
            result["interaction_recency"] = (now - last_ts).total_seconds() / 3600

        return result

    def compute_temporal_features(self, timestamps: pd.Series) -> pd.DataFrame:
        """Extract temporal features from timestamps."""
        dt = pd.to_datetime(timestamps, utc=True)

        features = pd.DataFrame()
        features["hour_of_day"] = dt.dt.hour
        features["day_of_week"] = dt.dt.dayofweek
        features["is_weekend"] = (dt.dt.dayofweek >= 5).astype(int)
        features["month"] = dt.dt.month
        features["season"] = dt.dt.month.map(
            {12: "winter", 1: "winter", 2: "winter",
             3: "spring", 4: "spring", 5: "spring",
             6: "summer", 7: "summer", 8: "summer",
             9: "fall", 10: "fall", 11: "fall"}
        )
        return features
