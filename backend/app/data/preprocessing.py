from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd
from scipy import sparse

from app.core.logging import get_logger

logger = get_logger(__name__)

HTML_TAG_RE = re.compile(r"<[^>]+>")
NON_ALPHANUMERIC_RE = re.compile(r"[^a-z0-9\s]")

STOPWORDS = frozenset(
    """
    a about above after again against all am an and any are aren't as at be
    because been before being below between both but by can't cannot could
    couldn't did didn't do does doesn't doing don't down during each few for
    from further had hadn't has hasn't have haven't having he he'd he'll he's
    her here here's hers herself him himself his how how's i i'd i'll i'm
    i've if in into is isn't it it's its itself let's me more most mustn't my
    myself no nor not of off on once only or other ought our ours ourselves
    out over own same shan't she she'd she'll she's should shouldn't so some
    such than that that's the their theirs them themselves then there there's
    these they they'd they'll they're they've this those through to too under
    until up very was wasn't we we'd we'll we're we've were weren't what
    what's when when's where where's which while who who's whom why why's
    with won't would wouldn't you you'd you'll you're you've your yours
    yourself yourselves
    """.split()
)

STEM_SUFFIXES = (
    ("ational", "ate"),
    ("tional", "tion"),
    ("iveness", "ive"),
    ("fulness", "ful"),
    ("ousness", "ous"),
    ("ization", "ize"),
    ("ations", "ate"),
    ("tions", "tion"),
    ("ments", "ment"),
    ("ingly", ""),
    ("edly", ""),
    ("ing", ""),
    ("ies", "y"),
    ("ied", "y"),
    ("ally", "al"),
    ("ness", ""),
    ("ment", ""),
    ("able", ""),
    ("ible", ""),
    ("ance", ""),
    ("ence", ""),
    ("ed", ""),
    ("ly", ""),
    ("es", ""),
    ("s", ""),
)


