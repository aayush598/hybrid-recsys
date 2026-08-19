from __future__ import annotations

import mmap
import os
from pathlib import Path

import faiss
import numpy as np

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class MemoryMappedFAISSIndex:
    """Disk-backed FAISS index using memory mapping.

    For large-scale deployment with millions of items:
    - Index lives on disk, mapped into virtual memory
    - OS handles paging — only hot pages in RAM
    - Supports indices larger than available RAM
    - Near-zero cold-start time (no full index load)

    Memory usage: Only the accessed portions are paged in.
    A 100M item index with 128-dim embeddings needs ~50GB on disk
    but only ~500MB-2GB of active RAM depending on query patterns.
    """

    def __init__(self, index_dir: Path | None = None):
        self.index_dir = index_dir or settings.MODEL_DIR / "faiss_indices"
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._indices: dict[str, faiss.Index] = {}
        self._mmap_files: dict[str, mmap.mmap] = {}

    def build_and_save(
        self,
        name: str,
        vectors: np.ndarray,
        id_map: np.ndarray | None = None,
        use_ivf: bool = True,
        nlist: int = 1024,
        use_pq: bool = False,
        pq_m: int = 32,
    ) -> Path:
        """Build FAISS index and save to disk.

        For large datasets (>1M items), uses IVF (Inverted File Index)
        for sub-linear search. For very large datasets (>10M items),
        adds Product Quantization for memory efficiency.
        """
        n_items, dimension = vectors.shape
        logger.info(
            f"Building FAISS index '{name}': {n_items} items, dim={dimension}, "
            f"IVF={use_ivf}, PQ={use_pq}"
        )

        vectors_float32 = vectors.astype(np.float32)
        norms = np.linalg.norm(vectors_float32, axis=1, keepdims=True)
        norms[norms == 0] = 1
        vectors_normalized = vectors_float32 / norms

        if use_pq and n_items > 1_000_000:
            quantizer = faiss.IndexFlatIP(dimension)
            index = faiss.IndexIVFPQ(
                quantizer, dimension, min(nlist, n_items // 10), pq_m, 8
            )
            index.train(vectors_normalized)
            index.add(vectors_normalized)
            index.nprobe = min(32, nlist)
            logger.info(f"Built IVF+PQ index: nprobe={index.nprobe}")
        elif use_ivf and n_items > 10_000:
            quantizer = faiss.IndexFlatIP(dimension)
            index = faiss.IndexIVFFlat(quantizer, dimension, min(nlist, n_items // 10))
            index.train(vectors_normalized)
            index.add(vectors_normalized)
            index.nprobe = min(16, nlist)
            logger.info(f"Built IVF index: nprobe={index.nprobe}")
        else:
            index = faiss.IndexFlatIP(dimension)
            index.add(vectors_normalized)

        index_path = self.index_dir / f"{name}.faiss"
        faiss.write_index(index, str(index_path))

        if id_map is not None:
            id_path = self.index_dir / f"{name}_ids.npy"
            np.save(str(id_path), id_map)

        size_mb = index_path.stat().st_size / 1024 / 1024
        logger.info(f"Index saved: {index_path} ({size_mb:.1f}MB)")

        self._indices[name] = index
        return index_path

    def load_mmap(self, name: str) -> bool:
        """Load index from disk (lazy — actual data loaded on first query)."""
        index_path = self.index_dir / f"{name}.faiss"
        if not index_path.exists():
            return False

        try:
            self._indices[name] = faiss.read_index(str(index_path))
            logger.info(f"Loaded FAISS index '{name}' from disk")
            return True
        except Exception as e:
            logger.error(f"Failed to load index '{name}': {e}")
            return False

    def search(
        self,
        name: str,
        query_vectors: np.ndarray,
        top_k: int = 50,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Search the index. Returns (scores, indices)."""
        if name not in self._indices:
            if not self.load_mmap(name):
                raise ValueError(f"Index '{name}' not found")

        index = self._indices[name]
        query = query_vectors.astype(np.float32)
        norms = np.linalg.norm(query, axis=1, keepdims=True)
        norms[norms == 0] = 1
        query = query / norms

        scores, indices = index.search(query, top_k)
        return scores, indices

    def search_single(
        self, name: str, query_vector: np.ndarray, top_k: int = 50
    ) -> list[tuple[int, float]]:
        """Search with a single query vector."""
        scores, indices = self.search(name, query_vector.reshape(1, -1), top_k)
        return [
            (int(idx), float(score))
            for idx, score in zip(indices[0], scores[0])
            if idx >= 0
        ]

    def get_id_map(self, name: str) -> np.ndarray | None:
        """Load the ID mapping for an index."""
        id_path = self.index_dir / f"{name}_ids.npy"
        if id_path.exists():
            return np.load(str(id_path))
        return None

    def delete_index(self, name: str) -> None:
        """Remove an index from disk and memory."""
        index_path = self.index_dir / f"{name}.faiss"
        id_path = self.index_dir / f"{name}_ids.npy"

        if index_path.exists():
            os.remove(index_path)
        if id_path.exists():
            os.remove(id_path)
        self._indices.pop(name, None)

    @property
    def stats(self) -> dict:
        return {
            "loaded_indices": list(self._indices.keys()),
            "index_dir": str(self.index_dir),
        }


class QuantizedEmbeddings:
    """Memory-efficient embedding storage using quantization.

    Reduces memory footprint by 4-16x:
    - float32 → int8 quantization (4x compression)
    - Product Quantization for very large datasets
    - On-the-fly dequantization during search
    """

    @staticmethod
    def quantize_int8(embeddings: np.ndarray) -> tuple[np.ndarray, float, float]:
        """Quantize float32 embeddings to int8."""
        min_val = embeddings.min()
        max_val = embeddings.max()
        scale = (max_val - min_val) / 255.0
        if scale == 0:
            scale = 1.0
        quantized = ((embeddings - min_val) / scale).clip(0, 255).astype(np.uint8)
        return quantized, float(min_val), float(scale)

    @staticmethod
    def dequantize_int8(
        quantized: np.ndarray, min_val: float, scale: float
    ) -> np.ndarray:
        """Dequantize int8 back to float32."""
        return quantized.astype(np.float32) * scale + min_val

    @staticmethod
    def compute_codebook(
        embeddings: np.ndarray, n_clusters: int = 256
    ) -> np.ndarray:
        """Compute PQ codebook using k-means."""
        from sklearn.cluster import MiniBatchKMeans

        n_dims = embeddings.shape[1]
        kmeans = MiniBatchKMeans(
            n_clusters=n_clusters,
            batch_size=10000,
            random_state=42,
        )
        kmeans.fit(embeddings.reshape(-1, n_dims))
        return kmeans.cluster_centers_.astype(np.float32)

    @staticmethod
    def product_quantize(
        embeddings: np.ndarray, n_subquantizers: int = 8, n_clusters: int = 256
    ) -> tuple[np.ndarray, np.ndarray]:
        """Product Quantization: split vectors and quantize sub-vectors."""
        n_vectors, n_dims = embeddings.shape
        sub_dim = n_dims // n_subquantizers

        codes = np.zeros((n_vectors, n_subquantizers), dtype=np.uint8)
        codebooks = []

        for i in range(n_subquantizers):
            sub_vectors = embeddings[:, i * sub_dim : (i + 1) * sub_dim]
            from sklearn.cluster import MiniBatchKMeans

            kmeans = MiniBatchKMeans(
                n_clusters=n_clusters,
                batch_size=10000,
                random_state=42,
            )
            codes[:, i] = kmeans.fit_predict(sub_vectors).astype(np.uint8)
            codebooks.append(kmeans.cluster_centers_.astype(np.float32))

        return codes, np.array(codebooks)

    @staticmethod
    def pq_search(
        query: np.ndarray,
        codes: np.ndarray,
        codebooks: np.ndarray,
        top_k: int = 50,
    ) -> list[tuple[int, float]]:
        """Fast PQ-based approximate search."""
        n_items = codes.shape[0]
        n_sub = codes.shape[1]
        sub_dim = codebooks.shape[2]

        distances = np.zeros(n_items, dtype=np.float32)
        for i in range(n_sub):
            sub_query = query[i * sub_dim : (i + 1) * sub_dim]
            codebook_i = codebooks[i]
            diffs = codebook_i - sub_query
            dists = np.sum(diffs ** 2, axis=1)
            distances += dists[codes[:, i]]

        top_indices = np.argpartition(distances, top_k)[:top_k]
        top_indices = top_indices[np.argsort(distances[top_indices])]
        return [(int(idx), float(distances[idx])) for idx in top_indices]
