from __future__ import annotations

import json
import logging
import os
import zipfile

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Movie, MovieFeature, MovieTag, Rating

logger = logging.getLogger(__name__)
settings = get_settings()


class MovieLensDataPipeline:
    """ETL pipeline for MovieLens 25M dataset.

    Downloads, processes, and loads data into the database.
    Handles both ratings and movie metadata with content features.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.raw_dir = settings.RAW_DATA_DIR
        self.processed_dir = settings.PROCESSED_DATA_DIR
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    async def run_full_pipeline(self, sample_size: int | None = None) -> dict:
        """Execute the complete data pipeline."""
        logger.info("Starting MovieLens data pipeline")

        movies_df, ratings_df, links_df, tags_df = self._download_and_load(sample_size)

        movies_df = self._process_movies(movies_df, links_df)
        ratings_df = self._process_ratings(ratings_df)

        await self._load_movies(movies_df)
        await self._load_ratings(ratings_df)
        if tags_df is not None and not tags_df.empty:
            await self._load_tags(tags_df)

        stats = {
            "movies_loaded": len(movies_df),
            "ratings_loaded": len(ratings_df),
            "tags_loaded": len(tags_df) if tags_df is not None else 0,
        }
        logger.info("Pipeline completed", extra=stats)
        return stats

    def _download_and_load(self, sample_size: int | None = None):
        """Download MovieLens 25M and load CSVs."""
        zip_path = self.raw_dir / "ml-25m.zip"
        extract_dir = self.raw_dir / "ml-25m"

        if not extract_dir.exists():
            logger.info("Downloading MovieLens 25M dataset")
            import urllib.request

            urllib.request.urlretrieve(settings.MOVIELENS_URL, zip_path)
            logger.info("Extracting dataset")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(self.raw_dir)
            os.remove(zip_path)

        movies_df = pd.read_csv(extract_dir / "movies.csv")

        if sample_size:
            logger.info(f"Sampling mode: loading {sample_size} ratings from CSV")
            ratings_df = pd.read_csv(extract_dir / "ratings.csv", nrows=sample_size)
            movie_ids_in_ratings = set(ratings_df["movieId"].unique())
        else:
            ratings_df = pd.read_csv(extract_dir / "ratings.csv")

        links_df = pd.read_csv(extract_dir / "links.csv")

        movie_ids_in_ratings = set(ratings_df["movieId"].unique())
        movies_df = movies_df[movies_df["movieId"].isin(movie_ids_in_ratings)]
        links_df = links_df[links_df["movieId"].isin(movie_ids_in_ratings)]

        tags_path = extract_dir / "tags.csv"
        if tags_path.exists():
            tags_df = pd.read_csv(tags_path, nrows=sample_size * 6 if sample_size else None)
            tags_df = tags_df[tags_df["movieId"].isin(movie_ids_in_ratings)]
        else:
            tags_df = None

        return movies_df, ratings_df, links_df, tags_df

    def _process_movies(
        self, movies_df: pd.DataFrame, links_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Clean and enrich movie metadata."""
        movies_df = movies_df.copy()
        movies_df = movies_df.rename(columns={"movieId": "id", "title": "title", "genres": "genres"})

        movies_df = movies_df.merge(
            links_df[["movieId", "imdbId", "tmdbId"]],
            left_on="id",
            right_on="movieId",
            how="left",
        )

        movies_df["year"] = movies_df["title"].str.extract(r"\((\d{4})\)", expand=False)
        movies_df["year"] = pd.to_numeric(movies_df["year"], errors="coerce").astype("Int64")
        movies_df["clean_title"] = movies_df["title"].str.replace(r"\s*\(\d{4}\)\s*$", "", regex=True)

        movies_df["vote_average"] = 0.0
        movies_df["vote_count"] = 0
        movies_df["popularity"] = 0.0
        movies_df["overview"] = ""
        movies_df["poster_url"] = None

        movies_df = movies_df.drop(columns=["movieId"], errors="ignore")

        logger.info(f"Processed {len(movies_df)} movies")
        return movies_df

    def _process_ratings(self, ratings_df: pd.DataFrame) -> pd.DataFrame:
        """Process and validate ratings."""
        ratings_df = ratings_df.copy()
        ratings_df["timestamp"] = pd.to_datetime(ratings_df["timestamp"], unit="s")
        ratings_df = ratings_df.rename(columns={"userId": "user_id", "movieId": "movie_id"})

        ratings_df = ratings_df[(ratings_df["rating"] >= 0.5) & (ratings_df["rating"] <= 5.0)]

        logger.info(f"Processed {len(ratings_df)} ratings")
        return ratings_df

    async def _load_movies(self, movies_df: pd.DataFrame) -> None:
        """Bulk insert movies into database."""
        batch_size = 1000
        total = len(movies_df)

        for start in range(0, total, batch_size):
            batch = movies_df.iloc[start : start + batch_size]
            objects = []
            for _, row in batch.iterrows():
                obj = Movie(
                    id=int(row["id"]),
                    title=row["title"],
                    genres=row.get("genres", ""),
                    year=int(row["year"]) if pd.notna(row.get("year")) else None,
                    overview=row.get("overview", ""),
                    poster_url=row.get("poster_url"),
                    vote_average=float(row.get("vote_average", 0)),
                    vote_count=int(row.get("vote_count", 0)),
                    popularity=float(row.get("popularity", 0)),
                )
                objects.append(obj)

            self.db.add_all(objects)
            await self.db.flush()
            logger.info(f"Loaded movies {start + 1}-{start + len(batch)} / {total}")

    async def _load_ratings(self, ratings_df: pd.DataFrame) -> None:
        """Bulk insert ratings into database."""
        batch_size = 5000
        total = len(ratings_df)

        for start in range(0, total, batch_size):
            batch = ratings_df.iloc[start : start + batch_size]
            objects = []
            for _, row in batch.iterrows():
                obj = Rating(
                    user_id=str(int(row["user_id"])),
                    movie_id=int(row["movie_id"]),
                    rating=float(row["rating"]),
                    timestamp=row["timestamp"],
                )
                objects.append(obj)

            self.db.add_all(objects)
            await self.db.flush()
            logger.info(f"Loaded ratings {start + 1}-{start + len(batch)} / {total}")

    async def _load_tags(self, tags_df: pd.DataFrame) -> None:
        """Bulk insert tags into database."""
        batch_size = 5000
        total = len(tags_df)

        for start in range(0, total, batch_size):
            batch = tags_df.iloc[start : start + batch_size]
            objects = []
            for _, row in batch.iterrows():
                obj = MovieTag(
                    movie_id=int(row["movieId"]),
                    tag=str(row["tag"]),
                    relevance=float(row.get("relevance", 1.0)),
                )
                objects.append(obj)

            self.db.add_all(objects)
            await self.db.flush()
            logger.info(f"Loaded tags {start + 1}-{start + len(batch)} / {total}")


