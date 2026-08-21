"""PyTorch deep learning recommendation models.

Each model exposes a compact, uniform interface:

- ``train_step(*batch) -> float``: one optimization step on a mini-batch,
  returning the scalar loss.
- ``predict(...) -> list[tuple]``: ranked ``(item_id, score)`` pairs,
  highest score first.
- ``save(path)`` / ``load(path)``: state-dict persistence round-trip.

Models are intentionally small so they can be trained on CPU for smoke
tests and local experiments.
"""

from __future__ import annotations

import math

import torch
from torch import nn


def _top_k(scores: torch.Tensor, item_ids: list | None, top_k: int) -> list[tuple]:
    """Return the top-K ``(id, score)`` pairs sorted by descending score.

    Non-finite scores (e.g. ``-inf`` markers for excluded items) are dropped.
    """
    flat = scores.flatten()
    finite = torch.isfinite(flat)
    values, indices = torch.topk(flat[finite], k=min(top_k, int(finite.sum())))
    original_indices = finite.nonzero(as_tuple=False).flatten()[indices]
    ids = item_ids if item_ids is not None else list(range(scores.numel()))
    return [(ids[int(i)], float(v)) for v, i in zip(values, original_indices)]


class AutoRec(nn.Module):
    """Item-based autoencoder for collaborative filtering (I-AutoRec)."""

    def __init__(self, n_items: int = 50, hidden_dim: int = 32):
        super().__init__()
        self.n_items = n_items
        self.encoder = nn.Sequential(nn.Linear(n_items, hidden_dim), nn.ReLU())
        self.decoder = nn.Linear(hidden_dim, n_items)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))

    def train_step(
        self, ratings: torch.Tensor, mask: torch.Tensor | None = None
    ) -> float:
        """Reconstruct observed ratings; ``mask`` marks observed entries."""
        self.train()
        ratings = ratings.float()
        mask = torch.ones_like(ratings) if mask is None else mask.float()
        reconstructed = self(ratings)
        error = (reconstructed - ratings) * mask
        loss = error.pow(2).sum() / mask.sum().clamp(min=1.0)
        self.zero_grad()
        loss.backward()
        with torch.no_grad():
            for param in self.parameters():
                param -= 1e-2 * param.grad
        return float(loss.detach())

    def predict(
        self, user_ratings: list[float], top_k: int = 10, exclude_seen: bool = True
    ) -> list[tuple[int, float]]:
        """Score every item from the user's partial rating vector."""
        vector = torch.zeros(self.n_items)
        known = torch.tensor([r for r in user_ratings[: self.n_items]], dtype=torch.float32)
        vector[: known.numel()] = known
        with torch.no_grad():
            scores = self(vector.unsqueeze(0)).squeeze(0)
        if exclude_seen:
            scores[vector > 0] = -math.inf
        return _top_k(scores, None, top_k)

    def save(self, path: str) -> None:
        torch.save(self.state_dict(), path)

    def load(self, path: str) -> AutoRec:
        self.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        self.eval()
        return self


class MultVAE(nn.Module):
    """Variational autoencoder with multinomial likelihood for implicit feedback."""

    def __init__(
        self,
        n_items: int = 50,
        hidden_dim: int = 64,
        latent_dim: int = 16,
        dropout: float = 0.5,
    ):
        super().__init__()
        self.n_items = n_items
        self.encoder = nn.Sequential(
            nn.Linear(n_items, hidden_dim), nn.Tanh(), nn.Dropout(dropout),
            nn.Linear(hidden_dim, latent_dim * 2),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim), nn.Tanh(),
            nn.Linear(hidden_dim, n_items),
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        mu, logvar = self.encoder(x).chunk(2, dim=-1)
        if self.training:
            z = mu + torch.randn_like(mu) * torch.exp(0.5 * logvar)
        else:
            z = mu
        return self.decoder(z), mu, logvar

    def train_step(self, interactions: torch.Tensor, beta: float = 0.2) -> float:
        """Maximize the ELBO; returns the negative ELBO as scalar loss."""
        self.train()
        x = interactions.float()
        logits, mu, logvar = self(x)
        recon = nn.functional.binary_cross_entropy_with_logits(
            logits, x, reduction="sum"
        )
        kld = -0.5 * (1.0 + logvar - mu.pow(2) - logvar.exp()).sum()
        loss = (recon + beta * kld) / x.size(0)
        self.zero_grad()
        loss.backward()
        with torch.no_grad():
            for param in self.parameters():
                param -= 1e-3 * param.grad
        return float(loss.detach())

    def predict(
        self, user_ratings: list[float], top_k: int = 10, exclude_seen: bool = True
    ) -> list[tuple[int, float]]:
        vector = torch.zeros(self.n_items)
        known = torch.tensor(list(user_ratings)[: self.n_items], dtype=torch.float32)
        vector[: known.numel()] = known
        was_training = self.training
        self.eval()
        with torch.no_grad():
            scores = torch.sigmoid(self(vector.unsqueeze(0))[0]).squeeze(0)
        if was_training:
            self.train()
        if exclude_seen:
            scores[vector > 0] = -math.inf
        return _top_k(scores, None, top_k)

    def save(self, path: str) -> None:
        torch.save(self.state_dict(), path)

    def load(self, path: str) -> MultVAE:
        self.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        self.eval()
        return self


