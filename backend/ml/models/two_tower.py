from __future__ import annotations

import pickle

import faiss
import numpy as np
import torch
import torch.nn as nn

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class TwoTowerModel(nn.Module):
    """Two-Tower Neural Retrieval Model.

    Architecture (inspired by YouTube's recommendation system and
    Facebook's DLRM):

    - User Tower: processes user features → user embedding
    - Item Tower: processes item features → item embedding
    - Score: dot product of user and item embeddings

    Key advantages:
    - Scales to millions of items via pre-computed item embeddings + FAISS
    - User embedding computed in real-time (<10ms)
    - Separates user understanding from item understanding
    - Enables cross-domain transfer (pretrain item tower on metadata)
    """

    def __init__(
        self,
        num_users: int,
        num_items: int,
        user_feature_dim: int = 32,
        item_feature_dim: int = 64,
        embedding_dim: int = 128,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.embedding_dim = embedding_dim

        # User Tower
        self.user_tower = nn.Sequential(
            nn.Linear(user_feature_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, embedding_dim),
            nn.LayerNorm(embedding_dim),
        )

        # Item Tower
        self.item_tower = nn.Sequential(
            nn.Linear(item_feature_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, embedding_dim),
            nn.LayerNorm(embedding_dim),
        )

        # Item embedding table for fast lookup
        self.item_embedding = nn.Embedding(num_items, item_feature_dim)

        self._init_weights()

    def _init_weights(self) -> None:
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.kaiming_normal_(module.weight, nonlinearity="relu")
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.xavier_uniform_(module.weight)

    def forward_user(self, user_features: torch.Tensor) -> torch.Tensor:
        """Encode user features into embedding."""
        return self.user_tower(user_features)

    def forward_item(self, item_features: torch.Tensor) -> torch.Tensor:
        """Encode item features into embedding."""
        return self.item_tower(item_features)

    def forward(
        self,
        user_features: torch.Tensor,
        item_features: torch.Tensor,
    ) -> torch.Tensor:
        """Compute dot product score between user and item."""
        user_emb = self.forward_user(user_features)
        item_emb = self.forward_item(item_features)
        scores = torch.sum(user_emb * item_emb, dim=-1)
        return torch.sigmoid(scores)

    def get_item_embeddings(
        self, item_ids: torch.Tensor
    ) -> np.ndarray:
        """Pre-compute item embeddings for FAISS index."""
        self.eval()
        with torch.no_grad():
            item_features = self.item_embedding(item_ids)
            item_embs = self.item_tower(item_features)
            item_embs = torch.nn.functional.normalize(item_embs, p=2, dim=-1)
        return item_embs.cpu().numpy()

    def get_user_embedding(self, user_features: torch.Tensor) -> np.ndarray:
        """Get user embedding for real-time retrieval."""
        self.eval()
        with torch.no_grad():
            user_emb = self.forward_user(user_features)
            user_emb = torch.nn.functional.normalize(user_emb, p=2, dim=-1)
        return user_emb.cpu().numpy()


class TwoTowerIndex:
    """FAISS-based index for Two-Tower model retrieval.

    Pre-computes all item embeddings and builds FAISS index.
    At query time, computes user embedding and searches FAISS.
    """

    def __init__(self, embedding_dim: int = 128):
        self.embedding_dim = embedding_dim
        self.index: faiss.IndexFlatIP | None = None
        self.item_ids: list[int] = []
        self.model: TwoTowerModel | None = None

    def build_index(
        self,
        model: TwoTowerModel,
        all_item_ids: torch.Tensor,
    ) -> None:
        """Build FAISS index from all item embeddings."""
        self.model = model
        embeddings = model.get_item_embeddings(all_item_ids)

        n_items = embeddings.shape[0]
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.index.add(embeddings.astype(np.float32))
        self.item_ids = all_item_ids.numpy().tolist()

        logger.info(f"Built Two-Tower FAISS index: {n_items} items, dim={self.embedding_dim}")

    def search(
        self,
        user_features: torch.Tensor,
        top_k: int = 50,
    ) -> list[tuple[int, float]]:
        """Retrieve top-K items for a user."""
        if self.index is None or self.model is None:
            return []

        user_emb = self.model.get_user_embedding(user_features)
        scores, indices = self.index.search(user_emb.astype(np.float32), top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if 0 <= idx < len(self.item_ids):
                results.append((self.item_ids[idx], float(score)))
        return results

    def save(self) -> None:
        """Save index to disk."""
        if self.index is None:
            return
        path = settings.MODEL_DIR
        path.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(path / "two_tower_faiss.index"))
        with open(path / "two_tower_item_ids.pkl", "wb") as f:
            pickle.dump(self.item_ids, f)

    def load(self) -> bool:
        """Load index from disk."""
        path = settings.MODEL_DIR
        faiss_path = path / "two_tower_faiss.index"
        ids_path = path / "two_tower_item_ids.pkl"

        if not faiss_path.exists() or not ids_path.exists():
            return False

        try:
            self.index = faiss.read_index(str(faiss_path))
            with open(ids_path, "rb") as f:
                self.item_ids = pickle.load(f)
            logger.info("Two-Tower index loaded from disk")
            return True
        except Exception as e:
            logger.error(f"Failed to load Two-Tower index: {e}")
            return False