class FeatureEngineer:
    """Generate content features for movies.

    Creates TF-IDF vectors, genre one-hot encodings, and combined
    content embeddings for the content-based recommendation model.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_content_features(self) -> pd.DataFrame:
        """Build feature matrix for all movies."""
        result = await self.db.execute(select(Movie))
        movies = result.scalars().all()

        records = []
        for movie in movies:
            records.append(
                {
                    "movie_id": movie.id,
                    "title": movie.title,
                    "genres": movie.genres or "",
                    "overview": movie.overview or "",
                    "year": movie.year or 0,
                }
            )

        df = pd.DataFrame(records)

        from sklearn.feature_extraction.text import TfidfVectorizer

        genre_list = [g.split("|") for g in df["genres"].fillna("")]
        all_genres = sorted(set(g for genres in genre_list for g in genres if g))
        genre_matrix = np.zeros((len(df), len(all_genres)))
        for i, genres in enumerate(genre_list):
            for g in genres:
                if g in all_genres:
                    genre_matrix[i, all_genres.index(g)] = 1.0

        text_data = df["title"].fillna("") + " " + df["genres"].fillna("").str.replace("|", " ")
        tfidf = TfidfVectorizer(max_features=500, stop_words="english")
        tfidf_matrix = tfidf.fit_transform(text_data).toarray()

        combined = np.hstack([genre_matrix, tfidf_matrix])

        for i, movie_id in enumerate(df["movie_id"]):
            feature = MovieFeature(
                movie_id=int(movie_id),
                genre_vector=json.dumps(genre_matrix[i].tolist()),
                content_embedding=json.dumps(combined[i].tolist()),
            )
            self.db.add(feature)

        await self.db.flush()
        logger.info(f"Built content features for {len(df)} movies")
        return df
