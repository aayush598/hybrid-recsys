"""Okapi BM25 text scoring for content-based movie similarity.

Indexes movie text (title, genres, overview) and scores documents
against free-text queries using Okapi BM25 with k1=1.5, b=0.75.
"""

from __future__ import annotations

import logging
import re
from collections import Counter

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokenizer."""
    return _TOKEN_PATTERN.findall(str(text).lower())


class BM25Model:
    """Okapi BM25 ranking model over movie content text."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.item_ids: list[str] = []
        self.item_index: dict[str, int] = {}
        self.postings: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        self.doc_lengths: np.ndarray | None = None
        self.avg_doc_length: float = 0.0
        self.idf: dict[str, float] = {}
        self.doc_tokens: list[list[str]] = []
        self.n_docs: int = 0
        self.is_trained = False

    def build_index(self, movies_df: pd.DataFrame) -> dict:
        """Build the BM25 index from a movies dataframe.

        Args:
            movies_df: DataFrame with title, genres, and overview columns
                (plus an item identifier column such as movie_id/item_id).

        Returns:
            Index statistics.
        """
        if movies_df is None or movies_df.empty:
            raise ValueError("movies_df must be a non-empty DataFrame")

        id_col = next(
            (c for c in ("movie_id", "item_id", "id") if c in movies_df.columns),
            None,
        )
        genres = movies_df["genres"].fillna("") if "genres" in movies_df.columns else None
        if genres is not None:
            genres = genres.str.replace(r"[|,\s]+", " ", regex=True)

        texts = (
            movies_df["title"].fillna("") + " "
            + (genres if genres is not None else "") + " "
            + (movies_df["overview"].fillna("") if "overview" in movies_df.columns else "")
        )

        if id_col is not None:
            self.item_ids = movies_df[id_col].astype(str).tolist()
        else:
            self.item_ids = [str(i) for i in range(len(movies_df))]
        self.item_index = {item_id: i for i, item_id in enumerate(self.item_ids)}

        self.doc_tokens = [_tokenize(t) for t in texts]
        self.n_docs = len(self.doc_tokens)
        self.doc_lengths = np.array([len(toks) for toks in self.doc_tokens], dtype=np.float64)
        self.avg_doc_length = float(self.doc_lengths.mean()) if self.n_docs else 0.0

        term_doc_freq: dict[str, Counter] = {}
        for doc_idx, tokens in enumerate(self.doc_tokens):
            for term, tf in Counter(tokens).items():
                term_doc_freq.setdefault(term, Counter())[doc_idx] = tf

        self.idf = {}
        self.postings = {}
        for term, tf_by_doc in term_doc_freq.items():
            doc_indices = np.array(sorted(tf_by_doc), dtype=np.int64)
            tfs = np.array([tf_by_doc[d] for d in doc_indices], dtype=np.float64)
            self.postings[term] = (doc_indices, tfs)
            df = len(doc_indices)
            self.idf[term] = float(np.log((self.n_docs - df + 0.5) / (df + 0.5) + 1.0))

        self.is_trained = True
        logger.info(
            "BM25 index built: %d docs, %d unique terms, avgdl=%.1f",
            self.n_docs,
            len(self.postings),
            self.avg_doc_length,
        )
        return {
            "n_docs": self.n_docs,
            "n_terms": len(self.postings),
            "avg_doc_length": self.avg_doc_length,
        }

    def score(self, query_string: str, top_k: int = 20) -> list[tuple[str, float]]:
        """Score all indexed documents against a text query.

        Returns the top-K (item_id, bm25_score) pairs; untrained models
        return an empty list.
        """
        if not self.is_trained or self.doc_lengths is None:
            return []

        query_terms = _tokenize(query_string)
        if not query_terms:
            return []

        scores = self._score_terms(query_terms)
        return self._top_k_from_scores(scores, top_k)

    def similar_items(self, item_id, top_k: int = 10) -> list[tuple[str, float]]:
        """Find content-similar items by scoring the corpus with the item's own text."""
        if not self.is_trained:
            return []

        doc_idx = self.item_index.get(str(item_id))
        if doc_idx is None:
            return []

        scores = self._score_terms(self.doc_tokens[doc_idx])
        scores[doc_idx] = -np.inf
        return self._top_k_from_scores(scores, top_k)

    def _score_terms(self, terms: list[str]) -> np.ndarray:
        """Accumulate Okapi BM25 scores for each query/document term."""
        scores = np.zeros(self.n_docs, dtype=np.float64)
        denom_norm = self.k1 * (1.0 - self.b + self.b * self.doc_lengths / self.avg_doc_length)

        for term, term_weight in Counter(terms).items():
            posting = self.postings.get(term)
            if posting is None:
                continue
            doc_indices, tfs = posting
            tf_component = (tfs * (self.k1 + 1.0)) / (tfs + denom_norm[doc_indices])
            scores[doc_indices] += self.idf[term] * tf_component * term_weight
        return scores

    def _top_k_from_scores(self, scores: np.ndarray, top_k: int) -> list[tuple[str, float]]:
        """Return the highest-scoring documents as (item_id, score) pairs."""
        top_k = min(max(int(top_k), 1), self.n_docs)
        top_indices = np.argpartition(scores, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]
        return [
            (self.item_ids[int(i)], float(scores[i]))
            for i in top_indices
            if scores[i] > 0
        ]
