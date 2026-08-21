"""Unit tests for extended evaluation: online metrics, bias, benchmarks."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


class TestOnlineMetrics:
    def test_ctr(self):
        from ml.evaluation.online_metrics import OnlineMetrics

        assert OnlineMetrics.track_ctr(200, 26) == pytest.approx(0.13)
        assert OnlineMetrics.track_ctr(0, 10) == 0.0

    def test_conversion_rate(self):
        from ml.evaluation.online_metrics import OnlineMetrics

        assert OnlineMetrics.track_conversion(4, 50) == pytest.approx(0.08)
        assert OnlineMetrics.track_conversion(1, 0) == 0.0

    def test_session_depth_percentiles(self):
        from ml.evaluation.online_metrics import OnlineMetrics

        stats = OnlineMetrics.track_session_depth([1, 2, 3, 4, 5])
        assert stats["avg"] == pytest.approx(3.0)
        assert stats["p50"] == pytest.approx(3.0)
        assert stats["p95"] >= stats["p50"]

    def test_retention_day_cohorts(self):
        from ml.evaluation.online_metrics import OnlineMetrics

        activity = {
            "u1": [0, 1, 8],   # active day 1 and day 7+
            "u2": [0],         # churned after signup
            "u3": [0, 2, 35],
        }
        retention = OnlineMetrics.track_retention(activity)
        assert retention["day_1"] == pytest.approx(2 / 3)
        assert retention["day_7"] == pytest.approx(2 / 3)
        assert retention["day_30"] == pytest.approx(1 / 3)

    def test_revenue_metrics(self):
        from ml.evaluation.online_metrics import OnlineMetrics

        result = OnlineMetrics.track_revenue([10.0, 20.0, 30.0])
        assert result["aov"] == pytest.approx(20.0)
        assert result["total_revenue"] == pytest.approx(60.0)

    def test_event_stream_snapshot(self):
        from ml.evaluation.online_metrics import OnlineMetrics

        metrics = OnlineMetrics()
        for _ in range(8):
            metrics.record("impression")
        metrics.record("click", user_id="u1", item_id="i2")
        metrics.record("conversion", user_id="u1", item_id="i2", value=25.0)

        snapshot = metrics.snapshot()
        assert snapshot["total_impressions"] == 8
        assert snapshot["ctr"] == pytest.approx(1 / 8)
        assert snapshot["total_revenue"] == 25.0
        assert metrics.top_users_by_revenue(1)[0][0] == "u1"

        metrics.reset()
        assert metrics.snapshot()["total_clicks"] == 0.0


class TestBiasDetector:
    def test_gini_bounds(self):
        from ml.evaluation.bias_fairness import BiasDetector

        detector = BiasDetector()
        assert detector.gini_coefficient([1, 1, 1, 1]) == pytest.approx(0.0)
        assert detector.gini_coefficient([0, 0, 0, 10]) > 0.7
        assert 0.0 <= detector.gini_coefficient([3, 1, 4, 1, 5]) <= 1.0

    def test_popularity_bias_report(self):
        from ml.evaluation.bias_fairness import BiasDetector

        recommendations = [["a", "b"], ["a", "c"], ["a", "b"]]
        report = BiasDetector().popularity_bias(recommendations)
        assert {"gini_coefficient", "coverage", "unique_items"} <= set(report)
        assert report["unique_items"] == 3
        assert 0.0 <= report["gini_coefficient"] <= 1.0

    def test_position_bias_concentrated_vs_uniform(self):
        from ml.evaluation.bias_fairness import BiasDetector

        detector = BiasDetector()
        concentrated = detector.position_bias({0: 100, 1: 5, 2: 1, 3: 0})
        uniform = detector.position_bias({0: 25, 1: 25, 2: 25, 3: 25})
        assert concentrated > uniform
        assert uniform == pytest.approx(0.0)

    def test_demographic_parity_four_fifths(self):
        from ml.evaluation.bias_fairness import BiasDetector

        parity = BiasDetector.demographic_parity(
            {"group_a": [1, 1, 1, 1], "group_b": [1, 0, 0, 0]}
        )
        assert parity == pytest.approx(0.25)
        assert BiasDetector.demographic_parity({"g1": [1, 1], "g2": [1, 1]}) == 1.0

    def test_fairness_report_flags_imbalance(self):
        from ml.evaluation.bias_fairness import BiasDetector

        recommendations = [
            ["i1", "i2", "i3", "i4"],
            ["i1", "i2"],
            ["i3"],
        ]
        groups = {0: "mobile", 1: "mobile", 2: "web"}
        report = BiasDetector().compute_fairness_metrics(recommendations, groups)
        assert report["n_groups"] == 2
        assert 0.0 < report["exposure_parity_ratio"] <= 1.0
        assert isinstance(report["fair"], bool)


class TestBenchmarkSuite:
    def test_compare_with_baselines(self):
        from ml.evaluation.benchmark import BenchmarkSuite

        suite = BenchmarkSuite(seed=42)
        model_recs = [[1, 2, 3], [4, 5, 6]]
        relevance = [[1, 0, 1], [0, 1, 0]]
        interactions = pd.DataFrame(
            {"item_id": [1, 2, 2, 3, 3, 3], "user_id": list(range(6))}
        )

        results = suite.compare_with_baselines(
            model_recs,
            baselines={"random", "popularity"},
            relevance=relevance,
            interactions=interactions,
            top_k=3,
        )
        assert results["model"]["score"] == pytest.approx(0.5)
        assert "baseline_random" in results
        assert "baseline_popularity" in results
        assert "lift_vs_model_pct" in results["baseline_random"]
        assert len(results["model"]["per_user_scores"]) == 2

    def test_statistical_test_detects_difference(self):
        from ml.evaluation.benchmark import BenchmarkSuite

        rng = np.random.default_rng(0)
        better = rng.normal(0.8, 0.05, size=50)
        worse = rng.normal(0.5, 0.05, size=50)
        p_value = BenchmarkSuite.statistical_test(better, worse, method="ttest")
        assert p_value < 0.001
        assert BenchmarkSuite.statistical_test([1.0], [2.0]) == 1.0

    def test_bootstrap_confidence_interval_brackets_mean(self):
        from ml.evaluation.benchmark import BenchmarkSuite

        scores = np.linspace(0.4, 0.6, 100).tolist()
        low, high = BenchmarkSuite.bootstrap_confidence_interval(scores)
        assert low < 0.5 < high
        assert 0.0 <= low <= high <= 1.0

    def test_markdown_report_rendering(self):
        from ml.evaluation.benchmark import BenchmarkSuite

        suite = BenchmarkSuite()
        results = {
            "model": {"score": 0.42},
            "baseline_random": {"score": 0.20, "lift_vs_model_pct": -52.4},
        }
        report = suite.generate_report(results, format="markdown")
        assert "| **model** | 0.4200 |" in report
        assert "baseline_random" in report
