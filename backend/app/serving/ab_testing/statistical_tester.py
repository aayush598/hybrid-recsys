"""Statistical testing for A/B experiments."""

from __future__ import annotations

import math

import numpy as np


class ABTestAnalyzer:
    """Statistical analysis for A/B test experiments."""

    def two_sample_proportion_test(
        self, successes_a: int, n_a: int, successes_b: int, n_b: int
    ) -> dict:
        """Z-test for two sample proportions."""
        p_a = successes_a / n_a if n_a > 0 else 0.0
        p_b = successes_b / n_b if n_b > 0 else 0.0
        p_pool = (successes_a + successes_b) / (n_a + n_b) if (n_a + n_b) > 0 else 0.0

        se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b)) if (n_a > 0 and n_b > 0) else 0.0
        z_stat = (p_a - p_b) / se if se > 0 else 0.0

        p_value = 2 * (1 - self._norm_cdf(abs(z_stat)))

        return {
            "z_statistic": round(z_stat, 4),
            "p_value": round(p_value, 4),
            "significant": p_value < 0.05,
            "rate_a": round(p_a, 4),
            "rate_b": round(p_b, 4),
            "lift": round((p_b - p_a) / p_a, 4) if p_a > 0 else 0.0,
        }

    def two_sample_t_test(self, values_a: list[float], values_b: list[float]) -> dict:
        """Welch's two-sample t-test."""
        a = np.array(values_a, dtype=float)
        b = np.array(values_b, dtype=float)

        mean_a, mean_b = a.mean(), b.mean()
        var_a, var_b = a.var(ddof=1), b.var(ddof=1)
        n_a, n_b = len(a), len(b)

        se = math.sqrt(var_a / n_a + var_b / n_b) if (n_a > 1 and n_b > 1) else 0.0
        t_stat = (mean_a - mean_b) / se if se > 0 else 0.0

        df = (var_a / n_a + var_b / n_b) ** 2 / (
            (var_a / n_a) ** 2 / (n_a - 1) + (var_b / n_b) ** 2 / (n_b - 1)
        ) if (n_a > 1 and n_b > 1) else 1.0

        p_value = 2 * (1 - self._t_cdf(abs(t_stat), df))

        return {
            "t_statistic": round(t_stat, 4),
            "p_value": round(p_value, 4),
            "significant": p_value < 0.05,
            "mean_a": round(mean_a, 4),
            "mean_b": round(mean_b, 4),
            "effect_size": round((mean_b - mean_a) / math.sqrt((var_a + var_b) / 2), 4) if (var_a + var_b) > 0 else 0.0,
        }

    def compute_confidence_interval(
        self, values: list[float], confidence: float = 0.95
    ) -> dict:
        """Compute confidence interval for a set of values."""
        arr = np.array(values, dtype=float)
        n = len(arr)
        mean = float(arr.mean())
        std = float(arr.std(ddof=1)) if n > 1 else 0.0
        se = std / math.sqrt(n) if n > 0 else 0.0

        z_crit = self._norm_ppf((1 + confidence) / 2)
        margin = z_crit * se

        return {
            "mean": round(mean, 4),
            "lower": round(mean - margin, 4),
            "upper": round(mean + margin, 4),
            "std": round(std, 4),
            "n": n,
            "confidence": confidence,
        }

    def minimum_sample_size(
        self, baseline_rate: float, mde: float, power: float = 0.8, alpha: float = 0.05
    ) -> int:
        """Calculate minimum sample size for a given MDE."""
        z_alpha = self._norm_ppf(1 - alpha / 2)
        z_beta = self._norm_ppf(power)

        p1 = baseline_rate
        p2 = baseline_rate * (1 + mde)
        p_avg = (p1 + p2) / 2

        n = (z_alpha * math.sqrt(2 * p_avg * (1 - p_avg)) + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2 / mde ** 2 if mde > 0 else 0
        return max(int(math.ceil(n)), 2)

    def analyze_ab_test(
        self, control_data: list[float], treatment_data: list[float], metric: str = "conversion"
    ) -> dict:
        """Full A/B test analysis with recommendations."""
        control_arr = np.array(control_data, dtype=float)
        treatment_arr = np.array(treatment_data, dtype=float)

        ci_control = self.compute_confidence_interval(control_data)
        ci_treatment = self.compute_confidence_interval(treatment_data)

        if metric == "conversion":
            ctrl_successes = int(control_arr.sum())
            treat_successes = int(treatment_arr.sum())
            significance = self.two_sample_proportion_test(
                ctrl_successes, len(control_data), treat_successes, len(treatment_data)
            )
        else:
            significance = self.two_sample_t_test(control_data, treatment_data)

        recommendation = "no_difference"
        if significance["significant"]:
            if significance.get("mean_b", significance.get("rate_b", 0)) > significance.get("mean_a", significance.get("rate_a", 0)):
                recommendation = "launch_treatment"
            else:
                recommendation = "keep_control"

        return {
            "metric": metric,
            "control": ci_control,
            "treatment": ci_treatment,
            "significance": significance,
            "recommendation": recommendation,
            "sample_sizes": {"control": len(control_data), "treatment": len(treatment_data)},
            "min_sample_size": self.minimum_sample_size(
                float(control_arr.mean()), 0.05  # 5% MDE
            ),
        }

    @staticmethod
    def _norm_cdf(x: float) -> float:
        """Approximate standard normal CDF."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    @staticmethod
    def _norm_ppf(p: float) -> float:
        """Approximate inverse normal CDF (Beasley-Springer-Moro)."""
        if p <= 0 or p >= 1:
            return 0.0
        if p < 0.5:
            return -ABTestAnalyzer._norm_ppf(1 - p)
        t = math.sqrt(-2 * math.log(1 - p))
        c0, c1, c2 = 2.515517, 0.802853, 0.010328
        d1, d2, d3 = 1.432788, 0.189269, 0.001308
        return t - (c0 + c1 * t + c2 * t ** 2) / (1 + d1 * t + d2 * t ** 2 + d3 * t ** 3)

    @staticmethod
    def _t_cdf(t: float, df: float) -> float:
        """Approximate t-distribution CDF using normal approximation for large df."""
        if df > 30:
            return ABTestAnalyzer._norm_cdf(t)
        x = df / (df + t ** 2)
        return 1 - 0.5 * ABTestAnalyzer._incomplete_beta(df / 2, 0.5, x) if t >= 0 else 0.5 * ABTestAnalyzer._incomplete_beta(df / 2, 0.5, x)

    @staticmethod
    def _incomplete_beta(a: float, b: float, x: float, n: int = 50) -> float:
        """Numerical approximation of regularized incomplete beta function."""
        if x <= 0:
            return 0.0
        if x >= 1:
            return 1.0
        term = 1.0
        result = 1.0
        for k in range(1, n + 1):
            if k % 2 == 1:
                m = (k - 1) // 2
                term *= x * (a + m) / (a + b + m) if (a + b + m) != 0 else 0
            else:
                m = k // 2
                term *= (1 - x) * (b + m - 1) / (a + b + m - 1) if (a + b + m - 1) != 0 else 0
            result += term
        return result
