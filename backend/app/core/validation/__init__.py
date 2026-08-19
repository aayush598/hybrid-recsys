"""Data Validation Module.

Implements schema validation, data quality checks, and anomaly detection
for incoming data streams in the recommendation system.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Result of a validation check."""
    check_name: str
    passed: bool
    severity: ValidationSeverity
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class SchemaValidator:
    """Validates data against expected schema."""

    def __init__(self):
        self.schemas: dict[str, dict[str, Any]] = {}

    def register_schema(
        self,
        name: str,
        schema: dict[str, Any],
    ):
        """Register a schema for validation."""
        self.schemas[name] = schema

    def validate(
        self,
        data: dict[str, Any],
        schema_name: str,
    ) -> list[ValidationResult]:
        """Validate data against a schema."""
        results = []
        schema = self.schemas.get(schema_name)
        if not schema:
            results.append(ValidationResult(
                check_name="schema_exists",
                passed=False,
                severity=ValidationSeverity.ERROR,
                message=f"Schema '{schema_name}' not found",
            ))
            return results

        # Check required fields
        for field_name, field_schema in schema.get("required", {}).items():
            if field_name not in data:
                results.append(ValidationResult(
                    check_name=f"required_field_{field_name}",
                    passed=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"Required field '{field_name}' missing",
                ))
            else:
                results.append(ValidationResult(
                    check_name=f"required_field_{field_name}",
                    passed=True,
                    severity=ValidationSeverity.INFO,
                    message=f"Required field '{field_name}' present",
                ))

        # Check field types
        for field_name, expected_type in schema.get("types", {}).items():
            if field_name in data:
                value = data[field_name]
                if not self._check_type(value, expected_type):
                    results.append(ValidationResult(
                        check_name=f"type_check_{field_name}",
                        passed=False,
                        severity=ValidationSeverity.WARNING,
                        message=f"Field '{field_name}' has wrong type: expected {expected_type}",
                    ))

        # Check constraints
        for field_name, constraints in schema.get("constraints", {}).items():
            if field_name in data:
                value = data[field_name]
                constraint_results = self._check_constraints(
                    field_name, value, constraints
                )
                results.extend(constraint_results)

        return results

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        type_map = {
            "int": int,
            "float": (int, float),
            "str": str,
            "bool": bool,
            "list": list,
            "dict": dict,
        }
        expected = type_map.get(expected_type)
        if expected:
            return isinstance(value, expected)
        return True

    def _check_constraints(
        self,
        field_name: str,
        value: Any,
        constraints: dict[str, Any],
    ) -> list[ValidationResult]:
        """Check field constraints."""
        results = []

        if "min" in constraints and value < constraints["min"]:
            results.append(ValidationResult(
                check_name=f"constraint_min_{field_name}",
                passed=False,
                severity=ValidationSeverity.WARNING,
                message=f"Field '{field_name}' below minimum: {value} < {constraints['min']}",
            ))

        if "max" in constraints and value > constraints["max"]:
            results.append(ValidationResult(
                check_name=f"constraint_max_{field_name}",
                passed=False,
                severity=ValidationSeverity.WARNING,
                message=f"Field '{field_name}' above maximum: {value} > {constraints['max']}",
            ))

        if "enum" in constraints and value not in constraints["enum"]:
            results.append(ValidationResult(
                check_name=f"constraint_enum_{field_name}",
                passed=False,
                severity=ValidationSeverity.WARNING,
                message=f"Field '{field_name}' not in allowed values: {constraints['enum']}",
            ))

        if "pattern" in constraints and isinstance(value, str):
            if not re.match(constraints["pattern"], value):
                results.append(ValidationResult(
                    check_name=f"constraint_pattern_{field_name}",
                    passed=False,
                    severity=ValidationSeverity.WARNING,
                    message=f"Field '{field_name}' doesn't match pattern: {constraints['pattern']}",
                ))

        return results


