from __future__ import annotations


class TestCollaborativeFiltering:
    """Unit tests for collaborative filtering model."""

    def test_model_initialization(self):
        from ml.models import NeuralCollaborativeFiltering

        model = NeuralCollaborativeFiltering(
            num_users=1000,
            num_items=500,
            embedding_dim=32,
            mlp_dims=[64, 32],
        )
        assert model.num_users == 1000
        assert model.num_items == 500

    def test_forward_pass_shape(self):
        import torch
        from ml.models import NeuralCollaborativeFiltering

        model = NeuralCollaborativeFiltering(
            num_users=100,
            num_items=50,
            embedding_dim=16,
            mlp_dims=[32, 16],
        )

        user_ids = torch.LongTensor([0, 1, 2, 3])
        item_ids = torch.LongTensor([0, 1, 2, 3])

        output = model(user_ids, item_ids)
        assert output.shape == (4,)
        assert all(0 <= v <= 1 for v in output.detach().numpy())

    def test_embedding_dimensions(self):
        import torch
        from ml.models import NeuralCollaborativeFiltering

        model = NeuralCollaborativeFiltering(
            num_users=100,
            num_items=50,
            embedding_dim=32,
        )

        user_emb = model.gmf_user_embedding(torch.LongTensor([0]))
        assert user_emb.shape == (1, 32)

        item_emb = model.gmf_item_embedding(torch.LongTensor([0]))
        assert item_emb.shape == (1, 32)


class TestContentBasedModel:
    """Unit tests for content-based model."""

    def test_index_building(self):
        from ml.models import ContentBasedModel

        model = ContentBasedModel()
        assert not model.is_loaded

    def test_prediction_without_index(self):
        from ml.models import ContentBasedModel

        model = ContentBasedModel()
        result = model.predict_from_history([1, 2, 3], top_k=10)
        assert result == []


class TestTrendingModel:
    """Unit tests for trending model."""

    def test_prediction_without_data(self):
        from ml.models import TrendingModel

        model = TrendingModel()
        assert not model.is_loaded
        result = model.predict(top_k=10)
        assert result == []

    def test_trending_with_data(self):
        from ml.models import TrendingModel

        model = TrendingModel()
        model.trending_cache = [(1, 10.0), (2, 8.0), (3, 6.0)]
        result = model.predict(top_k=2)
        assert len(result) == 2
        assert result[0][0] == 1


class TestHybridEnsemble:
    """Unit tests for hybrid ensemble."""

    def test_diversity(self):
        from ml.models import (
            CollaborativeFilteringModel,
            ContentBasedModel,
            HybridEnsemble,
            TrendingModel,
        )

        ensemble = HybridEnsemble(
            CollaborativeFilteringModel(),
            ContentBasedModel(),
            TrendingModel(),
        )

        scored = [(1, 0.9, "cf"), (2, 0.8, "cb"), (3, 0.7, "cf"), (4, 0.6, "cb")]
        diversified = ensemble._diversify(scored, top_k=3)
        assert len(diversified) == 3


class TestFeatureStore:
    """Unit tests for feature store."""

    def test_set_and_get(self):
        from app.features.store.online_store import FeatureStore

        store = FeatureStore()
        store.register_feature("avg_rating", "float", "Average user rating")

        store.set_online_features("user:1", {"avg_rating": 4.5})
        features = store.get_online_features("user:1", ["avg_rating"])

        assert features["avg_rating"] == 4.5

    def test_missing_feature(self):
        from app.features.store.online_store import FeatureStore

        store = FeatureStore()
        features = store.get_online_features("user:999", ["nonexistent"])
        assert features["nonexistent"] is None

    def test_bulk_get(self):
        from app.features.store.online_store import FeatureStore

        store = FeatureStore()
        store.set_online_features("user:1", {"score": 0.8})
        store.set_online_features("user:2", {"score": 0.6})

        results = store.bulk_get(["user:1", "user:2"], ["score"])
        assert len(results) == 2
        assert results["user:1"]["score"] == 0.8


