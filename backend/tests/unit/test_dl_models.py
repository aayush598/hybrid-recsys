"""Unit tests for the PyTorch deep learning models in ml/dl_models."""

from __future__ import annotations

import os

import pytest
import torch


def _ratings_matrix(batch: int = 4, n_items: int = 12, seed: int = 0) -> torch.Tensor:
    gen = torch.Generator().manual_seed(seed)
    ratings = (torch.rand(batch, n_items, generator=gen) * 5).round()
    return ratings * (torch.rand(batch, n_items, generator=gen) > 0.5)


def _sequences(batch: int = 4, seq_len: int = 6, n_items: int = 12, seed: int = 1) -> torch.Tensor:
    gen = torch.Generator().manual_seed(seed)
    return torch.randint(0, n_items, (batch, seq_len), generator=gen)


def _assert_tuple_list(result):
    assert isinstance(result, list) and result
    assert all(isinstance(pair, tuple) and len(pair) == 2 for pair in result)
    scores = [score for _, score in result]
    assert scores == sorted(scores, reverse=True)


class TestAutoRec:
    def test_train_predict_save_load(self, tmp_path):
        from ml.dl_models import AutoRec

        model = AutoRec(n_items=12, hidden_dim=16)
        data = _ratings_matrix()
        loss = model.train_step(data)
        assert loss >= 0.0
        predictions = model.predict([5.0, 0.0, 3.0] + [0.0] * 9, top_k=5)
        _assert_tuple_list(predictions)

        path = str(tmp_path / "autorec.pt")
        model.save(path)
        restored = AutoRec(n_items=12, hidden_dim=16).load(path)
        assert restored.predict([5.0, 0.0, 3.0] + [0.0] * 9, top_k=5) == predictions
        assert os.path.exists(path)


class TestMultVAE:
    def test_train_predict_save_load(self, tmp_path):
        from ml.dl_models import MultVAE

        model = MultVAE(n_items=12, hidden_dim=24, latent_dim=8)
        data = _ratings_matrix()
        for _ in range(2):
            loss = model.train_step(data)
        assert loss >= 0.0
        predictions = model.predict([1.0, 1.0, 0.0, 1.0] + [0.0] * 8, top_k=4)
        _assert_tuple_list(predictions)

        path = str(tmp_path / "multvae.pt")
        model.save(path)
        restored = MultVAE(n_items=12, hidden_dim=24, latent_dim=8).load(path)
        assert restored.predict([1.0, 1.0, 0.0, 1.0] + [0.0] * 8, top_k=4) == predictions


class TestWideAndDeep:
    def test_train_predict_save_load(self, tmp_path):
        from ml.dl_models import WideAndDeep

        model = WideAndDeep(n_users=20, n_items=10, n_features=3, embed_dim=8)
        batch = 16
        users = torch.randint(0, 20, (batch,))
        items = torch.randint(0, 10, (batch,))
        features = torch.randn(batch, 3)
        labels = (torch.rand(batch) > 0.5).float()
        loss = model.train_step(users, items, features, labels)
        assert loss >= 0.0

        predictions = model.predict(user_id=3, candidate_item_ids=[0, 1, 2])
        _assert_tuple_list(predictions)
        assert {item for item, _ in predictions} == {0, 1, 2}

        path = str(tmp_path / "wdl.pt")
        model.save(path)
        WideAndDeep(n_users=20, n_items=10, n_features=3, embed_dim=8).load(path)


class TestDeepFM:
    def test_train_predict_save_load(self, tmp_path):
        from ml.dl_models import DeepFM

        model = DeepFM(field_dims=[20, 10], embed_dim=8)
        batch = 16
        features = torch.stack(
            [torch.randint(0, 20, (batch,)), torch.randint(0, 10, (batch,))], dim=1
        )
        labels = (torch.rand(batch) > 0.5).float()
        loss = model.train_step(features, labels)
        assert loss >= 0.0

        predictions = model.predict(features[:4])
        _assert_tuple_list(predictions)
        assert len(predictions) == 4

        path = str(tmp_path / "deepfm.pt")
        model.save(path)
        DeepFM(field_dims=[20, 10], embed_dim=8).load(path)


class TestLightGCN:
    def _graph(self):
        # Node ids are global: users [0, 4), items offset by n_users=4.
        users = torch.tensor([0, 0, 1, 2])
        items = torch.tensor([4, 5, 6, 7])
        return torch.stack([users, items])

    def test_train_predict_save_load(self, tmp_path):
        from ml.dl_models import LightGCN

        model = LightGCN(n_users=4, n_items=4, embed_dim=8, n_layers=2)
        edge_index = self._graph()
        loss = model.train_step(
            edge_index,
            users=torch.tensor([0, 1]),
            pos_items=torch.tensor([0, 2]),
            neg_items=torch.tensor([1, 3]),
        )
        assert loss >= 0.0

        predictions = model.predict(user_id=0, edge_index=edge_index, top_k=3)
        _assert_tuple_list(predictions)
        seen_items = {0, 1}
        assert all(item not in seen_items for item, _ in predictions)

        path = str(tmp_path / "lightgcn.pt")
        model.save(path)
        LightGCN(n_users=4, n_items=4, embed_dim=8, n_layers=2).load(path)


