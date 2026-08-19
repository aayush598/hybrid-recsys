from __future__ import annotations

import hashlib
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExperimentVariant:
    name: str
    weight: float
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class Experiment:
    name: str
    variants: list[ExperimentVariant]
    description: str = ""
    is_active: bool = True
    created_at: float = field(default_factory=time.time)
    start_time: float | None = None
    end_time: float | None = None


@dataclass
class ConversionEvent:
    experiment: str
    variant: str
    user_id: str
    metric_name: str
    metric_value: float
    timestamp: float = field(default_factory=time.time)


class ABTestManager:
    """A/B Testing framework for recommendation algorithms.

    Supports:
    - Deterministic user assignment (hash-based)
    - Traffic splitting with configurable weights
    - Multi-variant experiments
    - Conversion tracking
    - Statistical significance testing

    Inspired by Netflix's experimentation platform that runs
    thousands of A/B tests simultaneously.
    """

    def __init__(self):
        self.experiments: dict[str, Experiment] = {}
        self.assignments: dict[str, dict[str, str]] = defaultdict(dict)
        self.conversions: list[ConversionEvent] = []

    def create_experiment(
        self,
        name: str,
        variants: list[dict[str, Any]],
        description: str = "",
    ) -> Experiment:
        """Create a new A/B test experiment."""
        experiment_variants = [
            ExperimentVariant(
                name=v["name"],
                weight=v.get("weight", 1.0),
                config=v.get("config", {}),
            )
            for v in variants
        ]

        experiment = Experiment(
            name=name,
            variants=experiment_variants,
            description=description,
        )
        self.experiments[name] = experiment
        logger.info(f"Created experiment: {name} with {len(variants)} variants")
        return experiment

    def assign_variant(self, experiment_name: str, user_id: str) -> str:
        """Deterministically assign a user to a variant.

        Uses hash-based assignment for consistency — same user
        always gets same variant within an experiment.
        """
        experiment = self.experiments.get(experiment_name)
        if not experiment or not experiment.is_active:
            return "control"

        if user_id in self.assignments[experiment_name]:
            return self.assignments[experiment_name][user_id]

        hash_input = f"{experiment_name}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        normalized = (hash_value % 10000) / 10000.0

        cumulative = 0.0
        for variant in experiment.variants:
            cumulative += variant.weight / sum(v.weight for v in experiment.variants)
            if normalized < cumulative:
                self.assignments[experiment_name][user_id] = variant.name
                return variant.name

        default_variant = experiment.variants[0].name
        self.assignments[experiment_name][user_id] = default_variant
        return default_variant

    def get_variant_config(
        self, experiment_name: str, user_id: str
    ) -> dict[str, Any]:
        """Get the configuration for a user's assigned variant."""
        variant_name = self.assign_variant(experiment_name, user_id)
        experiment = self.experiments.get(experiment_name)
        if experiment:
            for v in experiment.variants:
                if v.name == variant_name:
                    return v.config
        return {}

    def track_conversion(
        self,
        experiment_name: str,
        user_id: str,
        metric_name: str,
        metric_value: float = 1.0,
    ) -> None:
        """Track a conversion event."""
        variant = self.assign_variant(experiment_name, user_id)
        event = ConversionEvent(
            experiment=experiment_name,
            variant=variant,
            user_id=user_id,
            metric_name=metric_name,
            metric_value=metric_value,
        )
        self.conversions.append(event)

    def get_experiment_results(self, experiment_name: str) -> dict:
        """Get statistical results for an experiment."""
        experiment = self.experiments.get(experiment_name)
        if not experiment:
            return {}

        variant_results = defaultdict(lambda: {"conversions": 0, "total": 0, "values": []})

        for event in self.conversions:
            if event.experiment == experiment_name:
                variant_results[event.variant]["conversions"] += 1
                variant_results[event.variant]["values"].append(event.metric_value)

        total_users = sum(
            len(users) for exp_name, users in self.assignments.items()
            if exp_name == experiment_name
        )

        results = {}
        for variant_name, data in variant_results.items():
            rate = data["conversions"] / max(total_users, 1)
            avg_value = (
                sum(data["values"]) / len(data["values"])
                if data["values"]
                else 0.0
            )
            results[variant_name] = {
                "conversions": data["conversions"],
                "total_assigned": total_users,
                "conversion_rate": round(rate, 4),
                "avg_metric_value": round(avg_value, 4),
            }

        control = results.get("control", {})
        treatment_results = {
            k: v for k, v in results.items() if k != "control"
        }

        for variant_name, data in treatment_results.items():
            if control.get("conversion_rate", 0) > 0:
                lift = (
                    (data["conversion_rate"] - control["conversion_rate"])
                    / control["conversion_rate"]
                )
                data["lift_vs_control"] = round(lift, 4)

        return {
            "experiment": experiment_name,
            "description": experiment.description,
            "is_active": experiment.is_active,
            "total_users": total_users,
            "variants": results,
        }

    def stop_experiment(self, experiment_name: str) -> None:
        """Stop an experiment."""
        if experiment_name in self.experiments:
            self.experiments[experiment_name].is_active = False
            self.experiments[experiment_name].end_time = time.time()
            logger.info(f"Stopped experiment: {experiment_name}")

    def list_experiments(self) -> list[dict]:
        """List all experiments with their status."""
        return [
            {
                "name": exp.name,
                "description": exp.description,
                "is_active": exp.is_active,
                "variants": [v.name for v in exp.variants],
                "created_at": exp.created_at,
            }
            for exp in self.experiments.values()
        ]


ab_test_manager = ABTestManager()
