"""Content-based item embeddings.

Builds dense item embeddings by applying TruncatedSVD to a TF-IDF matrix
of movie text (title, genres, overview), enabling similarity search and
vector retrieval in a low-dimensional latent space.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

logger = logging.getLogger(__name__)


class ContentEmbeddings:
    """TF-IDF + TruncatedSVD content embeddings for items."""

    def __init__(self, n_components: int = 128, max_features: int = 20000):
        self.n_components = n_components
        self.max_features = max_features
        self.vectorizer: TfidfVectorizer | None = None
        self.svd: TruncatedSVD | None = None
        self.embeddings: np.ndarray | None = None
        self.item_ids: list[str] = []
        self.item_index: dict[str, int] = {}
        self.explained_variance: float = 0.0
        self.is_trained = False

    def build(self, movies_df: pd.DataFrame) -> dict:
        """Build embeddings from a movies dataframe.

        Args:
            movies_df: DataFrame with title, genres, and overview columns
                (plus an item identifier column such as movie_id/item_id).

        Returns:
            Build statistics.
        """
        if movies_df is None or movies_df.empty:
            raise ValueError("movies_df must be a non-empty DataFrame")

        id_col = next(
            (c for c in ("movie_id", "item_id", "id") if c in movies_df.columns),
            None,
        )
        genres = (
            movies_df["genres"].fillna("").str.replace(r"[|,\s]+", " ", regex=True)
            if "genres" in movies_df.columns else ""
        )
        overview = (
            movies_df["overview"].fillna("")
            if "overview" in movies_df.columns else ""
        )
        texts = (
            movies_df["title"].fillna("") + " " + genres + " " + overview
        ).astype(str)

        if id_col is not None:
            self.item_ids = movies_df[id_col].astype(str).tolist()
        else:
            self.item_ids = [str(i) for i in range(len(movies_df))]
        self.item_index = {item_id: i for i, item_id in enumerate(self.item_ids)}

        self.vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,
        )
        tfidf_matrix = self.vectorizer.fit_transform(texts)

        n_components = min(
            self.n_components,
            tfidf_matrix.shape[1] - 1,
            tfidf_matrix.shape[0] - 1,
        )
        if n_components >= 2:
            self.svd = TruncatedSVD(n_components=n_components, random_state=42)
            embeddings = self.svd.fit_transform(tfidf_matrix)
            self.explained_variance = float(self.svd.explained_variance_ratio_.sum())
        else:
            logger.warning("Corpus too small for SVD; using raw TF-IDF vectors")
            self.svd = None
            embeddings = tfidf_matrix.toarray()
            self.explained_variance = 1.0

        self.embeddings = normalize(np.asarray(embeddings, dtype=np.float64), norm="l2")
        self.is_trained = True
        logger.info(
            "ContentEmbeddings built: %d items, %d dims, explained variance %.4f",
            len(self.item_ids),
            self.embeddings.shape[1],
            self.explained_variance,
        )
        return {
            "n_items": len(self.item_ids),
            "n_dimensions": int(self.embeddings.shape[1]),
            "explained_variance": self.explained_variance,
        }

    def similar_items(self, item_id, top_k: int = 10) -> list[tuple[str, float]]:
        """Return the most cosine-similar items to the given item."""
        if not self.is_trained or self.embeddings is None:
            return []

        idx = self.item_index.get(str(item_id))
        if idx is None:
            return []

        sims = self.embeddings @ self.embeddings[idx]
        sims[idx] = -np.inf

        top_k = min(max(int(top_k), 1), len(sims) - 1)
        top_indices = np.argpartition(sims, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(sims[top_indices])[::-1]]
        return [
            (self.item_ids[int(i)], float(sims[i]))
            for i in top_indices
            if np.isfinite(sims[i])
        ]

    def get_embedding(self, item_id) -> np.ndarray | None:
        """Return the embedding vector for an item, or None if unavailable."""
        if not self.is_trained or self.embeddings is None:
            return None
        idx = self.item_index.get(str(item_id))
        if idx is None:
            return None
        return self.embeddings[idx]
