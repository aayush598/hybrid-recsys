"""Multi-armed bandit algorithms for recommendation exploration.

Includes classic bandits (epsilon-greedy, UCB1, Thompson sampling) and a
contextual LinUCB bandit. Each arm tracks pull counts, mean reward, and
full reward history.
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


class MultiArmedBandit:
    """Classic multi-armed bandit with per-arm reward tracking.

    Supports epsilon-greedy, UCB1, and Thompson sampling (Beta posterior,
    suited to rewards in [0, 1]) arm-selection strategies.
    """

    METHODS = ("epsilon_greedy", "ucb", "thompson_sampling")

    def __init__(
        self,
        n_arms: int,
        epsilon: float = 0.1,
        method: str = "epsilon_greedy",
        seed: int | None = None,
    ):
        if n_arms < 1:
            raise ValueError("n_arms must be >= 1")
        self.n_arms = n_arms
        self.epsilon = float(epsilon)
        self.method = method
        self.rng = np.random.default_rng(seed)
        self.counts = np.zeros(n_arms, dtype=np.int64)
        self.values = np.zeros(n_arms, dtype=np.float64)
        self.reward_sums = np.zeros(n_arms, dtype=np.float64)
        self.rewards_history: list[list[float]] = [[] for _ in range(n_arms)]
        self.total_pulls = 0

    def select_arm(self, method: str | None = None) -> int:
        """Select an arm using the configured (or given) strategy."""
        chosen = method or self.method
        if chosen == "epsilon_greedy":
            return self.epsilon_greedy()
        if chosen == "ucb":
            return self.ucb()
        if chosen == "thompson_sampling":
            return self.thompson_sampling()
        raise ValueError(f"Unknown method {chosen!r}; expected one of {self.METHODS}")

    def predict(self, method: str | None = None) -> int:
        """Alias for select_arm for API consistency with other models."""
        return self.select_arm(method)

    def update(self, arm: int, reward: float) -> None:
        """Record an observed reward for an arm (incremental mean update)."""
        if not 0 <= arm < self.n_arms:
            raise ValueError(f"arm must be in [0, {self.n_arms})")
        reward = float(reward)
        self.counts[arm] += 1
        self.reward_sums[arm] += reward
        self.values[arm] = self.reward_sums[arm] / self.counts[arm]
        self.rewards_history[arm].append(reward)
        self.total_pulls += 1

    def epsilon_greedy(self) -> int:
        """Explore uniformly with probability epsilon, else exploit the best arm."""
        if self.total_pulls < self.n_arms:
            return int(self.total_pulls)
        if self.rng.random() < self.epsilon:
            return int(self.rng.integers(self.n_arms))
        return int(np.argmax(self.values))

    def ucb(self, c: float = 2.0) -> int:
        """UCB1: optimistic exploitation of mean reward plus confidence bonus."""
        if self.total_pulls < self.n_arms:
            return int(self.total_pulls)
        confidence = c * np.sqrt(2.0 * np.log(self.total_pulls + 1) / self.counts)
        return int(np.argmax(self.values + confidence))

    def thompson_sampling(self) -> int:
        """Sample from each arm's Beta posterior and pick the largest draw."""
        if self.total_pulls < self.n_arms:
            return int(self.total_pulls)
        successes = np.clip(self.reward_sums, 0.0, None)
        failures = np.maximum(self.counts - successes, 0.0)
        samples = self.rng.beta(successes + 1.0, failures + 1.0)
        return int(np.argmax(samples))

    @property
    def best_arm(self) -> int:
        """Arm with the highest empirical mean reward."""
        return int(np.argmax(self.values))

    def reset(self) -> None:
        """Clear all reward tracking state."""
        self.counts[:] = 0
        self.values[:] = 0
        self.reward_sums[:] = 0
        self.rewards_history = [[] for _ in range(self.n_arms)]
        self.total_pulls = 0


class LinUCB:
    """Contextual bandit (disjoint LinUCB model).

    Each arm maintains its own ridge-regularized linear model over context
    features; selection follows the standard UCB-style exploration bonus.
    """

    def __init__(self, n_arms: int, alpha: float = 1.0, n_features: int | None = None):
        if n_arms < 1:
            raise ValueError("n_arms must be >= 1")
        self.n_arms = n_arms
        self.alpha = float(alpha)
        self.n_features = n_features
        self.A: list[np.ndarray | None] = [None] * n_arms
        self.b: list[np.ndarray | None] = [None] * n_arms
        self.counts = np.zeros(n_arms, dtype=np.int64)
        self.values = np.zeros(n_arms, dtype=np.float64)

    def _ensure_arm(self, arm: int, context: np.ndarray) -> None:
        """Lazily initialize an arm's model matrices from the context dimension."""
        d = context.shape[0]
        if self.n_features is None:
            self.n_features = d
        elif d != self.n_features:
            raise ValueError(f"context dimension {d} != expected {self.n_features}")
        if self.A[arm] is None:
            self.A[arm] = np.eye(d)
            self.b[arm] = np.zeros(d)

    def select_arm(self, context: np.ndarray) -> int:
        """Select the arm maximizing theta^T x + alpha * sqrt(x^T A^-1 x)."""
        x = np.asarray(context, dtype=np.float64).ravel()
        scores = np.full(self.n_arms, -np.inf)
        for arm in range(self.n_arms):
            self._ensure_arm(arm, x)
            A_inv = np.linalg.inv(self.A[arm])
            theta = A_inv @ self.b[arm]
            bonus = self.alpha * np.sqrt(max(float(x @ A_inv @ x), 0.0))
            scores[arm] = float(theta @ x) + bonus
        return int(np.argmax(scores))

    def predict(self, context: np.ndarray) -> int:
        """Alias for select_arm for API consistency with other models."""
        return self.select_arm(context)

    def update(self, arm: int, context: np.ndarray, reward: float) -> None:
        """Update an arm's linear model with an observed (context, reward) pair."""
        if not 0 <= arm < self.n_arms:
            raise ValueError(f"arm must be in [0, {self.n_arms})")
        x = np.asarray(context, dtype=np.float64).ravel()
        self._ensure_arm(arm, x)
        self.A[arm] += np.outer(x, x)
        self.b[arm] += float(reward) * x
        self.counts[arm] += 1
        self.values[arm] += (
            float(reward) - self.values[arm]
        ) / self.counts[arm]

    def fit(
        self,
        contexts: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
    ) -> dict:
        """Offline training via replay of logged (context, action, reward) events.

        Args:
            contexts: Array of shape (n_events, n_features).
            actions: Arm index chosen at each event.
            rewards: Observed reward for each event.

        Returns:
            Training metrics including cumulative replay reward.
        """
        contexts = np.atleast_2d(np.asarray(contexts, dtype=np.float64))
        actions = np.asarray(actions).ravel()
        rewards = np.asarray(rewards, dtype=np.float64).ravel()

        if self.n_features is None:
            self.n_features = contexts.shape[1]
        for arm in range(self.n_arms):
            self._ensure_arm(arm, contexts[0])

        cumulative_reward = 0.0
        matches = 0
        for x, action, reward in zip(contexts, actions, rewards):
            chosen = self.select_arm(x)
            if chosen == int(action):
                matches += 1
                self.update(chosen, x, reward)
                cumulative_reward += float(reward)
        logger.info(
            "LinUCB fit on %d events, replay match rate %.3f",
            len(contexts),
            matches / max(len(contexts), 1),
        )
        return {
            "n_events": int(len(contexts)),
            "match_rate": matches / max(len(contexts), 1),
            "cumulative_replay_reward": cumulative_reward,
        }
