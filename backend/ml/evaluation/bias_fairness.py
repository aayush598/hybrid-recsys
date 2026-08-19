"""Bias and Fairness Evaluation Metrics.

Implements metrics for detecting and measuring bias in recommendations,
including popularity bias, fairness across user groups, and diversity metrics.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BiasMetrics:
    """Comprehensive bias and fairness metrics."""
    # Popularity bias
    gini_coefficient: float = 0.0
    popularity_bias_ratio: float = 0.0
    long_tail_coverage: float = 0.0

    # Fairness metrics
    demographic_parity: float = 0.0
    equal_opportunity: float = 0.0
    calibration_score: float = 0.0

    # Diversity metrics
    intra_list_diversity: float = 0.0
    average_similarity: float = 0.0
    coverage: float = 0.0
    novelty: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "gini_coefficient": self.gini_coefficient,
            "popularity_bias_ratio": self.popularity_bias_ratio,
            "long_tail_coverage": self.long_tail_coverage,
            "demographic_parity": self.demographic_parity,
            "equal_opportunity": self.equal_opportunity,
            "calibration_score": self.calibration_score,
            "intra_list_diversity": self.intra_list_diversity,
            "average_similarity": self.average_similarity,
            "coverage": self.coverage,
            "novelty": self.novelty,
        }


class PopularityBiasAnalyzer:
    """Analyzes popularity bias in recommendations."""

    def __init__(self, popularity_threshold_percentile: float = 80):
        self.popularity_threshold_percentile = popularity_threshold_percentile

    def compute_gini_coefficient(
        self,
        item_popularity: dict[int, int],
    ) -> float:
        """Compute Gini coefficient for item popularity distribution.

        Gini = 0 means perfect equality (all items equally popular)
        Gini = 1 means perfect inequality (one item gets all interactions)
        """
        if not item_popularity:
            return 0.0

        values = sorted(item_popularity.values())
        n = len(values)
        if n == 0:
            return 0.0

        cumulative = np.cumsum(values)
        gini = 1 - 2 * np.sum(cumulative) / (n * cumulative[-1]) + 1 / n
        return float(gini)

    def compute_popularity_bias_ratio(
        self,
        recommended_items: list[int],
        item_popularity: dict[int, int],
    ) -> float:
        """Compute ratio of popular items in recommendations.

        Returns fraction of recommendations that are popular items.
        """
        if not recommended_items or not item_popularity:
            return 0.0

        popularity_values = list(item_popularity.values())
        threshold = np.percentile(popularity_values, self.popularity_threshold_percentile)

        popular_count = sum(
            1 for item in recommended_items
            if item_popularity.get(item, 0) >= threshold
        )

        return popular_count / len(recommended_items)

    def compute_long_tail_coverage(
        self,
        recommended_items: list[int],
        item_popularity: dict[int, int],
    ) -> float:
        """Compute fraction of long-tail items in recommendations."""
        if not recommended_items or not item_popularity:
            return 0.0

        popularity_values = list(item_popularity.values())
        threshold = np.percentile(popularity_values, self.popularity_threshold_percentile)

        long_tail_count = sum(
            1 for item in recommended_items
            if item_popularity.get(item, 0) < threshold
        )

        return long_tail_count / len(recommended_items)


class FairnessAnalyzer:
    """Analyzes fairness across user groups."""

    def __init__(self):
        pass

    def compute_demographic_parity(
        self,
        recommendations: dict[str, list[int]],
        user_groups: dict[str, str],
        item_scores: dict[int, float],
    ) -> float:
        """Compute demographic parity across user groups.

        Measures if different user groups receive similar recommendation quality.
        """
        group_scores: dict[str, list[float]] = defaultdict(list)

        for user_id, recs in recommendations.items():
            group = user_groups.get(user_id, "unknown")
            avg_score = np.mean([item_scores.get(item, 0) for item in recs]) if recs else 0
            group_scores[group].append(avg_score)

        if len(group_scores) < 2:
            return 1.0  # Perfect parity with one group

        group_means = {g: np.mean(scores) for g, scores in group_scores.items()}
        max_mean = max(group_means.values())
        min_mean = min(group_means.values())

        if max_mean == 0:
            return 1.0

        return min_mean / max_mean

    def compute_equal_opportunity(
        self,
        relevant_items: dict[str, set[int]],
        recommendations: dict[str, list[int]],
        user_groups: dict[str, str],
    ) -> float:
        """Compute equal opportunity across user groups.

        Measures if different user groups have similar true positive rates.
        """
        group_tpr: dict[str, list[float]] = defaultdict(list)

        for user_id, recs in recommendations.items():
            relevant = relevant_items.get(user_id, set())
            if not relevant:
                continue

            group = user_groups.get(user_id, "unknown")
            hits = len(set(recs) & relevant)
            tpr = hits / len(relevant) if relevant else 0
            group_tpr[group].append(tpr)

        if len(group_tpr) < 2:
            return 1.0

        group_means = {g: np.mean(tprs) for g, tprs in group_tpr.items()}
        max_mean = max(group_means.values())
        min_mean = min(group_means.values())

        if max_mean == 0:
            return 1.0

        return min_mean / max_mean

    def compute_calibration_score(
        self,
        predicted_scores: dict[str, list[float]],
        actual_outcomes: dict[str, list[float]],
    ) -> float:
        """Compute calibration score across user groups.

        Measures if predicted scores match actual outcomes for each group.
        """
        calibration_scores = []

        for group in predicted_scores:
            if group not in actual_outcomes:
                continue

            pred_mean = np.mean(predicted_scores[group])
            actual_mean = np.mean(actual_outcomes[group])

            calibration_scores.append(abs(pred_mean - actual_mean))

        if not calibration_scores:
            return 1.0

        return 1.0 - np.mean(calibration_scores)


class DiversityAnalyzer:
    """Analyzes diversity of recommendations."""

    def __init__(self, item_embeddings: dict[int, np.ndarray] | None = None):
        self.item_embeddings = item_embeddings or {}

    def compute_intra_list_diversity(
        self,
        recommendations: list[int],
    ) -> float:
        """Compute intra-list diversity (average pairwise distance)."""
        if len(recommendations) < 2:
            return 0.0

        embeddings = [
            self.item_embeddings[item]
            for item in recommendations
            if item in self.item_embeddings
        ]

        if len(embeddings) < 2:
            return 0.0

        embeddings = np.array(embeddings)
        n = len(embeddings)

        # Compute pairwise cosine distances
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / (norms + 1e-10)
        similarity_matrix = np.dot(normalized, normalized.T)

        # Average pairwise distance
        total_distance = 0
        count = 0
        for i in range(n):
            for j in range(i + 1, n):
                total_distance += 1 - similarity_matrix[i, j]
                count += 1

        return total_distance / count if count > 0 else 0.0

    def compute_coverage(
        self,
        all_recommendations: list[list[int]],
        total_items: int,
    ) -> float:
        """Compute catalog coverage."""
        recommended_items = set()
        for recs in all_recommendations:
            recommended_items.update(recs)

        return len(recommended_items) / total_items if total_items > 0 else 0.0

    def compute_novelty(
        self,
        recommendations: list[int],
        item_popularity: dict[int, int],
    ) -> float:
        """Compute average novelty of recommendations.

        Novelty = -log2(popularity) where popularity is fraction of users
        who interacted with the item.
        """
        if not recommendations:
            return 0.0

        total_users = sum(item_popularity.values()) if item_popularity else 1

        novelties = []
        for item in recommendations:
            pop = item_popularity.get(item, 0) / total_users if total_users > 0 else 0
            if pop > 0:
                novelty = -np.log2(pop)
            else:
                novelty = np.log2(total_users)  # Max novelty for unseen items
            novelties.append(novelty)

        return float(np.mean(novelties))


class BiasFairnessEvaluator:
    """Comprehensive bias and fairness evaluator."""

    def __init__(
        self,
        item_popularity: dict[int, int] | None = None,
        item_embeddings: dict[int, np.ndarray] | None = None,
    ):
        self.item_popularity = item_popularity or {}
        self.item_embeddings = item_embeddings or {}

        self.popularity_analyzer = PopularityBiasAnalyzer()
        self.fairness_analyzer = FairnessAnalyzer()
        self.diversity_analyzer = DiversityAnalyzer(item_embeddings)

    def evaluate(
        self,
        all_recommendations: list[list[int]],
        user_recommendations: dict[str, list[int]] | None = None,
        user_groups: dict[str, str] | None = None,
        relevant_items: dict[str, set[int]] | None = None,
        item_scores: dict[int, float] | None = None,
        total_items: int = 62000,
    ) -> BiasMetrics:
        """Run comprehensive bias and fairness evaluation."""
        metrics = BiasMetrics()

        # Flatten recommendations for popularity analysis
        flat_recs = [item for recs in all_recommendations for item in recs]

        # Popularity bias
        metrics.gini_coefficient = self.popularity_analyzer.compute_gini_coefficient(
            self.item_popularity
        )
        metrics.popularity_bias_ratio = self.popularity_analyzer.compute_popularity_bias_ratio(
            flat_recs, self.item_popularity
        )
        metrics.long_tail_coverage = self.popularity_analyzer.compute_long_tail_coverage(
            flat_recs, self.item_popularity
        )

        # Fairness (if user groups provided)
        if user_recommendations and user_groups and item_scores:
            metrics.demographic_parity = self.fairness_analyzer.compute_demographic_parity(
                user_recommendations, user_groups, item_scores
            )
        if user_recommendations and user_groups and relevant_items:
            metrics.equal_opportunity = self.fairness_analyzer.compute_equal_opportunity(
                relevant_items, user_recommendations, user_groups
            )

        # Diversity
        if all_recommendations:
            ild_scores = [
                self.diversity_analyzer.compute_intra_list_diversity(recs)
                for recs in all_recommendations
                if len(recs) >= 2
            ]
            metrics.intra_list_diversity = float(np.mean(ild_scores)) if ild_scores else 0.0

        metrics.coverage = self.diversity_analyzer.compute_coverage(
            all_recommendations, total_items
        )
        metrics.novelty = self.diversity_analyzer.compute_novelty(
            flat_recs, self.item_popularity
        )

        return metrics

    def generate_report(self, metrics: BiasMetrics) -> dict[str, Any]:
        """Generate a bias/fairness report with interpretations."""
        interpretations = {}

        # Gini interpretation
        if metrics.gini_coefficient < 0.3:
            interpretations["gini"] = "Low inequality - recommendations are well distributed"
        elif metrics.gini_coefficient < 0.6:
            interpretations["gini"] = "Moderate inequality - some items dominate"
        else:
            interpretations["gini"] = "High inequality - strong popularity bias"

        # Coverage interpretation
        if metrics.coverage > 0.3:
            interpretations["coverage"] = "Good catalog coverage"
        elif metrics.coverage > 0.1:
            interpretations["coverage"] = "Moderate catalog coverage"
        else:
            interpretations["coverage"] = "Low catalog coverage - consider diversity boost"

        # Diversity interpretation
        if metrics.intra_list_diversity > 0.5:
            interpretations["diversity"] = "High diversity - recommendations are varied"
        elif metrics.intra_list_diversity > 0.3:
            interpretations["diversity"] = "Moderate diversity"
        else:
            interpretations["diversity"] = "Low diversity - recommendations are too similar"

        return {
            "metrics": metrics.to_dict(),
            "interpretations": interpretations,
            "recommendations": self._generate_recommendations(metrics),
        }

    def _generate_recommendations(self, metrics: BiasMetrics) -> list[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if metrics.gini_coefficient > 0.6:
            recommendations.append(
                "Apply popularity penalty or diversity re-ranking to reduce inequality"
            )

        if metrics.long_tail_coverage < 0.2:
            recommendations.append(
                "Increase exploration to expose long-tail items"
            )

        if metrics.intra_list_diversity < 0.3:
            recommendations.append(
                "Apply MMR (Maximal Marginal Relevance) to increase list diversity"
            )

        if metrics.coverage < 0.1:
            recommendations.append(
                "Implement exploration strategies to improve catalog coverage"
            )

        return recommendations