class TestABTesting:
    """Unit tests for A/B testing framework."""

    def test_variant_assignment(self):
        from app.serving.ab_testing.manager import ABTestManager

        manager = ABTestManager()
        manager.create_experiment(
            "test_exp",
            [{"name": "control", "weight": 0.5}, {"name": "treatment", "weight": 0.5}],
        )

        variant = manager.assign_variant("test_exp", "user_123")
        assert variant in ["control", "treatment"]

    def test_deterministic_assignment(self):
        from app.serving.ab_testing.manager import ABTestManager

        manager = ABTestManager()
        manager.create_experiment(
            "test_exp",
            [{"name": "control", "weight": 0.5}, {"name": "treatment", "weight": 0.5}],
        )

        v1 = manager.assign_variant("test_exp", "user_42")
        v2 = manager.assign_variant("test_exp", "user_42")
        assert v1 == v2

    def test_conversion_tracking(self):
        from app.serving.ab_testing.manager import ABTestManager

        manager = ABTestManager()
        manager.create_experiment(
            "test_exp",
            [{"name": "control", "weight": 0.5}, {"name": "treatment", "weight": 0.5}],
        )

        for i in range(100):
            manager.track_conversion("test_exp", f"user_{i}", "click", 1.0)

        results = manager.get_experiment_results("test_exp")
        assert "variants" in results


class TestCircuitBreaker:
    """Unit tests for circuit breaker."""

    def test_closed_state(self):
        from app.serving.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker("test", failure_threshold=3)
        assert cb._should_allow_request()

    def test_opens_after_failures(self):
        from app.serving.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker("test", failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert not cb._should_allow_request()


class TestRateLimiter:
    """Unit tests for rate limiter."""

    def test_allows_within_limit(self):
        from app.serving.rate_limiter import SlidingWindowRateLimiter

        limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60)
        allowed, _ = limiter.is_allowed("user_1")
        assert allowed

    def test_blocks_over_limit(self):
        from app.serving.rate_limiter import SlidingWindowRateLimiter

        limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            limiter.is_allowed("user_1")
        allowed, info = limiter.is_allowed("user_1")
        assert not allowed
        assert info["remaining"] == 0


class TestEvaluationMetrics:
    """Unit tests for evaluation metrics."""

    def test_precision_at_k(self):
        from ml.evaluation.metrics import RecommendationEvaluator

        evaluator = RecommendationEvaluator.__new__(RecommendationEvaluator)
        recs = [1, 2, 3, 4, 5]
        relevant = {2, 4, 6}

        precision = evaluator.precision_at_k(recs, relevant, k=5)
        assert 0.0 <= precision <= 1.0
        assert precision == 2 / 5

    def test_recall_at_k(self):
        from ml.evaluation.metrics import RecommendationEvaluator

        evaluator = RecommendationEvaluator.__new__(RecommendationEvaluator)
        recs = [1, 2, 3, 4, 5]
        relevant = {1, 2, 3}

        recall = evaluator.recall_at_k(recs, relevant, k=5)
        assert recall == 1.0

    def test_ndcg_perfect(self):
        from ml.evaluation.metrics import RecommendationEvaluator

        evaluator = RecommendationEvaluator.__new__(RecommendationEvaluator)
        recs = [1, 2, 3]
        relevant = {1, 2, 3}

        ndcg = evaluator.ndcg_at_k(recs, relevant, k=3)
        assert ndcg == 1.0

    def test_ndcg_empty(self):
        from ml.evaluation.metrics import RecommendationEvaluator

        evaluator = RecommendationEvaluator.__new__(RecommendationEvaluator)
        ndcg = evaluator.ndcg_at_k([], set(), k=5)
        assert ndcg == 0.0

    def test_coverage(self):
        from ml.evaluation.metrics import RecommendationEvaluator

        evaluator = RecommendationEvaluator.__new__(RecommendationEvaluator)
        all_recs = [[1, 2], [2, 3], [3, 4]]
        coverage = evaluator.coverage(all_recs, total_items=5)
        assert 0.0 <= coverage <= 1.0
        assert coverage == 4 / 5
