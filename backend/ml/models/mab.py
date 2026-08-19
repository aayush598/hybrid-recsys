"""Multi-Armed Bandit for Exploration/Exploitation.

Implements Thompson Sampling and LinUCB for balancing exploration
and exploitation in the recommendation system.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Arm:
    """A single arm (option) in the bandit."""
    arm_id: str
    alpha: float = 1.0  # Prior success count
    beta: float = 1.0   # Prior failure count
    total_pulls: int = 0
    total_rewards: float = 0.0
    features: np.ndarray | None = None  # For contextual bandits

    @property
    def mean_reward(self) -> float:
        """Expected reward for this arm."""
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        """Variance of reward distribution."""
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))

    def sample(self) -> float:
        """Sample from Beta distribution."""
        return np.random.beta(self.alpha, self.beta)

    def update(self, reward: float):
        """Update arm statistics with observed reward."""
        self.total_pulls += 1
        self.total_rewards += reward
        self.alpha += reward
        self.beta += (1 - reward)


class ThompsonSampler:
    """Thompson Sampling for discrete arms."""

    def __init__(self, arms: list[Arm] | None = None):
        self.arms: dict[str, Arm] = {}
        if arms:
            for arm in arms:
                self.arms[arm.arm_id] = arm

    def add_arm(self, arm_id: str, alpha: float = 1.0, beta: float = 1.0):
        """Add a new arm."""
        self.arms[arm_id] = Arm(arm_id=arm_id, alpha=alpha, beta=beta)

    def select_arm(self) -> str:
        """Select the best arm based on Thompson Sampling."""
        if not self.arms:
            raise ValueError("No arms available")

        samples = {arm_id: arm.sample() for arm_id, arm in self.arms.items()}
        return max(samples, key=samples.get)

    def update(self, arm_id: str, reward: float):
        """Update arm statistics after observing reward."""
        if arm_id in self.arms:
            self.arms[arm_id].update(reward)
        else:
            logger.warning(f"Unknown arm: {arm_id}")

    def get_arm_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all arms."""
        return {
            arm_id: {
                "mean_reward": arm.mean_reward,
                "variance": arm.variance,
                "total_pulls": arm.total_pulls,
                "alpha": arm.alpha,
                "beta": arm.beta,
            }
            for arm_id, arm in self.arms.items()
        }


class LinUCB:
    """LinUCB contextual bandit algorithm.

    Uses linear models to estimate rewards based on context features.
    """

    def __init__(self, n_features: int, alpha: float = 1.0):
        self.n_features = n_features
        self.alpha = alpha  # Exploration parameter
        self.arms: dict[str, Arm] = {}

        # Per-arm linear regression parameters
        self.A: dict[str, np.ndarray] = {}  # d x d matrix
        self.b: dict[str, np.ndarray] = {}  # d x 1 vector

    def add_arm(self, arm_id: str):
        """Add a new arm."""
        self.arms[arm_id] = Arm(arm_id=arm_id, features=None)
        self.A[arm_id] = np.eye(self.n_features)
        self.b[arm_id] = np.zeros(self.n_features)

    def select_arm(self, context: np.ndarray) -> str:
        """Select the best arm given context."""
        if not self.arms:
            raise ValueError("No arms available")

        ucb_values = {}
        for arm_id in self.arms:
            A_inv = np.linalg.inv(self.A[arm_id])
            theta = A_inv @ self.b[arm_id]

            # UCB = theta^T x + alpha * sqrt(x^T A^-1 x)
            x = context.reshape(-1, 1)
            ucb = float(theta @ context + self.alpha * np.sqrt(context @ A_inv @ context))
            ucb_values[arm_id] = ucb

        return max(ucb_values, key=ucb_values.get)

    def update(self, arm_id: str, context: np.ndarray, reward: float):
        """Update arm statistics after observing reward."""
        if arm_id not in self.arms:
            logger.warning(f"Unknown arm: {arm_id}")
            return

        x = context.reshape(-1, 1)
        self.A[arm_id] += x @ x.T
        self.b[arm_id] += reward * context

        self.arms[arm_id].update(reward)

    def get_arm_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all arms."""
        stats = {}
        for arm_id, arm in self.arms.items():
            A_inv = np.linalg.inv(self.A[arm_id])
            theta = A_inv @ self.b[arm_id]
            stats[arm_id] = {
                "theta": theta.tolist(),
                "mean_reward": arm.mean_reward,
                "total_pulls": arm.total_pulls,
            }
        return stats


class EpsilonGreedy:
    """Epsilon-Greedy algorithm for exploration/exploitation."""

    def __init__(self, epsilon: float = 0.1, decay: float = 0.999):
        self.epsilon = epsilon
        self.decay = decay
        self.arms: dict[str, Arm] = {}
        self.total_pulls = 0

    def add_arm(self, arm_id: str):
        """Add a new arm."""
        self.arms[arm_id] = Arm(arm_id=arm_id)

    def select_arm(self) -> str:
        """Select the best arm with epsilon-greedy strategy."""
        if not self.arms:
            raise ValueError("No arms available")

        self.total_pulls += 1
        current_epsilon = self.epsilon * (self.decay ** self.total_pulls)

        if np.random.random() < current_epsilon:
            # Explore: random arm
            return np.random.choice(list(self.arms.keys()))
        else:
            # Exploit: best arm
            return max(self.arms.keys(), key=lambda a: self.arms[a].mean_reward)

    def update(self, arm_id: str, reward: float):
        """Update arm statistics."""
        if arm_id in self.arms:
            self.arms[arm_id].update(reward)

    def get_arm_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all arms."""
        return {
            arm_id: {
                "mean_reward": arm.mean_reward,
                "total_pulls": arm.total_pulls,
            }
            for arm_id, arm in self.arms.items()
        }