class TestSASRec:
    def test_train_predict_save_load(self, tmp_path):
        from ml.dl_models import SASRec

        model = SASRec(n_items=12, max_len=8, d_model=16, n_heads=2, n_blocks=1)
        sequences = _sequences(seq_len=8)
        positives = sequences[:, -1]
        negatives = (positives + 1) % 12
        loss = model.train_step(sequences, positives, negatives)
        assert loss >= 0.0

        sequence = [1, 2, 3, 4]
        predictions = model.predict(sequence, top_k=5)
        _assert_tuple_list(predictions)
        assert all(item not in sequence for item, _ in predictions)

        path = str(tmp_path / "sasrec.pt")
        model.save(path)
        SASRec(n_items=12, max_len=8, d_model=16, n_heads=2, n_blocks=1).load(path)


class TestBERT4Rec:
    def test_train_predict_save_load(self, tmp_path):
        from ml.dl_models import BERT4Rec

        model = BERT4Rec(n_items=12, max_len=8, d_model=16, n_heads=2, n_blocks=1)
        sequences = _sequences(seq_len=8)
        loss = model.train_step(sequences, mask_prob=0.25)
        assert loss >= 0.0

        sequence = [2, 4, 6, 8]
        predictions = model.predict(sequence, top_k=5)
        _assert_tuple_list(predictions)
        assert all(item not in sequence[:-1] for item, _ in predictions)

        path = str(tmp_path / "bert4rec.pt")
        model.save(path)
        BERT4Rec(n_items=12, max_len=8, d_model=16, n_heads=2, n_blocks=1).load(path)


class TestGRU4Rec:
    def test_train_predict_save_load(self, tmp_path):
        from ml.dl_models import GRU4Rec

        model = GRU4Rec(n_items=12, embed_dim=16, hidden_dim=16)
        sequences = _sequences(seq_len=6)
        targets = _sequences(batch=4, seq_len=1, seed=7).squeeze(1)
        loss = model.train_step(sequences, targets)
        assert loss >= 0.0

        predictions = model.predict([1, 2, 3], top_k=5)
        _assert_tuple_list(predictions)
        assert all(item not in (1, 2, 3) for item, _ in predictions)

        path = str(tmp_path / "gru4rec.pt")
        model.save(path)
        GRU4Rec(n_items=12, embed_dim=16, hidden_dim=16).load(path)


class TestStackingEnsemble:
    def test_train_predict_save_load(self, tmp_path):
        from ml.dl_models import StackingEnsemble

        ensemble = StackingEnsemble(n_models=3)
        base_scores = torch.rand(10, 3)
        target_scores = base_scores[:, 0]  # learnable: weight -> [1, 0, 0]
        first_loss = ensemble.train_step(base_scores, target_scores)
        for _ in range(30):
            final_loss = ensemble.train_step(base_scores, target_scores)
        assert final_loss < first_loss

        predictions = ensemble.predict(torch.rand(6, 3), top_k=4)
        _assert_tuple_list(predictions)
        assert len(predictions) == 4

        path = str(tmp_path / "stacking.pt")
        ensemble.save(path)
        StackingEnsemble(n_models=3).load(path)


class TestKnowledgeGraphEmbedding:
    def test_train_predict_save_load(self, tmp_path):
        from ml.dl_models import KnowledgeGraphEmbedding

        model = KnowledgeGraphEmbedding(n_entities=10, n_relations=3, embed_dim=8)
        positives = torch.tensor([[0, 0, 1], [2, 1, 3]])
        negatives = torch.tensor([[0, 0, 5], [2, 1, 6]])
        first_loss = model.train_step(positives, negatives)
        second_loss = model.train_step(positives, negatives)
        assert first_loss >= 0.0 and second_loss <= first_loss

        predictions = model.predict(head=0, relation=0, top_k=4)
        _assert_tuple_list(predictions)

        candidates = [1, 2, 3, 4]
        filtered = model.predict(head=0, relation=0, candidate_tails=candidates, top_k=4)
        _assert_tuple_list(filtered)
        assert {tail for tail, _ in filtered} == set(candidates)

        path = str(tmp_path / "transe.pt")
        model.save(path)
        KnowledgeGraphEmbedding(n_entities=10, n_relations=3, embed_dim=8).load(path)


def test_untrained_models_still_rank():
    """Predictions must be well-formed even before any training."""
    from ml.dl_models import AutoRec, GRU4Rec

    autorec = AutoRec(n_items=6)
    _assert_tuple_list(autorec.predict([1.0, 0.0, 2.0, 0.0, 0.0, 0.0], top_k=3))
    gru = GRU4Rec(n_items=6)
    _assert_tuple_list(gru.predict([0, 1, 2], top_k=3))