class WideAndDeep(nn.Module):
    """Wide-and-deep model blending a linear memorization term with an MLP."""

    def __init__(
        self,
        n_users: int = 100,
        n_items: int = 50,
        n_features: int = 4,
        embed_dim: int = 16,
        hidden_dims: tuple[int, ...] = (32, 16),
    ):
        super().__init__()
        self.user_embedding = nn.Embedding(n_users, embed_dim)
        self.item_embedding = nn.Embedding(n_items, embed_dim)
        input_dim = embed_dim * 2 + n_features
        self.wide = nn.Linear(input_dim, 1)
        layers: list[nn.Module] = []
        prev = input_dim
        for units in hidden_dims:
            layers += [nn.Linear(prev, units), nn.ReLU()]
            prev = units
        layers.append(nn.Linear(prev, 1))
        self.deep = nn.Sequential(*layers)

    def _logits(
        self,
        user_ids: torch.Tensor,
        item_ids: torch.Tensor,
        features: torch.Tensor,
    ) -> torch.Tensor:
        embedded = torch.cat(
            [self.user_embedding(user_ids), self.item_embedding(item_ids), features],
            dim=-1,
        )
        return (self.wide(embedded) + self.deep(embedded)).squeeze(-1)

    def train_step(
        self,
        user_ids: torch.Tensor,
        item_ids: torch.Tensor,
        features: torch.Tensor,
        labels: torch.Tensor,
    ) -> float:
        self.train()
        logits = self._logits(user_ids.long(), item_ids.long(), features.float())
        loss = nn.functional.binary_cross_entropy_with_logits(logits, labels.float())
        self.zero_grad()
        loss.backward()
        with torch.no_grad():
            for param in self.parameters():
                param -= 1e-2 * param.grad
        return float(loss.detach())

    def predict(
        self,
        user_id: int,
        candidate_item_ids: list[int],
        features: torch.Tensor | None = None,
    ) -> list[tuple[int, float]]:
        """Return ``[(item_id, click_probability)]`` sorted by probability."""
        items = torch.tensor(candidate_item_ids, dtype=torch.long)
        batch = items.numel()
        users = torch.full((batch,), int(user_id), dtype=torch.long)
        if features is None:
            features = torch.zeros(batch, self.wide.in_features - 2 * self.user_embedding.embedding_dim)
        was_training = self.training
        self.eval()
        with torch.no_grad():
            probs = torch.sigmoid(self._logits(users, items, features.float()))
        if was_training:
            self.train()
        return _top_k(probs, candidate_item_ids, len(candidate_item_ids))

    def save(self, path: str) -> None:
        torch.save(self.state_dict(), path)

    def load(self, path: str) -> WideAndDeep:
        self.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        self.eval()
        return self