class RecommendationBandit:
    """Multi-armed bandit for recommendation strategies.

    Each arm represents a different recommendation strategy
    (e.g., collaborative filtering, content-based, trending).
    """

    def __init__(self, strategy: str = "thompson"):
        self.strategy = strategy
        if strategy == "thompson":
            self.bandit = ThompsonSampler()
        elif strategy == "linucb":
            self.bandit = LinUCB(n_features=10)
        elif strategy == "epsilon_greedy":
            self.bandit = EpsilonGreedy()
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        self.reward_history: dict[str, list[float]] = defaultdict(list)

    def initialize_strategies(self, strategies: list[str]):
        """Initialize bandit arms for recommendation strategies."""
        for strategy in strategies:
            if self.strategy == "linucb":
                self.bandit.add_arm(strategy)
            else:
                self.bandit.add_arm(strategy)
        logger.info(f"Initialized {len(strategies)} strategies: {strategies}")

    def select_strategy(self, context: np.ndarray | None = None) -> str:
        """Select a recommendation strategy."""
        if self.strategy == "linucb" and context is not None:
            return self.bandit.select_arm(context)
        else:
            return self.bandit.select_arm()

    def update(self, strategy: str, reward: float, context: np.ndarray | None = None):
        """Update bandit with observed reward."""
        self.bandit.update(strategy, reward, context) if context is not None else self.bandit.update(strategy, reward)
        self.reward_history[strategy].append(reward)

    def get_strategy_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all strategies."""
        stats = self.bandit.get_arm_stats()
        for strategy in stats:
            history = self.reward_history.get(strategy, [])
            if history:
                stats[strategy]["recent_avg_reward"] = np.mean(history[-100:])
                stats[strategy]["reward_std"] = np.std(history[-100:]) if len(history) > 1 else 0
        return stats

    def compute_regret(self, optimal_reward: float) -> float:
        """Compute cumulative regret."""
        total_regret = 0
        for strategy, rewards in self.reward_history.items():
            for reward in rewards:
                total_regret += optimal_reward - reward
        return total_regret


# Global bandit instance
_recommendation_bandit: RecommendationBandit | None = None


def get_recommendation_bandit() -> RecommendationBandit:
    """Get the global recommendation bandit."""
    global _recommendation_bandit
    if _recommendation_bandit is None:
        _recommendation_bandit = RecommendationBandit(strategy="thompson")
        _recommendation_bandit.initialize_strategies([
            "collaborative_filtering",
            "content_based",
            "neural_cf",
            "trending",
            "hybrid",
        ])
    return _recommendation_bandit
