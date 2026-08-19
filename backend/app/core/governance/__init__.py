"""Data Governance Module.

Implements data catalog, lineage tracking, quality monitoring,
retention policies, and PII handling for the recommendation system.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SensitivityLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DataQualityDimension(str, Enum):
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    VALIDITY = "validity"
    UNIQUENESS = "uniqueness"


@dataclass
class DataLineage:
    """Tracks data lineage from source to destination."""
    source: str
    transformation: str
    destination: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0"
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "transformation": self.transformation,
            "destination": self.destination,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
        }


@dataclass
class DatasetMetadata:
    """Metadata for a dataset in the catalog."""
    name: str
    description: str
    owner: str
    domain: str
    sensitivity_level: SensitivityLevel
    freshness: str  # real-time, hourly, daily, weekly
    retention_days: int
    schema_version: str
    tags: list[str] = field(default_factory=list)
    lineage: DataLineage | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "owner": self.owner,
            "domain": self.domain,
            "sensitivity_level": self.sensitivity_level.value,
            "freshness": self.freshness,
            "retention_days": self.retention_days,
            "schema_version": self.schema_version,
            "tags": self.tags,
            "lineage": self.lineage.to_dict() if self.lineage else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class DataCatalog:
    """Central registry for all datasets."""

    def __init__(self):
        self.datasets: dict[str, DatasetMetadata] = {}
        self._register_default_datasets()

    def _register_default_datasets(self):
        """Register default datasets for the recommendation system."""
        self.register(DatasetMetadata(
            name="users",
            description="User profiles and preferences",
            owner="data-team",
            domain="user",
            sensitivity_level=SensitivityLevel.CONFIDENTIAL,
            freshness="real-time",
            retention_days=1095,  # 3 years
            schema_version="1.0",
            tags=["users", "profiles", "pii"],
        ))
        self.register(DatasetMetadata(
            name="ratings",
            description="User-item ratings",
            owner="data-team",
            domain="interaction",
            sensitivity_level=SensitivityLevel.INTERNAL,
            freshness="real-time",
            retention_days=1095,
            schema_version="1.0",
            tags=["ratings", "interactions", "explicit"],
        ))
        self.register(DatasetMetadata(
            name="movies",
            description="Movie metadata and features",
            owner="content-team",
            domain="content",
            sensitivity_level=SensitivityLevel.PUBLIC,
            freshness="daily",
            retention_days=-1,  # Unlimited
            schema_version="1.0",
            tags=["movies", "metadata", "content"],
        ))
        self.register(DatasetMetadata(
            name="recommendations",
            description="Generated recommendations",
            owner="ml-team",
            domain="ml",
            sensitivity_level=SensitivityLevel.INTERNAL,
            freshness="real-time",
            retention_days=30,
            schema_version="1.0",
            tags=["recommendations", "ml", "predictions"],
        ))
        self.register(DatasetMetadata(
            name="features",
            description="Engineered features for ML models",
            owner="ml-team",
            domain="ml",
            sensitivity_level=SensitivityLevel.INTERNAL,
            freshness="hourly",
            retention_days=90,
            schema_version="1.0",
            tags=["features", "ml", "engineering"],
        ))

    def register(self, dataset: DatasetMetadata):
        """Register a dataset in the catalog."""
        self.datasets[dataset.name] = dataset
        logger.info(f"Registered dataset: {dataset.name}")

    def get(self, name: str) -> DatasetMetadata | None:
        """Get dataset metadata by name."""
        return self.datasets.get(name)

    def search(self, query: str) -> list[DatasetMetadata]:
        """Search datasets by name or tags."""
        results = []
        query_lower = query.lower()
        for dataset in self.datasets.values():
            if query_lower in dataset.name.lower() or any(
                query_lower in tag.lower() for tag in dataset.tags
            ):
                results.append(dataset)
        return results

    def list_all(self) -> list[DatasetMetadata]:
        """List all registered datasets."""
        return list(self.datasets.values())


class PIIHandler:
    """Handles PII detection, masking, and anonymization."""

    PII_FIELDS = {"email", "ip_address", "phone", "address", "ssn"}

    @staticmethod
    def pseudonymize_email(email: str) -> str:
        """Pseudonymize email while preserving domain."""
        hash_part = hashlib.sha256(email.encode()).hexdigest()[:12]
        domain = email.split("@")[-1] if "@" in email else "unknown.com"
        return f"{hash_part}@{domain}"

    @staticmethod
    def generalize_age(age: int) -> str:
        """Generalize age into buckets for k-anonymity."""
        if age < 0 or age > 150:
            return "unknown"
        if age < 18:
            return "under_18"
        elif age < 30:
            return "18-29"
        elif age < 50:
            return "30-49"
        elif age < 65:
            return "50-64"
        else:
            return "65+"

    @staticmethod
    def anonymize_ip(ip: str) -> str:
        """Anonymize IP address by zeroing last octet."""
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0"
        return "0.0.0.0"

    @staticmethod
    def hash_value(value: str) -> str:
        """One-way hash for pseudonymization."""
        return hashlib.sha256(value.encode()).hexdigest()

    @classmethod
    def mask_pii(cls, record: dict[str, Any]) -> dict[str, Any]:
        """Mask all PII fields in a record."""
        masked = record.copy()
        for field_name in cls.PII_FIELDS:
            if field_name in masked:
                value = masked[field_name]
                if field_name == "email":
                    masked[field_name] = cls.pseudonymize_email(value)
                elif field_name == "ip_address":
                    masked[field_name] = cls.anonymize_ip(value)
                else:
                    masked[field_name] = cls.hash_value(str(value))
        return masked


class DataRetentionManager:
    """Manages data retention and archival policies."""

    def __init__(self):
        self.policies: dict[str, dict[str, Any]] = {}

    def add_policy(
        self,
        dataset_name: str,
        retention_days: int,
        archive_after_days: int | None = None,
        delete_after_days: int | None = None,
    ):
        """Add retention policy for a dataset."""
        self.policies[dataset_name] = {
            "retention_days": retention_days,
            "archive_after_days": archive_after_days or retention_days * 3,
            "delete_after_days": delete_after_days or retention_days * 10,
        }
        logger.info(f"Added retention policy for {dataset_name}")

    def get_policy(self, dataset_name: str) -> dict[str, Any] | None:
        """Get retention policy for a dataset."""
        return self.policies.get(dataset_name)

    def get_datasets_for_deletion(self) -> list[str]:
        """Get datasets that should be deleted based on policies."""
        # In production, this would check actual data timestamps
        logger.info("Checking for datasets to delete...")
        return []

    def get_datasets_for_archival(self) -> list[str]:
        """Get datasets that should be archived."""
        logger.info("Checking for datasets to archive...")
        return []


class DataQualityChecker:
    """Checks data quality against defined rules."""

    def __init__(self):
        self.rules: dict[str, dict[str, Any]] = {}
        self.results: list[dict[str, Any]] = []

    def add_rule(
        self,
        dataset_name: str,
        dimension: DataQualityDimension,
        rule_name: str,
        threshold: float,
        check_fn: Any,
    ):
        """Add a quality rule."""
        if dataset_name not in self.rules:
            self.rules[dataset_name] = []
        self.rules[dataset_name].append({
            "dimension": dimension,
            "rule_name": rule_name,
            "threshold": threshold,
            "check_fn": check_fn,
        })

    def check_quality(
        self,
        dataset_name: str,
        data: Any,
    ) -> dict[str, DataQualityDimension, float]:
        """Run quality checks on a dataset."""
        scores: dict[DataQualityDimension, float] = {}
        rules = self.rules.get(dataset_name, [])

        for rule in rules:
            try:
                score = rule["check_fn"](data)
                scores[rule["dimension"]] = score
                self.results.append({
                    "dataset": dataset_name,
                    "rule": rule["rule_name"],
                    "score": score,
                    "threshold": rule["threshold"],
                    "passed": score >= rule["threshold"],
                    "timestamp": datetime.utcnow().isoformat(),
                })
            except Exception as e:
                logger.error(f"Quality check failed for {rule['rule_name']}: {e}")
                scores[rule["dimension"]] = 0.0

        return scores

    def get_quality_report(self) -> dict[str, Any]:
        """Generate a quality report."""
        return {
            "total_checks": len(self.results),
            "passed": sum(1 for r in self.results if r["passed"]),
            "failed": sum(1 for r in self.results if not r["passed"]),
            "results": self.results[-100:],  # Last 100 results
        }


class DataGovernanceManager:
    """Central manager for data governance."""

    def __init__(self):
        self.catalog = DataCatalog()
        self.pii_handler = PIIHandler()
        self.retention_manager = DataRetentionManager()
        self.quality_checker = DataQualityChecker()
        self.lineage: list[DataLineage] = []

    def add_lineage(self, lineage: DataLineage):
        """Add data lineage record."""
        self.lineage.append(lineage)
        logger.info(
            f"Lineage: {lineage.source} -> {lineage.transformation} -> {lineage.destination}"
        )

    def get_lineage(
        self,
        source: str | None = None,
        destination: str | None = None,
    ) -> list[DataLineage]:
        """Get lineage records filtered by source/destination."""
        results = self.lineage
        if source:
            results = [l for l in results if l.source == source]
        if destination:
            results = [l for l in results if l.destination == destination]
        return results

    def generate_governance_report(self) -> dict[str, Any]:
        """Generate comprehensive governance report."""
        return {
            "catalog": {
                "total_datasets": len(self.catalog.list_all()),
                "datasets": [d.to_dict() for d in self.catalog.list_all()],
            },
            "quality": self.quality_checker.get_quality_report(),
            "retention": {
                "total_policies": len(self.retention_manager.policies),
                "policies": self.retention_manager.policies,
            },
            "lineage": {
                "total_records": len(self.lineage),
                "recent": [l.to_dict() for l in self.lineage[-10:]],
            },
            "generated_at": datetime.utcnow().isoformat(),
        }


# Global governance manager
_governance_manager: DataGovernanceManager | None = None


def get_governance_manager() -> DataGovernanceManager:
    """Get the global data governance manager."""
    global _governance_manager
    if _governance_manager is None:
        _governance_manager = DataGovernanceManager()
    return _governance_manager