class DeepFM(nn.Module):
    """Factorization-machine + deep MLP over categorical feature fields."""

    def __init__(
        self,
        field_dims: list[int],
        embed_dim: int = 8,
        hidden_dims: tuple[int, ...] = (16, 8),
    ):
        super().__init__()
        self.field_dims = list(field_dims)
        self.embeddings = nn.ModuleList(
            [nn.Embedding(dim, embed_dim) for dim in field_dims]
        )
        self.first_order = nn.ModuleList([nn.Embedding(dim, 1) for dim in field_dims])
        input_dim = embed_dim * len(field_dims)
        layers: list[nn.Module] = []
        prev = input_dim
        for units in hidden_dims:
            layers += [nn.Linear(prev, units), nn.ReLU()]
            prev = units
        layers.append(nn.Linear(prev, 1))
        self.mlp = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        field_embs = torch.stack(
            [emb(x[:, i]) for i, emb in enumerate(self.embeddings)], dim=1
        )
        first_order = sum(emb(x[:, i]) for i, emb in enumerate(self.first_order))
        sum_sq = field_embs.sum(dim=1).pow(2)
        sq_sum = field_embs.pow(2).sum(dim=1)
        fm = 0.5 * (sum_sq - sq_sum).sum(dim=-1, keepdim=True)
        deep = self.mlp(field_embs.flatten(start_dim=1))
        return (first_order + fm + deep).squeeze(-1)

    def train_step(self, features: torch.Tensor, labels: torch.Tensor) -> float:
        self.train()
        logits = self(features.long())
        loss = nn.functional.binary_cross_entropy_with_logits(logits, labels.float())
        self.zero_grad()
        loss.backward()
        with torch.no_grad():
            for param in self.parameters():
                param -= 1e-2 * param.grad
        return float(loss.detach())

    def predict(self, features: torch.Tensor) -> list[tuple[int, float]]:
        """Return ``[(row_index, probability)]`` sorted by probability."""
        was_training = self.training
        self.eval()
        with torch.no_grad():
            probs = torch.sigmoid(self(features.long()))
        if was_training:
            self.train()
        ranked = sorted(enumerate(float(p) for p in probs), key=lambda kv: kv[1], reverse=True)
        return [(int(i), p) for i, p in ranked]

    def save(self, path: str) -> None:
        torch.save(self.state_dict(), path)

    def load(self, path: str) -> DeepFM:
        self.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        self.eval()
        return self


class LightGCN(nn.Module):
    """LightGCN: simplified graph convolution using only neighbor aggregation.

    Node ids are global: users occupy ``[0, n_users)`` and items occupy
    ``[n_users, n_users + n_items)``. ``edge_index`` is a ``[2, E]`` tensor
    of (source, destination) node ids.
    """

    def __init__(
        self, n_users: int = 20, n_items: int = 20, embed_dim: int = 32, n_layers: int = 2
    ):
        super().__init__()
        self.n_users = n_users
        self.n_items = n_items
        self.n_layers = n_layers
        self.embedding = nn.Embedding(n_users + n_items, embed_dim)
        nn.init.xavier_uniform_(self.embedding.weight)

    def _propagate(self, edge_index: torch.Tensor) -> torch.Tensor:
        """Symmetric-normalized message passing averaged over layers."""
        n_nodes = self.n_users + self.n_items
        row = torch.cat([edge_index[0], edge_index[1]])
        col = torch.cat([edge_index[1], edge_index[0]])
        index = torch.cat([row, col])
        ones = torch.ones(index.numel())
        degree = torch.zeros(n_nodes).index_add_(0, index, ones).clamp(min=1.0)
        norm = (degree[row] * degree[col]).rsqrt()

        emb = self.embedding.weight
        out = emb.clone()
        for _ in range(self.n_layers):
            messages = emb[row] * norm.unsqueeze(-1)
            aggregated = torch.zeros_like(emb).index_add_(0, col, messages)
            out = out + aggregated
        return out / (self.n_layers + 1)

    def bpr_loss(
        self,
        emb: torch.Tensor,
        users: torch.Tensor,
        pos_items: torch.Tensor,
        neg_items: torch.Tensor,
    ) -> torch.Tensor:
        u = emb[users]
        p = emb[pos_items]
        n = emb[neg_items]
        pos_scores = (u * p).sum(dim=-1)
        neg_scores = (u * n).sum(dim=-1)
        return -nn.functional.logsigmoid(pos_scores - neg_scores).mean()

    def train_step(
        self,
        edge_index: torch.Tensor,
        users: torch.Tensor,
        pos_items: torch.Tensor,
        neg_items: torch.Tensor,
    ) -> float:
        self.train()
        emb = self._propagate(edge_index.long())
        loss = self.bpr_loss(
            emb,
            users.long(),
            pos_items.long() + self.n_users,
            neg_items.long() + self.n_users,
        )
        self.zero_grad()
        loss.backward()
        with torch.no_grad():
            for param in self.parameters():
                param -= 1e-2 * param.grad
        return float(loss.detach())

    def predict(
        self, user_id: int, edge_index: torch.Tensor, top_k: int = 10
    ) -> list[tuple[int, float]]:
        """Rank unseen items for a user by inner product with their embedding."""
        was_training = self.training
        self.eval()
        with torch.no_grad():
            emb = self._propagate(edge_index.long())
            user_vec = emb[int(user_id)]
            item_vecs = emb[self.n_users :]
            scores = item_vecs @ user_vec
            interacted = {
                int(node_id) - self.n_users
                for node_id in edge_index[1][edge_index[0] == int(user_id)].tolist()
            }
            for item_idx in interacted:
                if 0 <= item_idx < self.n_items:
                    scores[item_idx] = -math.inf
        if was_training:
            self.train()
        return _top_k(scores, None, top_k)

    def save(self, path: str) -> None:
        torch.save(self.state_dict(), path)

    def load(self, path: str) -> LightGCN:
        self.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        self.eval()
        return self