class DataQualityChecker:
    """Checks data quality across multiple dimensions."""

    def __init__(self):
        self.checks: list[Callable] = []

    def add_check(self, check_fn: Callable):
        """Add a quality check function."""
        self.checks.append(check_fn)

    def check_completeness(
        self,
        data: list[dict[str, Any]],
        required_fields: list[str],
    ) -> ValidationResult:
        """Check data completeness."""
        total = len(data)
        if total == 0:
            return ValidationResult(
                check_name="completeness",
                passed=False,
                severity=ValidationSeverity.ERROR,
                message="Empty dataset",
            )

        incomplete = 0
        for record in data:
            for field_name in required_fields:
                if field_name not in record or record[field_name] is None:
                    incomplete += 1
                    break

        completeness = 1 - (incomplete / total)
        threshold = 0.95

        return ValidationResult(
            check_name="completeness",
            passed=completeness >= threshold,
            severity=ValidationSeverity.WARNING if completeness < threshold else ValidationSeverity.INFO,
            message=f"Data completeness: {completeness:.2%}",
            details={
                "total_records": total,
                "incomplete_records": incomplete,
                "completeness_score": completeness,
                "threshold": threshold,
            },
        )

    def check_uniqueness(
        self,
        data: list[dict[str, Any]],
        key_fields: list[str],
    ) -> ValidationResult:
        """Check data uniqueness."""
        total = len(data)
        if total == 0:
            return ValidationResult(
                check_name="uniqueness",
                passed=True,
                severity=ValidationSeverity.INFO,
                message="Empty dataset",
            )

        seen = set()
        duplicates = 0
        for record in data:
            key = tuple(record.get(f) for f in key_fields)
            if key in seen:
                duplicates += 1
            seen.add(key)

        uniqueness = 1 - (duplicates / total)
        threshold = 0.99

        return ValidationResult(
            check_name="uniqueness",
            passed=uniqueness >= threshold,
            severity=ValidationSeverity.WARNING if uniqueness < threshold else ValidationSeverity.INFO,
            message=f"Data uniqueness: {uniqueness:.2%}",
            details={
                "total_records": total,
                "duplicate_records": duplicates,
                "uniqueness_score": uniqueness,
                "threshold": threshold,
            },
        )

    def check_range(
        self,
        data: list[dict[str, Any]],
        field_name: str,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> ValidationResult:
        """Check if field values are within range."""
        values = [
            record.get(field_name)
            for record in data
            if field_name in record and record[field_name] is not None
        ]

        if not values:
            return ValidationResult(
                check_name=f"range_{field_name}",
                passed=False,
                severity=ValidationSeverity.WARNING,
                message=f"No values found for field '{field_name}'",
            )

        out_of_range = 0
        for v in values:
            if min_value is not None and v < min_value:
                out_of_range += 1
            if max_value is not None and v > max_value:
                out_of_range += 1

        in_range = 1 - (out_of_range / len(values))
        threshold = 0.99

        return ValidationResult(
            check_name=f"range_{field_name}",
            passed=in_range >= threshold,
            severity=ValidationSeverity.WARNING if in_range < threshold else ValidationSeverity.INFO,
            message=f"Range check for '{field_name}': {in_range:.2%} in range",
            details={
                "field": field_name,
                "min_value": min_value,
                "max_value": max_value,
                "out_of_range": out_of_range,
                "total": len(values),
                "in_range_score": in_range,
            },
        )

    def check_distribution(
        self,
        values: list[float],
        feature_name: str,
        baseline_mean: float | None = None,
        baseline_std: float | None = None,
    ) -> ValidationResult:
        """Check if distribution matches baseline."""
        if not values:
            return ValidationResult(
                check_name=f"distribution_{feature_name}",
                passed=False,
                severity=ValidationSeverity.WARNING,
                message=f"No values for distribution check: {feature_name}",
            )

        current_mean = float(np.mean(values))
        current_std = float(np.std(values))

        issues = []
        if baseline_mean is not None:
            mean_drift = abs(current_mean - baseline_mean) / (baseline_std or 1)
            if mean_drift > 3:
                issues.append(f"Mean drift: {mean_drift:.2f} std deviations")

        if baseline_std is not None:
            std_ratio = current_std / (baseline_std or 1)
            if std_ratio > 2 or std_ratio < 0.5:
                issues.append(f"Variance ratio: {std_ratio:.2f}")

        passed = len(issues) == 0
        return ValidationResult(
            check_name=f"distribution_{feature_name}",
            passed=passed,
            severity=ValidationSeverity.WARNING if not passed else ValidationSeverity.INFO,
            message=f"Distribution check for '{feature_name}': {'OK' if passed else 'Issues found'}",
            details={
                "feature": feature_name,
                "current_mean": current_mean,
                "current_std": current_std,
                "baseline_mean": baseline_mean,
                "baseline_std": baseline_std,
                "issues": issues,
            },
        )


class AnomalyDetector:
    """Detects anomalies in incoming data."""

    def __init__(self, z_threshold: float = 3.0):
        self.z_threshold = z_threshold
        self.feature_stats: dict[str, dict[str, float]] = {}

    def update_stats(self, feature_name: str, values: list[float]):
        """Update running statistics for a feature."""
        if not values:
            return
        self.feature_stats[feature_name] = {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "count": len(values),
        }

    def detect_anomalies(
        self,
        data: list[dict[str, Any]],
        feature_name: str,
    ) -> list[int]:
        """Detect anomalous records for a feature."""
        if feature_name not in self.feature_stats:
            return []

        stats = self.feature_stats[feature_name]
        if stats["std"] == 0:
            return []

        anomalies = []
        for i, record in enumerate(data):
            value = record.get(feature_name)
            if value is not None:
                z_score = abs(value - stats["mean"]) / stats["std"]
                if z_score > self.z_threshold:
                    anomalies.append(i)

        return anomalies

    def detect_batch_anomalies(
        self,
        data: list[dict[str, Any]],
        feature_names: list[str],
    ) -> dict[str, list[int]]:
        """Detect anomalies across multiple features."""
        results = {}
        for feature_name in feature_names:
            anomalies = self.detect_anomalies(data, feature_name)
            if anomalies:
                results[feature_name] = anomalies
        return results


class DataValidator:
    """Central data validation system."""

    def __init__(self):
        self.schema_validator = SchemaValidator()
        self.quality_checker = DataQualityChecker()
        self.anomaly_detector = AnomalyDetector()
        self.validation_history: list[dict[str, Any]] = []

    def register_rating_schema(self):
        """Register schema for rating data."""
        self.schema_validator.register_schema("rating", {
            "required": {
                "user_id": {"type": "int"},
                "item_id": {"type": "int"},
                "rating": {"type": "float"},
            },
            "types": {
                "user_id": "int",
                "item_id": "int",
                "rating": "float",
                "timestamp": "str",
            },
            "constraints": {
                "rating": {"min": 0.5, "max": 5.0},
                "user_id": {"min": 0},
                "item_id": {"min": 0},
            },
        })

    def register_user_schema(self):
        """Register schema for user data."""
        self.schema_validator.register_schema("user", {
            "required": {
                "user_id": {"type": "int"},
            },
            "types": {
                "user_id": "int",
                "age": "int",
                "gender": "str",
            },
            "constraints": {
                "age": {"min": 0, "max": 150},
                "gender": {"enum": ["M", "F", "Other", ""]},
            },
        })

    def validate_rating(self, rating: dict[str, Any]) -> list[ValidationResult]:
        """Validate a rating record."""
        return self.schema_validator.validate(rating, "rating")

    def validate_batch(
        self,
        data: list[dict[str, Any]],
        schema_name: str,
        required_fields: list[str],
        key_fields: list[str],
    ) -> dict[str, Any]:
        """Validate a batch of records."""
        all_results = []
        for record in data:
            results = self.schema_validator.validate(record, schema_name)
            all_results.extend(results)

        # Quality checks
        completeness = self.quality_checker.check_completeness(data, required_fields)
        uniqueness = self.quality_checker.check_uniqueness(data, key_fields)

        validation_summary = {
            "total_records": len(data),
            "schema_checks": len(all_results),
            "passed_checks": sum(1 for r in all_results if r.passed),
            "failed_checks": sum(1 for r in all_results if not r.passed),
            "completeness": completeness.to_dict(),
            "uniqueness": uniqueness.to_dict(),
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.validation_history.append(validation_summary)
        return validation_summary

    def get_validation_history(self, last_n: int = 10) -> list[dict[str, Any]]:
        """Get recent validation history."""
        return self.validation_history[-last_n:]


# Global validator instance
_data_validator: DataValidator | None = None


def get_data_validator() -> DataValidator:
    """Get the global data validator."""
    global _data_validator
    if _data_validator is None:
        _data_validator = DataValidator()
        _data_validator.register_rating_schema()
        _data_validator.register_user_schema()
    return _data_validator
