from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class InteractionDataset(Dataset):
    """Dataset for user-item interactions."""

    def __init__(self, user_ids: np.ndarray, item_ids: np.ndarray, ratings: np.ndarray):
        self.user_ids = torch.LongTensor(user_ids)
        self.item_ids = torch.LongTensor(item_ids)
        self.ratings = torch.FloatTensor(ratings)

    def __len__(self) -> int:
        return len(self.ratings)

    def __getitem__(self, idx: int):
        return self.user_ids[idx], self.item_ids[idx], self.ratings[idx]


class NeuralCollaborativeFiltering(nn.Module):
    """Neural Collaborative Filtering combining GMF and MLP.

    Architecture (inspired by He et al., 2017):
    - GMF path: element-wise product of user/item embeddings
    - MLP path: concatenated embeddings through deep layers
    - NeuMLP: combines GMF and MLP outputs

    Achieves better performance than traditional matrix factorization
    by learning non-linear user-item interactions.
    """

    def __init__(
        self,
        num_users: int,
        num_items: int,
        embedding_dim: int = 64,
        mlp_dims: list[int] | None = None,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.num_users = num_users
        self.num_items = num_items
        self.embedding_dim = embedding_dim

        if mlp_dims is None:
            mlp_dims = [128, 64, 32]

        # GMF embeddings
        self.gmf_user_embedding = nn.Embedding(num_users, embedding_dim)
        self.gmf_item_embedding = nn.Embedding(num_items, embedding_dim)

        # MLP embeddings
        self.mlp_user_embedding = nn.Embedding(num_users, embedding_dim)
        self.mlp_item_embedding = nn.Embedding(num_items, embedding_dim)

        # MLP layers
        mlp_layers = []
        input_dim = embedding_dim * 2
        for dim in mlp_dims:
            mlp_layers.extend([
                nn.Linear(input_dim, dim),
                nn.BatchNorm1d(dim),
                nn.ReLU(),
                nn.Dropout(dropout),
            ])
            input_dim = dim
        self.mlp = nn.Sequential(*mlp_layers)

        # NeuMLP prediction
        self.neumlp = nn.Linear(embedding_dim + mlp_dims[-1], 1)

        self._init_weights()

    def _init_weights(self) -> None:
        for module in self.modules():
            if isinstance(module, nn.Embedding):
                nn.init.xavier_uniform_(module.weight)
            elif isinstance(module, nn.Linear):
                nn.init.kaiming_uniform_(module.weight, nonlinearity="relu")
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(
        self, user_ids: torch.Tensor, item_ids: torch.Tensor
    ) -> torch.Tensor:
        # GMF path
        gmf_user = self.gmf_user_embedding(user_ids)
        gmf_item = self.gmf_item_embedding(item_ids)
        gmf_out = gmf_user * gmf_item

        # MLP path
        mlp_user = self.mlp_user_embedding(user_ids)
        mlp_item = self.mlp_item_embedding(item_ids)
        mlp_input = torch.cat([mlp_user, mlp_item], dim=-1)
        mlp_out = self.mlp(mlp_input)

        # Combine
        concat = torch.cat([gmf_out, mlp_out], dim=-1)
        output = torch.sigmoid(self.neumlp(concat))
        return output.squeeze(-1)

    def predict_scores(
        self, user_ids: torch.Tensor, item_ids: torch.Tensor
    ) -> np.ndarray:
        self.eval()
        with torch.no_grad():
            scores = self.forward(user_ids, item_ids)
        return scores.cpu().numpy()


class NCFTrainer:
    """Trainer for the Neural Collaborative Filtering model."""

    def __init__(
        self,
        model: NeuralCollaborativeFiltering,
        lr: float = 0.001,
        weight_decay: float = 1e-5,
        device: str = "cpu",
    ):
        self.model = model.to(device)
        self.device = device
        self.optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
        self.criterion = nn.BCELoss()
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode="min", factor=0.5, patience=2
        )

    def train_epoch(self, dataloader: DataLoader) -> float:
        self.model.train()
        total_loss = 0.0
        for user_ids, item_ids, ratings in dataloader:
            user_ids = user_ids.to(self.device)
            item_ids = item_ids.to(self.device)
            ratings = ratings.to(self.device)

            self.optimizer.zero_grad()
            predictions = self.model(user_ids, item_ids)
            loss = self.criterion(predictions, ratings)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()

            total_loss += loss.item()

        avg_loss = total_loss / len(dataloader)
        self.scheduler.step(avg_loss)
        return avg_loss

    def train(
        self,
        dataset: InteractionDataset,
        epochs: int = 20,
        batch_size: int = 1024,
        val_split: float = 0.1,
    ) -> dict[str, list[float]]:
        """Full training loop with validation."""
        from sklearn.model_selection import train_test_split

        train_users, val_users, train_items, val_items, train_ratings, val_ratings = (
            train_test_split(
                dataset.user_ids.numpy(),
                dataset.item_ids.numpy(),
                dataset.ratings.numpy(),
                test_size=val_split,
                random_state=42,
            )
        )

        train_dataset = InteractionDataset(train_users, train_items, train_ratings)
        val_dataset = InteractionDataset(val_users, val_items, val_ratings)

        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size)

        history: dict[str, list[float]] = {"train_loss": [], "val_loss": []}
        best_val_loss = float("inf")

        for epoch in range(epochs):
            train_loss = self.train_epoch(train_loader)
            val_loss = self._validate(val_loader)

            history["train_loss"].append(train_loss)
            history["val_loss"].append(val_loss)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                self._save_checkpoint()

            if (epoch + 1) % 5 == 0:
                logger.info(
                    f"Epoch {epoch + 1}/{epochs} - "
                    f"train_loss={train_loss:.4f}, val_loss={val_loss:.4f}"
                )

        return history

    @torch.no_grad()
    def _validate(self, dataloader: DataLoader) -> float:
        self.model.eval()
        total_loss = 0.0
        for user_ids, item_ids, ratings in dataloader:
            user_ids = user_ids.to(self.device)
            item_ids = item_ids.to(self.device)
            ratings = ratings.to(self.device)
            predictions = self.model(user_ids, item_ids)
            loss = self.criterion(predictions, ratings)
            total_loss += loss.item()
        return total_loss / len(dataloader)

    def _save_checkpoint(self) -> None:
        path = settings.MODEL_DIR / "ncf_model.pt"
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.model.state_dict(), path)

    def load_checkpoint(self, path: Path | None = None) -> bool:
        if path is None:
            path = settings.MODEL_DIR / "ncf_model.pt"
        if not path.exists():
            return False
        try:
            self.model.load_state_dict(torch.load(path, map_location=self.device))
            self.model.eval()
            return True
        except Exception as e:
            logger.error(f"Failed to load NCF checkpoint: {e}")
            return False