class SASRec(nn.Module):
    """Self-Attentive Sequential recommendation with causal transformer blocks."""

    def __init__(
        self,
        n_items: int = 50,
        max_len: int = 20,
        d_model: int = 32,
        n_heads: int = 2,
        n_blocks: int = 1,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.n_items = n_items
        self.max_len = max_len
        self.item_embedding = nn.Embedding(n_items + 1, d_model, padding_idx=n_items)
        self.position_embedding = nn.Embedding(max_len, d_model)
        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True,
        )
        self.blocks = nn.TransformerEncoder(layer, num_layers=n_blocks)

    def _encode(self, sequences: torch.Tensor) -> torch.Tensor:
        sequences = sequences.long()[:, -self.max_len :]
        lengths = (sequences != self.n_items).sum(dim=-1).clamp(min=1)
        positions = (
            torch.arange(sequences.size(1)).unsqueeze(0).expand_as(sequences)
        )
        hidden = self.item_embedding(sequences) + self.position_embedding(positions)
        mask = sequences == self.n_items
        hidden = self.blocks(hidden, src_key_padding_mask=mask)
        last = (lengths - 1).view(-1, 1, 1).expand(-1, 1, hidden.size(-1))
        return hidden.gather(1, last).squeeze(1)

    def train_step(
        self, sequences: torch.Tensor, positives: torch.Tensor, negatives: torch.Tensor
    ) -> float:
        """Binary cross-entropy over one positive and one sampled negative."""
        self.train()
        hidden = self._encode(sequences)
        pos = self.item_embedding(positives.long())
        neg = self.item_embedding(negatives.long())
        pos_scores = (hidden * pos).sum(dim=-1)
        neg_scores = (hidden * neg).sum(dim=-1)
        loss = (
            -nn.functional.logsigmoid(pos_scores - neg_scores).mean()
        )
        self.zero_grad()
        loss.backward()
        with torch.no_grad():
            for param in self.parameters():
                param -= 1e-3 * param.grad
        return float(loss.detach())

    def predict(self, sequence: list[int], top_k: int = 10) -> list[tuple[int, float]]:
        """Score all items as the next interaction after ``sequence``."""
        padded = list(sequence)[-self.max_len :]
        padded = [self.n_items] * (self.max_len - len(padded)) + padded
        was_training = self.training
        self.eval()
        with torch.no_grad():
            hidden = self._encode(torch.tensor([padded]))
            scores = hidden @ self.item_embedding.weight[: self.n_items].T
        if was_training:
            self.train()
        for item_id in set(sequence):
            if 0 <= item_id < self.n_items:
                scores[0, item_id] = -math.inf
        return _top_k(scores, None, top_k)

    def save(self, path: str) -> None:
        torch.save(self.state_dict(), path)

    def load(self, path: str) -> SASRec:
        self.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        self.eval()
        return self


