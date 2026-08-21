"""Unit tests for the new classical ML models in ml/models."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _interactions_df(n_users: int = 8, n_items: int = 6, seed: int = 42) -> pd.DataFrame:
    """Small dense-ish synthetic interaction log."""
    rng = np.random.default_rng(seed)
    rows = [
        (f"u{u}", f"i{i}", float(rng.integers(1, 6)))
        for u in range(n_users)
        for i in range(n_items)
        if rng.random() < 0.7
    ]
    return pd.DataFrame(rows, columns=["user_id", "item_id", "rating"])


def _movies_df(n_items: int = 6) -> pd.DataFrame:
    """Tiny movie catalog with distinct genre/overview text."""
    genres = ["Action|Adventure", "Romance|Drama", "Comedy", "Horror|Thriller",
              "Sci-Fi|Action", "Animation|Family"]
    overviews = [
        "explosions and car chases through the city",
        "a love story between two strangers",
        "hilarious jokes and funny situations",
        "dark scary nights and haunted houses",
        "space travel and futuristic robots",
        "colorful cartoon animals for kids",
    ]
    return pd.DataFrame(
        {
            "movie_id": [f"i{i}" for i in range(n_items)],
            "title": [f"Movie {i}" for i in range(n_items)],
            "genres": genres[:n_items],
            "overview": overviews[:n_items],
        }
    )


class TestUserBasedCF:
    def test_train_returns_metrics(self):
        from ml.models.user_cf import UserBasedCF

        model = UserBasedCF(n_neighbors=3)
        metrics = model.train(_interactions_df())
        assert model.is_trained
        assert metrics["n_users"] == 8
        assert metrics["n_interactions"] > 0

    def test_predict_returns_tuple_list(self):
        from ml.models.user_cf import UserBasedCF

        model = UserBasedCF(n_neighbors=3)
        model.train(_interactions_df())
        predictions = model.predict("u0", top_k=4)
        assert isinstance(predictions, list)
        assert len(predictions) <= 4
        assert all(isinstance(p, tuple) and len(p) == 2 for p in predictions)
        scores = [score for _, score in predictions]
        assert scores == sorted(scores, reverse=True)

    def test_predict_excludes_seen_items(self):
        from ml.models.user_cf import UserBasedCF

        model = UserBasedCF(n_neighbors=3)
        model.train(_interactions_df())
        seen = set(_interactions_df().query("user_id == 'u1'")["item_id"])
        predicted = {item for item, _ in model.predict("u1", top_k=20)}
        assert predicted.isdisjoint(seen)

    def test_untrained_and_unknown_user(self):
        from ml.models.user_cf import UserBasedCF

        untrained = UserBasedCF()
        assert untrained.predict("u0") == []
        trained = UserBasedCF(n_neighbors=3)
        trained.train(_interactions_df())
        fallback = trained.predict("ghost_user", top_k=3)
        assert len(fallback) == 3


class TestItemBasedCF:
    def test_train_returns_metrics(self):
        from ml.models.item_cf import ItemBasedCF

        model = ItemBasedCF(n_neighbors=3)
        metrics = model.train(_interactions_df())
        assert model.is_trained
        assert metrics["n_items"] == 6

    def test_predict_returns_sorted_tuples(self):
        from ml.models.item_cf import ItemBasedCF

        model = ItemBasedCF(n_neighbors=3)
        model.train(_interactions_df())
        predictions = model.predict("u2", top_k=5)
        assert all(isinstance(p, tuple) for p in predictions)
        scores = [s for _, s in predictions]
        assert scores == sorted(scores, reverse=True)

    def test_similar_items(self):
        from ml.models.item_cf import ItemBasedCF

        model = ItemBasedCF(n_neighbors=3)
        model.train(_interactions_df())
        similar = model.similar_items("i0", top_k=3)
        assert all(item != "i0" for item, _ in similar)

    def test_unknown_user_popularity_fallback(self):
        from ml.models.item_cf import ItemBasedCF

        model = ItemBasedCF()
        model.train(_interactions_df())
        fallback = model.predict("nobody", top_k=2)
        assert len(fallback) == 2


class TestBM25Model:
    def test_build_index(self):
        from ml.models.bm25 import BM25Model

        model = BM25Model()
        stats = model.build_index(_movies_df())
        assert model.is_trained
        assert stats["n_docs"] == 6
        assert stats["n_terms"] > 0

    def test_score_ranks_matching_genre_first(self):
        from ml.models.bm25 import BM25Model

        model = BM25Model()
        model.build_index(_movies_df())
        results = model.score("scary haunted horror", top_k=3)
        assert results and results[0][0] == "i3"
        assert all(isinstance(r, tuple) for r in results)

    def test_similar_items_excludes_self(self):
        from ml.models.bm25 import BM25Model

        model = BM25Model()
        model.build_index(_movies_df())
        similar = model.similar_items("i0", top_k=3)
        assert all(item != "i0" for item, _ in similar)

    def test_empty_query_and_untrained(self):
        from ml.models.bm25 import BM25Model

        assert BM25Model().score("anything") == []
        model = BM25Model()
        model.build_index(_movies_df())
        assert model.score("!!!") == []


class TestContentEmbeddings:
    def test_build_embeddings(self):
        from ml.models.embeddings import ContentEmbeddings

        model = ContentEmbeddings(n_components=4)
        stats = model.build(_movies_df())
        assert model.is_trained
        assert stats["n_items"] == 6
        assert model.embeddings.shape[0] == 6

    def test_similar_items_returns_tuples(self):
        from ml.models.embeddings import ContentEmbeddings

        model = ContentEmbeddings(n_components=4)
        model.build(_movies_df())
        similar = model.similar_items("i0", top_k=3)
        assert all(isinstance(s, tuple) and s[0] != "i0" for s in similar)

    def test_get_embedding_vector(self):
        from ml.models.embeddings import ContentEmbeddings

        model = ContentEmbeddings(n_components=4)
        model.build(_movies_df())
        vector = model.get_embedding("i2")
        assert vector is not None and np.isfinite(vector).all()
        assert model.get_embedding("missing") is None


class TestMultiArmedBandit:
    @pytest.mark.parametrize("method", ["epsilon_greedy", "ucb", "thompson_sampling"])
    def test_all_methods_select_valid_arms(self, method):
        from ml.models.bandits import MultiArmedBandit

        bandit = MultiArmedBandit(n_arms=3, seed=42)
        for _ in range(30):
            arm = bandit.select_arm(method)
            assert 0 <= arm < 3
            bandit.update(arm, reward=arm * 0.4)

    def test_best_arm_converges_to_rewarding_arm(self):
        from ml.models.bandits import MultiArmedBandit

        bandit = MultiArmedBandit(n_arms=3, epsilon=0.1, seed=42)
        rng = np.random.default_rng(0)
        for _ in range(300):
            arm = bandit.select_arm()
            reward = rng.normal(1.0 if arm == 2 else 0.1)
            bandit.update(arm, reward=max(reward, 0.0))
        assert bandit.best_arm == 2

    def test_invalid_arm_raises(self):
        from ml.models.bandits import MultiArmedBandit

        bandit = MultiArmedBandit(n_arms=2)
        with pytest.raises(ValueError):
            bandit.update(arm=5, reward=1.0)


class TestDynamicHybrid:
    def test_predict_fuses_three_signals(self):
        from ml.models.dynamic_hybrid import DynamicHybrid

        hybrid = DynamicHybrid(cf_weight=0.5, content_weight=0.3, trending_weight=0.2)
        cf = [(1, 0.9), (2, 0.8)]
        content = [(2, 0.7), (3, 0.6)]
        trending = [(3, 0.5), (4, 0.4)]
        result = hybrid.predict(cf, content, trending, top_k=3)
        assert len(result) <= 3
        assert all(isinstance(r, tuple) for r in result)
        ranked_items = [item for item, _ in result]
        assert set(ranked_items) <= {1, 2, 3, 4}

    def test_weights_renormalize_to_one(self):
        from ml.models.dynamic_hybrid import DynamicHybrid

        hybrid = DynamicHybrid(cf_weight=2.0, content_weight=1.0, trending_weight=1.0)
        total = hybrid.cf_weight + hybrid.content_weight + hybrid.trending_weight
        assert total == pytest.approx(1.0)

    def test_confident_signal_gains_weight(self):
        from ml.models.dynamic_hybrid import DynamicHybrid

        hybrid = DynamicHybrid()
        before = (hybrid.cf_weight, hybrid.content_weight)
        hybrid.predict([(1, 0.9)], None, None, top_k=2)
        after = (hybrid.cf_weight, hybrid.content_weight)
        assert after[0] > before[0]
        assert after[1] < before[1]


class TestCascadeRecommender:
    def _build_cascade(self) -> "object":
        from ml.models.cascade import CascadeRecommender

        cascade = CascadeRecommender()
        cascade.add_generator(
            lambda user_id, k: [("a", 0.9), ("b", 0.8), ("c", 0.7), ("d", 0.6)]
        )
        cascade.add_filter(lambda cands, ctx: [c for c in cands if c["item_id"] != "d"])
        cascade.add_ranker(lambda cands, k: sorted(cands, key=lambda c: -c["score"])[:k])
        return cascade

    def test_full_pipeline_returns_ranked_tuples(self):
        cascade = self._build_cascade()
        result = cascade.predict("u1", top_k=2)
        assert result == [("a", 0.9), ("b", 0.8)]

    def test_seen_items_filtered_via_history(self):
        cascade = self._build_cascade()
        cascade.record_interaction("u1", "a")
        result = cascade.predict("u1", top_k=10)
        assert all(item != "a" for item, _ in result)

    def test_generator_failure_is_tolerated(self):
        from ml.models.cascade import CascadeRecommender

        cascade = CascadeRecommender()

        def broken(user_id, k):
            raise RuntimeError("boom")

        cascade.add_generator(broken)
        cascade.add_generator(lambda user_id, k: [("x", 1.0)])
        assert cascade.predict("u1", top_k=5) == [("x", 1.0)]


class TestMultiObjectiveHybrid:
    class _StaticModel:
        def __init__(self, predictions):
            self._predictions = predictions

        def predict(self, user_id, top_k):
            return self._predictions[:top_k]

    def test_predict_balances_objectives(self):
        from ml.models.hybrid_v2 import MultiObjectiveHybrid

        base_a = self._StaticModel([("i1", 0.95), ("i2", 0.90)])
        base_b = self._StaticModel([("i2", 0.80), ("i3", 0.70)])
        hybrid = MultiObjectiveHybrid(models=[base_a, base_b])
        result = hybrid.predict("u1", top_k=3)
        assert len(result) == 3
        assert all(isinstance(r, tuple) for r in result)
        assert {item for item, _ in result} == {"i1", "i2", "i3"}

    def test_no_models_returns_empty(self):
        from ml.models.hybrid_v2 import MultiObjectiveHybrid

        assert MultiObjectiveHybrid().predict("u1", top_k=5) == []

    def test_pareto_front_drops_dominated_candidates(self):
        from ml.models.hybrid_v2 import MultiObjectiveHybrid

        candidates = [
            {"relevance": 0.9, "diversity": 0.5, "novelty": 0.5},
            {"relevance": 0.5, "diversity": 0.5, "novelty": 0.5},
            {"relevance": 0.2, "diversity": 0.9, "novelty": 0.9},
        ]
        front = MultiObjectiveHybrid.pareto_front(candidates)
        assert candidates[1] not in front
        assert candidates[0] in front and candidates[2] in front

    def test_invalid_objective_rejected(self):
        from ml.models.hybrid_v2 import MultiObjectiveHybrid

        with pytest.raises(ValueError):
            MultiObjectiveHybrid(objectives=["profit"])
