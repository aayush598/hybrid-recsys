"""Unit tests for extended serving: batch processing, A/B analysis,
cold start, and feedback loops (app/serving/advanced)."""

from __future__ import annotations

import pytest


class TestAdvancedBatchProcessor:
    async def test_processes_all_items_in_order(self):
        from app.serving.advanced import AdvancedBatchProcessor

        processor = AdvancedBatchProcessor(max_concurrency=3, batch_size=4)
        results = await processor.process(range(10), lambda x: x * 2)
        assert results == [x * 2 for x in range(10)]
        assert processor.stats["succeeded"] == 10
        assert processor.stats["failed"] == 0

    async def test_failures_become_none_and_count(self):
        from app.serving.advanced import AdvancedBatchProcessor

        def flaky(value):
            if value == 3:
                raise RuntimeError("boom")
            return value

        processor = AdvancedBatchProcessor(max_retries=1)
        results = await processor.process([1, 2, 3, 4], flaky)
        assert results == [1, 2, None, 4]
        assert processor.stats["failed"] == 1
        assert processor.stats["retries"] >= 1

    async def test_progress_callback_invoked(self):
        from app.serving.advanced import AdvancedBatchProcessor

        seen = []

        def on_progress(done, total):
            seen.append((done, total))

        processor = AdvancedBatchProcessor(batch_size=5)
        await processor.process(list(range(7)), lambda x: x, on_progress=on_progress)
        assert seen[-1] == (7, 7)

    async def test_async_functions_supported(self):
        from app.serving.advanced import AdvancedBatchProcessor

        async def double(value):
            return value * 2

        processor = AdvancedBatchProcessor()
        results = await processor.process([1, 2, 3], double)
        assert results == [2, 4, 6]

    def test_invalid_configuration_rejected(self):
        from app.serving.advanced import AdvancedBatchProcessor

        with pytest.raises(ValueError):
            AdvancedBatchProcessor(max_concurrency=0)


class TestABTestAnalyzer:
    def test_two_proportion_z_test(self):
        from app.serving.advanced import ABTestAnalyzer

        result = ABTestAnalyzer.two_proportion_z_test(
            conversions_a=50, exposures_a=1000,
            conversions_b=80, exposures_b=1000,
        )
        assert result["rate_a"] == pytest.approx(0.05)
        assert result["rate_b"] == pytest.approx(0.08)
        assert 0.0 <= result["p_value"] <= 1.0
        assert result["p_value"] < 0.05
        assert result["z_score"] > 0

    def test_identical_rates_not_significant(self):
        from app.serving.advanced import ABTestAnalyzer

        result = ABTestAnalyzer.two_proportion_z_test(60, 1000, 60, 1000)
        assert result["p_value"] > 0.05

    def test_confidence_interval_brackets_rate(self):
        from app.serving.advanced import ABTestAnalyzer

        low, high = ABTestAnalyzer.proportion_confidence_interval(100, 1000)
        rate = 100 / 1000
        assert low < rate < high

    def test_analyze_picks_significant_winner(self):
        from app.serving.advanced import ABTestAnalyzer

        analyzer = ABTestAnalyzer()
        report = analyzer.analyze(
            {
                "control": (50, 1000),
                "treatment": (90, 1000),
                "loser": (48, 1000),
            }
        )
        assert report["control"] == "control"
        assert report["variants"]["treatment"]["significant"]
        assert not report["variants"]["loser"]["significant"]
        assert report["winner"] == "treatment"

    def test_missing_control_raises(self):
        from app.serving.advanced import ABTestAnalyzer

        with pytest.raises(KeyError):
            ABTestAnalyzer().analyze({"arm_x": (10, 100)})


class TestColdStartHandler:
    def test_new_user_popularity_fallback(self):
        from app.serving.advanced import ColdStartHandler

        handler = ColdStartHandler()
        popularity = [("i1", 30.0), ("i2", 20.0), ("i3", 10.0)]
        recommendations = handler.recommend_for_new_user(popularity, top_k=2)
        assert [item for item, _ in recommendations] == ["i1", "i2"]

    def test_new_user_genre_preferences_boost_matching_items(self):
        from app.serving.advanced import ColdStartHandler

        handler = ColdStartHandler()
        popularity = [("action_flick", 10.0), ("romance_flick", 9.0)]
        preferences = {"Action": 1.0}
        genres = {"action_flick": "Action|Thriller", "romance_flick": "Romance"}
        recommendations = handler.recommend_for_new_user(
            popularity, genre_preferences=preferences, item_genres=genres, top_k=2
        )
        assert recommendations[0][0] == "action_flick"

    def test_new_item_finds_genre_neighbors(self):
        from app.serving.advanced import ColdStartHandler

        handler = ColdStartHandler()
        catalog = {
            "a": "Action|Sci-Fi",
            "b": "Action",
            "c": "Romance",
        }
        neighbors = handler.recommend_for_new_item("Action|Sci-Fi", catalog, top_k=2)
        assert neighbors[0][0] == "a"
        assert {item for item, _ in neighbors} == {"a", "b"}

    def test_epsilon_greedy_explores_and_exploits(self):
        from app.serving.advanced import ColdStartHandler

        exploiter = ColdStartHandler(epsilon=0.0, seed=1)
        assert exploiter.select_action({"a": 0.1, "b": 0.9}) == "b"

        explorer = ColdStartHandler(epsilon=1.0, seed=1)
        choices = {explorer.select_action({"a": 0.1, "b": 0.9}) for _ in range(50)}
        assert choices == {"a", "b"}

    def test_empty_scores_rejected(self):
        from app.serving.advanced import ColdStartHandler

        with pytest.raises(ValueError):
            ColdStartHandler().select_action({})


class TestFeedbackLoop:
    def _loop_with_events(self):
        from app.serving.advanced import FeedbackLoop

        loop = FeedbackLoop(min_events=10, negative_rate_threshold=0.5)
        for _ in range(8):
            loop.record("click", user_id="u1", item_id="i1")
        loop.record("impression", user_id="u1", item_id="i1")
        return loop

    def test_stats_aggregation(self):
        loop = self._loop_with_events()
        stats = loop.stats()
        assert stats["total"] == 9
        assert stats["counts"]["click"] == 8
        assert stats["positive_rate"] == pytest.approx(8 / 9)

    def test_no_retrain_below_min_events(self):
        loop = self._loop_with_events()
        assert not loop.should_retrain()

    def test_retrain_on_negative_feedback_spike(self):
        from app.serving.advanced import FeedbackLoop

        loop = FeedbackLoop(min_events=5, negative_rate_threshold=0.5)
        for _ in range(6):
            loop.record("dislike", user_id="u2", item_id="i9")
        assert loop.should_retrain()

    def test_drain_clears_buffer(self):
        loop = self._loop_with_events()
        drained = loop.drain()
        assert len(drained) == 9
        assert loop.stats()["total"] == 0

    def test_event_recorded_with_payload(self):
        from app.serving.advanced import FeedbackLoop

        loop = FeedbackLoop()
        event = loop.record("purchase", user_id="u7", item_id="i3", value=19.99)
        assert event.event_type == "purchase"
        assert event.value == 19.99
        assert loop.events[-1] is event