class DataPreprocessor:
    """Reusable data cleaning utilities for recommendation pipelines.

    Covers numeric imputation, outlier detection, feature scaling and a
    dependency-light text pipeline (HTML stripping, stopword removal,
    suffix stemming) with a from-scratch TF-IDF vectorizer built on
    scipy.sparse.
    """

    def handle_missing_values(
        self,
        df: pd.DataFrame,
        strategy: str = "mean",
        columns: list[str] | None = None,
    ) -> pd.DataFrame:
        """Fill or drop missing values.

        Numeric columns support mean/median; object/categorical columns use
        mode. ``strategy="drop"`` removes rows containing any NaN.
        """
        if strategy not in {"mean", "median", "mode", "drop"}:
            raise ValueError(f"Unknown missing-value strategy: {strategy}")

        df = df.copy()
        if strategy == "drop":
            return df.dropna().reset_index(drop=True)

        targets = columns if columns is not None else df.columns.tolist()
        fill_report: dict[str, int] = {}
        for col in targets:
            if col not in df.columns or not df[col].isna().any():
                continue
            n_missing = int(df[col].isna().sum())
            if pd.api.types.is_numeric_dtype(df[col]):
                if strategy == "mode":
                    fill_value = df[col].mode(dropna=True)
                    fill_value = fill_value.iloc[0] if not fill_value.empty else 0
                elif strategy == "median":
                    fill_value = float(df[col].median())
                else:
                    fill_value = float(df[col].mean())
            else:
                mode_vals = df[col].mode(dropna=True)
                fill_value = mode_vals.iloc[0] if not mode_vals.empty else "unknown"
            df[col] = df[col].fillna(fill_value)
            fill_report[col] = n_missing

        if fill_report:
            logger.info(f"Imputed missing values ({strategy}): {fill_report}")
        return df

    def detect_outliers(
        self,
        df: pd.DataFrame,
        columns: list[str],
        method: str = "iqr",
        z_threshold: float = 3.0,
        iqr_factor: float = 1.5,
    ) -> pd.Series:
        """Return a boolean mask marking outlier rows (True = outlier)."""
        if method not in {"iqr", "zscore"}:
            raise ValueError(f"Unknown outlier detection method: {method}")

        mask = pd.Series(False, index=df.index)
        for col in columns:
            if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
                continue
            values = df[col].astype(float)
            valid = values.notna()
            if method == "iqr":
                q1, q3 = values.quantile(0.25), values.quantile(0.75)
                iqr = q3 - q1
                lower, upper = q1 - iqr_factor * iqr, q3 + iqr_factor * iqr
                col_mask = (values < lower) | (values > upper)
            else:
                std = values.std()
                if std == 0 or np.isnan(std):
                    continue
                col_mask = ((values - values.mean()).abs() / std) > z_threshold
            mask |= col_mask.fillna(False) & valid

        logger.debug(f"Outlier detection ({method}): {int(mask.sum())} rows flagged")
        return mask

    def scale_features(
        self,
        df: pd.DataFrame,
        columns: list[str],
        method: str = "standard",
    ) -> pd.DataFrame:
        """Scale numeric columns in place on a copy of the dataframe.

        - standard: zero mean, unit variance
        - minmax:   rescale to [0, 1]
        - robust:   center on median, scale by IQR
        """
        if method not in {"standard", "minmax", "robust"}:
            raise ValueError(f"Unknown scaling method: {method}")

        df = df.copy()
        stats_log: dict[str, dict[str, Any]] = {}
        for col in columns:
            if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
                continue
            values = df[col].astype(float)
            if method == "standard":
                std = values.std()
                center, scale = values.mean(), (std if std > 0 else 1.0)
                scaled = (values - center) / scale
            elif method == "minmax":
                vmin, vmax = values.min(), values.max()
                scale = (vmax - vmin) if vmax > vmin else 1.0
                scaled = (values - vmin) / scale
            else:
                q1, q3 = values.quantile(0.25), values.quantile(0.75)
                iqr = q3 - q1
                center, scale = values.median(), (iqr if iqr > 0 else 1.0)
                scaled = (values - center) / scale
            df[col] = scaled
            stats_log[col] = {"method": method, "center": center, "scale": scale}

        logger.debug(f"Scaled {len(stats_log)} columns using {method}")
        return df

    @staticmethod
    def text_preprocess(text: str) -> str:
        """Clean raw text: strip HTML, lowercase, remove stopwords, stem."""
        if not isinstance(text, str):
            return ""
        text = HTML_TAG_RE.sub(" ", text.lower())
        tokens = NON_ALPHANUMERIC_RE.sub(" ", text).split()
        cleaned = []
        for token in tokens:
            if token in STOPWORDS or token.isdigit() or len(token) < 2:
                continue
            cleaned.append(DataPreprocessor._stem(token))
        return " ".join(cleaned)

    @staticmethod
    def _stem(token: str) -> str:
        """Very light suffix-stripping stemmer (no external deps)."""
        for suffix, replacement in STEM_SUFFIXES:
            if token.endswith(suffix) and len(token) - len(suffix) >= 3:
                return token[: len(token) - len(suffix)] + replacement
        return token

    def build_tfidf_matrix(
        self,
        texts: list[str],
        max_features: int = 10000,
    ) -> sparse.csr_matrix:
        """Build an L2-normalized TF-IDF matrix from raw texts.

        Vocabulary is capped at ``max_features`` terms ranked by document
        frequency. Returns a scipy.sparse CSR matrix of shape
        ``(n_texts, vocab_size)``.
        """
        cleaned = [self.text_preprocess(t) for t in texts]
        tokenized = [c.split() for c in cleaned]

        doc_freq: dict[str, int] = {}
        for tokens in tokenized:
            for term in set(tokens):
                doc_freq[term] = doc_freq.get(term, 0) + 1

        if not doc_freq:
            return sparse.csr_matrix((len(texts), 0), dtype=np.float64)

        vocab_terms = sorted(
            sorted(doc_freq.items(), key=lambda kv: (-kv[1], kv[0]))[:max_features],
            key=lambda kv: kv[0],
        )
        vocab = {term: idx for idx, (term, _) in enumerate(vocab_terms)}
        idf = np.zeros(len(vocab), dtype=np.float64)
        n_docs = len(tokenized)
        for term, idx in vocab.items():
            idf[idx] = np.log((1.0 + n_docs) / (1.0 + doc_freq[term])) + 1.0

        rows, cols, vals = [], [], []
        for row_idx, tokens in enumerate(tokenized):
            counts: dict[int, int] = {}
            for token in tokens:
                col = vocab.get(token)
                if col is not None:
                    counts[col] = counts.get(col, 0) + 1
            doc_len = sum(counts.values())
            if doc_len == 0:
                continue
            for col, count in counts.items():
                rows.append(row_idx)
                cols.append(col)
                vals.append((count / doc_len) * idf[col])

        matrix = sparse.csr_matrix(
            (vals, (rows, cols)), shape=(n_docs, len(vocab)), dtype=np.float64
        )
        row_norms = np.sqrt(matrix.multiply(matrix).sum(axis=1)).A.ravel()
        nonzero_rows = row_norms > 0
        matrix[nonzero_rows] = sparse.diags(1.0 / row_norms[nonzero_rows]).dot(
            matrix[nonzero_rows]
        )
        logger.info(f"TF-IDF matrix built: {matrix.shape}, nnz={matrix.nnz}")
        return matrix
