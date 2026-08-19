from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from scipy.sparse import csr_matrix

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class ChunkedDataReader:
    """Memory-efficient chunked data reader.

    Processes large datasets in configurable chunks without loading
    everything into memory. Critical for handling 25M+ ratings.

    Memory usage: O(chunk_size) instead of O(total_records)
    """

    def __init__(self, chunk_size: int = 100_000):
        self.chunk_size = chunk_size

    def read_csv_chunked(
        self,
        filepath: str | Path,
        columns: list[str] | None = None,
        dtype: dict | None = None,
    ) -> Iterator[pd.DataFrame]:
        """Read CSV in chunks without loading full file."""
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        logger.info(
            "Reading CSV in chunks",
            file=str(filepath),
            chunk_size=self.chunk_size,
        )

        for chunk in pd.read_csv(
            filepath,
            usecols=columns,
            dtype=dtype,
            chunksize=self.chunk_size,
            engine="c",
            low_memory=True,
        ):
            yield chunk

    def read_parquet_chunked(
        self,
        filepath: str | Path,
        columns: list[str] | None = None,
        batch_size: int = 100_000,
    ) -> Iterator[pd.DataFrame]:
        """Read Parquet file in batches using pyarrow."""
        import pyarrow.parquet as pq

        filepath = Path(filepath)
        parquet_file = pq.ParquetFile(filepath)

        for batch in parquet_file.iter_batches(batch_size=batch_size, columns=columns):
            yield batch.to_pandas()

    def stream_csv_rows(
        self,
        filepath: str | Path,
        columns: list[str] | None = None,
    ) -> Iterator[dict]:
        """Stream individual rows from CSV (lowest memory usage)."""
        for chunk in self.read_csv_chunked(filepath, columns):
            for _, row in chunk.iterrows():
                yield row.to_dict()

    def count_rows_fast(self, filepath: str | Path) -> int:
        """Fast row count without loading data."""
        filepath = Path(filepath)
        if filepath.suffix == ".parquet":
            import pyarrow.parquet as pq
            return pq.read_metadata(filepath).num_rows
        else:
            with open(filepath) as f:
                return sum(1 for _ in f) - 1


class ParquetWriter:
    """Efficient Parquet writer for columnar storage.

    Parquet provides:
    - 3-10x compression vs CSV
    - Column pruning (read only needed columns)
    - Predicate pushdown (filter at storage level)
    - Memory-mapped reads
    """

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or settings.PROCESSED_DATA_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_ratings_parquet(
        self,
        reader: ChunkedDataReader,
        input_csv: Path,
        output_path: Path | None = None,
    ) -> Path:
        """Convert ratings CSV to optimized Parquet."""
        if output_path is None:
            output_path = self.output_dir / "ratings.parquet"

        logger.info(f"Converting {input_csv} to Parquet")

        chunks = []
        for chunk in reader.read_csv_chunked(
            input_csv,
            columns=["userId", "movieId", "rating", "timestamp"],
            dtype={"userId": "int32", "movieId": "int32", "rating": "float32"},
        ):
            chunks.append(chunk)

        if chunks:
            df = pd.concat(chunks, ignore_index=True)
            df.to_parquet(
                output_path,
                engine="pyarrow",
                compression="snappy",
                index=False,
            )
            logger.info(
                f"Written Parquet: {output_path}",
                rows=len(df),
                size_mb=round(output_path.stat().st_size / 1024 / 1024, 2),
            )

        return output_path

    def write_movies_parquet(
        self,
        reader: ChunkedDataReader,
        input_csv: Path,
        output_path: Path | None = None,
    ) -> Path:
        """Convert movies CSV to optimized Parquet."""
        if output_path is None:
            output_path = self.output_dir / "movies.parquet"

        chunks = []
        for chunk in reader.read_csv_chunked(
            input_csv,
            columns=["movieId", "title", "genres"],
        ):
            chunks.append(chunk)

        if chunks:
            df = pd.concat(chunks, ignore_index=True)
            df.to_parquet(output_path, engine="pyarrow", compression="snappy", index=False)

        return output_path

    def write_interactions_parquet(
        self,
        interactions: list[dict],
        output_path: Path | None = None,
    ) -> Path:
        """Write user interactions to Parquet."""
        if output_path is None:
            output_path = self.output_dir / "interactions.parquet"

        df = pd.DataFrame(interactions)
        if not df.empty:
            df.to_parquet(output_path, engine="pyarrow", compression="snappy", index=False)

        return output_path


class ChunkedInteractionMatrix:
    """Build sparse interaction matrix without full materialization.

    For 162K users x 62K items, a dense matrix would need ~80GB RAM.
    This builds a sparse matrix incrementally in chunks.
    """

    def __init__(self, chunk_size: int = 100_000):
        self.chunk_size = chunk_size
        self.user_map: dict[str, int] = {}
        self.item_map: dict[int, int] = {}
        self.reverse_item_map: dict[int, int] = {}
        self._user_counts: dict[str, int] = {}
        self._item_counts: dict[int, int] = {}

    def build_from_parquet(
        self, parquet_path: Path
    ) -> csr_matrix:
        """Build sparse CSR matrix from Parquet in chunks."""
        import pyarrow.parquet as pq
        from scipy.sparse import csr_matrix

        logger.info(f"Building sparse interaction matrix from {parquet_path}")

        parquet_file = pq.ParquetFile(parquet_path)
        rows = []
        for batch in parquet_file.iter_batches(batch_size=self.chunk_size):
            df = batch.to_pandas()
            for _, row in df.iterrows():
                user_id = str(int(row["userId"]))
                item_id = int(row["movieId"])
                rating = float(row["rating"])

                if user_id not in self.user_map:
                    self.user_map[user_id] = len(self.user_map)
                if item_id not in self.item_map:
                    self.item_map[item_id] = len(self.item_map)
                    self.reverse_item_map[self.item_map[item_id]] = item_id

                self._user_counts[user_id] = self._user_counts.get(user_id, 0) + 1
                self._item_counts[item_id] = self._item_counts.get(item_id, 0) + 1

                rows.append((
                    self.user_map[user_id],
                    self.item_map[item_id],
                    rating,
                ))

        n_users = len(self.user_map)
        n_items = len(self.item_map)

        logger.info(f"Matrix dimensions: {n_users} users x {n_items} items")

        row_indices = np.array([r[0] for r in rows], dtype=np.int32)
        col_indices = np.array([r[1] for r in rows], dtype=np.int32)
        values = np.array([r[2] for r in rows], dtype=np.float32)

        matrix = csr_matrix((values, (row_indices, col_indices)), shape=(n_users, n_items))

        density = matrix.nnz / (n_users * n_items) * 100
        logger.info(
            f"Sparse matrix built: nnz={matrix.nnz}, density={density:.4f}%, "
            f"memory={matrix.data.nbytes / 1024 / 1024:.1f}MB"
        )

        return matrix

    def get_popular_items(self, min_count: int = 5) -> list[int]:
        """Get items with enough interactions for reliable recommendations."""
        return [
            item_id for item_id, count in self._item_counts.items()
            if count >= min_count
        ]

    def get_active_users(self, min_count: int = 10) -> list[str]:
        """Get users with enough interactions for personalization."""
        return [
            user_id for user_id, count in self.user_map.items()
            if self._user_counts.get(user_id, 0) >= min_count
        ]