class BERT4Rec(nn.Module):
    """Bidirectional encoder with masked-item prediction (BERT4Rec)."""

    def __init__(
        self,
        n_items: int = 50,
        max_len: int = 20,
        d_model: int = 32,
        n_heads: int = 2,
        n_blocks: int = 1,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.n_items = n_items
        self.mask_id = n_items
        self.max_len = max_len
        self.item_embedding = nn.Embedding(n_items + 1, d_model)
        self.position_embedding = nn.Embedding(max_len, d_model)
        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True,
        )
        self.blocks = nn.TransformerEncoder(layer, num_layers=n_blocks)
        self.output = nn.Linear(d_model, n_items)

    def _encode(self, sequences: torch.Tensor) -> torch.Tensor:
        positions = (
            torch.arange(sequences.size(1)).unsqueeze(0).expand_as(sequences)
        )
        hidden = self.item_embedding(sequences.long()) + self.position_embedding(positions)
        return self.blocks(hidden)

    def train_step(self, sequences: torch.Tensor, mask_prob: float = 0.15) -> float:
        """Mask random positions and predict the original items (cross-entropy)."""
        self.train()
        sequences = sequences.long()[:, -self.max_len :]
        labels = sequences.clone()
        maskable = sequences != self.mask_id
        random_scores = torch.rand(sequences.shape)
        masked = (random_scores < mask_prob) & maskable
        if not masked.any():
            masked.view(-1)[0] = True
        inputs = sequences.clone()
        inputs[masked] = self.mask_id
        logits = self.output(self._encode(inputs))
        loss = nn.functional.cross_entropy(
            logits[masked], labels[masked]
        )
        self.zero_grad()
        loss.backward()
        with torch.no_grad():
            for param in self.parameters():
                param -= 1e-3 * param.grad
        return float(loss.detach())

    def predict(self, sequence: list[int], top_k: int = 10) -> list[tuple[int, float]]:
        """Rank items by the model's reconstruction of the final position."""
        trimmed = list(sequence)[-self.max_len :]
        inputs = torch.tensor([trimmed])
        inputs[0, -1] = self.mask_id
        was_training = self.training
        self.eval()
        with torch.no_grad():
            logits = self.output(self._encode(inputs))
            scores = logits[0, -1]
        if was_training:
            self.train()
        for item_id in set(trimmed[:-1]):
            if 0 <= item_id < self.n_items:
                scores[item_id] = -math.inf
        return _top_k(scores, None, top_k)

    def save(self, path: str) -> None:
        torch.save(self.state_dict(), path)

    def load(self, path: str) -> BERT4Rec:
        self.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        self.eval()
        return self


class GRU4Rec(nn.Module):
    """GRU-based sequential recommendation over item-id sessions."""

    def __init__(
        self,
        n_items: int = 50,
        embed_dim: int = 32,
        hidden_dim: int = 32,
        n_layers: int = 1,
    ):
        super().__init__()
        self.n_items = n_items
        self.item_embedding = nn.Embedding(n_items + 1, embed_dim, padding_idx=n_items)
        self.gru = nn.GRU(embed_dim, hidden_dim, num_layers=n_layers, batch_first=True)
        self.output = nn.Linear(hidden_dim, n_items)

    def train_step(self, sequences: torch.Tensor, targets: torch.Tensor) -> float:
        """Cross-entropy prediction of the next item for each session."""
        self.train()
        hidden, _ = self.gru(self.item_embedding(sequences.long()))
        logits = self.output(hidden[:, -1])
        loss = nn.functional.cross_entropy(logits, targets.long())
        self.zero_grad()
        loss.backward()
        with torch.no_grad():
            for param in self.parameters():
                param -= 1e-3 * param.grad
        return float(loss.detach())

    def predict(self, sequence: list[int], top_k: int = 10) -> list[tuple[int, float]]:
        """Rank items by predicted next-item probability."""
        trimmed = list(sequence)[-self.max_len :] if hasattr(self, "max_len") else list(sequence)
        was_training = self.training
        self.eval()
        with torch.no_grad():
            hidden, _ = self.gru(self.item_embedding(torch.tensor([trimmed]).long()))
            scores = self.output(hidden[:, -1]).squeeze(0)
        if was_training:
            self.train()
        for item_id in set(sequence):
            if 0 <= item_id < self.n_items:
                scores[item_id] = -math.inf
        return _top_k(scores, None, top_k)

    def save(self, path: str) -> None:
        torch.save(self.state_dict(), path)

    def load(self, path: str) -> GRU4Rec:
        self.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        self.eval()
        return self


class StackingEnsemble(nn.Module):
    """Learned linear blend of base recommender score columns (stacking)."""

    def __init__(self, n_models: int = 3):
        super().__init__()
        self.n_models = n_models
        self.weights = nn.Parameter(torch.ones(n_models) / n_models)

    def forward(self, base_scores: torch.Tensor) -> torch.Tensor:
        normalized = torch.softmax(self.weights, dim=0)
        return base_scores @ normalized

    def train_step(
        self, base_scores: torch.Tensor, target_scores: torch.Tensor
    ) -> float:
        """Fit blend weights toward ground-truth relevance scores (MSE)."""
        self.train()
        blended = self(base_scores.float())
        loss = nn.functional.mse_loss(blended, target_scores.float())
        self.zero_grad()
        loss.backward()
        with torch.no_grad():
            self.weights -= 5e-2 * self.weights.grad
        return float(loss.detach())

    def predict(self, base_scores: torch.Tensor, top_k: int = 10) -> list[tuple[int, float]]:
        """Blend base-model scores per item and return the top-K ranked pairs."""
        was_training = self.training
        self.eval()
        with torch.no_grad():
            blended = self(base_scores.float())
        if was_training:
            self.train()
        return _top_k(blended, None, top_k)

    def save(self, path: str) -> None:
        torch.save(self.state_dict(), path)

    def load(self, path: str) -> StackingEnsemble:
        self.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        self.eval()
        return self


class KnowledgeGraphEmbedding(nn.Module):
    """TransE knowledge-graph embeddings for graph-aware recommendations."""

    def __init__(self, n_entities: int = 30, n_relations: int = 5, embed_dim: int = 16):
        super().__init__()
        self.n_entities = n_entities
        bound = 0.5 / embed_dim
        self.entities = nn.Embedding(n_entities, embed_dim)
        self.relations = nn.Embedding(n_relations, embed_dim)
        nn.init.uniform_(self.entities.weight, -bound, bound)
        nn.init.uniform_(self.relations.weight, -bound, bound)

    def _distance(
        self, heads: torch.Tensor, relations: torch.Tensor, tails: torch.Tensor
    ) -> torch.Tensor:
        h = nn.functional.normalize(self.entities(heads), dim=-1)
        r = self.relations(relations)
        t = nn.functional.normalize(self.entities(tails), dim=-1)
        return torch.norm(h + r - t, p=2, dim=-1)

    def train_step(
        self,
        positive_triples: torch.Tensor,
        negative_triples: torch.Tensor,
        margin: float = 1.0,
    ) -> float:
        """Margin ranking loss between true and corrupted triples."""
        self.train()
        pos = positive_triples.long()
        neg = negative_triples.long()
        d_pos = self._distance(pos[:, 0], pos[:, 1], pos[:, 2])
        d_neg = self._distance(neg[:, 0], neg[:, 1], neg[:, 2])
        loss = nn.functional.relu(margin + d_pos - d_neg).mean()
        self.zero_grad()
        loss.backward()
        with torch.no_grad():
            for param in self.parameters():
                param -= 1e-2 * param.grad
            self.entities.weight.div_(
                self.entities.weight.norm(dim=-1, keepdim=True).clamp(min=1e-8)
            )
        return float(loss.detach())

    def predict(
        self,
        head: int,
        relation: int,
        candidate_tails: list[int] | None = None,
        top_k: int = 10,
    ) -> list[tuple[int, float]]:
        """Rank tail entities by proximity to ``head + relation`` (higher = closer)."""
        tails = (
            torch.arange(self.n_entities)
            if candidate_tails is None
            else torch.tensor(candidate_tails)
        ).long()
        was_training = self.training
        self.eval()
        with torch.no_grad():
            distances = self._distance(
                torch.full((tails.numel(),), int(head)),
                torch.full((tails.numel(),), int(relation)),
                tails,
            )
            scores = -distances
        if was_training:
            self.train()
        ids = tails.tolist()
        return _top_k(scores, ids, top_k)

    def save(self, path: str) -> None:
        torch.save(self.state_dict(), path)

    def load(self, path: str) -> KnowledgeGraphEmbedding:
        self.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        self.eval()
        return self


__all__ = [
    "AutoRec",
    "BERT4Rec",
    "DeepFM",
    "GRU4Rec",
    "KnowledgeGraphEmbedding",
    "LightGCN",
    "MultVAE",
    "SASRec",
    "StackingEnsemble",
    "WideAndDeep",
]
