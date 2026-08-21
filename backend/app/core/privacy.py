"""Privacy compliance utilities.

Provides data anonymization/pseudonymization, consent management
(GDPR right to erasure), and data retention policy enforcement.
All state is kept in-memory; only the standard library is used.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

_TIMESTAMP_FIELDS = ("timestamp", "created_at", "date", "updated_at")


def _parse_timestamp(value) -> datetime | None:
    """Best-effort conversion of a record timestamp to an aware datetime."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value, tz=timezone.utc)
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _record_age_days(record: dict, now: datetime) -> float | None:
    fields = [f for f in _TIMESTAMP_FIELDS if f in record]
    fields += [
        f for f in record
        if f not in fields
        and any(marker in f for marker in ("time", "date", "created", "updated"))
    ]
    for field in fields:
        dt = _parse_timestamp(record[field])
        if dt is not None:
            return (now - dt).total_seconds() / 86400.0
    return None


class DataAnonymizer:
    """Anonymize, pseudonymize and k-anonymize user records."""

    def __init__(self, salt: str | None = None):
        self.salt = salt or secrets.token_hex(16)

    def _hash(self, value: str) -> str:
        return hashlib.sha256(f"{self.salt}:{value}".encode()).hexdigest()

    def anonymize_user(self, data: dict) -> dict:
        """Hash identifying fields (username/email) and truncate IDs."""
        result = dict(data)
        for field in ("username", "email", "user_email"):
            if field in result and result[field] is not None:
                result[field] = self._hash(str(result[field]))
        for field in ("user_id", "id", "device_id", "session_id"):
            if field in result and result[field] is not None:
                digest = self._hash(str(result[field]))
                result[field] = digest[:12]
        return result

    def pseudonymize(self, records: list[dict], fields: list[str]) -> list[dict]:
        """Replace values of ``fields`` with stable random tokens.

        A unique token is generated per distinct original value so that
        joins across records remain possible without revealing the value.
        """
        token_map: dict[tuple[str, str], str] = {}
        out: list[dict] = []
        for record in records:
            new_record = dict(record)
            for field in fields:
                if field in new_record and new_record[field] is not None:
                    key = (field, str(new_record[field]))
                    if key not in token_map:
                        token_map[key] = f"tok_{secrets.token_hex(8)}"
                    new_record[field] = token_map[key]
            out.append(new_record)
        return out

    def k_anonymize(
        self,
        records: list[dict],
        quasi_identifiers: list[str],
        k: int,
    ) -> list[dict]:
        """Enforce k-anonymity over the given quasi-identifiers.

        Records are grouped by their quasi-identifier tuple. Groups with
        fewer than ``k`` members have their quasi-identifiers suppressed
        (set to ``None``) so they can no longer single out individuals.
        """
        if k < 1:
            raise ValueError("k must be >= 1")

        def qi_key(record: dict) -> tuple:
            return tuple(record.get(qi) for qi in quasi_identifiers)

        counts: dict[tuple, int] = {}
        for record in records:
            counts[qi_key(record)] = counts.get(qi_key(record), 0) + 1

        out: list[dict] = []
        for record in records:
            new_record = dict(record)
            if counts[qi_key(record)] < k:
                for qi in quasi_identifiers:
                    new_record[qi] = None
            out.append(new_record)
        return out


class ConsentManager:
    """In-memory consent ledger with GDPR erasure support."""

    VALID_CONSENT_TYPES = frozenset(
        {"analytics", "marketing", "personalization", "third_party"}
    )

    def __init__(self):
        # user_id -> {consent_type: {"granted": bool, "recorded_at": iso}}
        self._consents: dict[str, dict[str, dict]] = {}
        # user_id -> {category: [data items]}
        self._user_data: dict[str, dict[str, list]] = {}

    def register_data(self, user_id: str, category: str, items: list) -> None:
        """Attach stored data to a user so it can be discovered on erasure."""
        self._user_data.setdefault(user_id, {}).setdefault(category, []).extend(items)

    def record_consent(self, user_id: str, consent_type: str, granted: bool) -> None:
        """Record (or update) a user's consent decision."""
        if consent_type not in self.VALID_CONSENT_TYPES:
            raise ValueError(f"Unknown consent type: {consent_type!r}")
        self._consents.setdefault(user_id, {})[consent_type] = {
            "granted": bool(granted),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }

    def check_consent(self, user_id: str, consent_type: str) -> bool:
        """Return True only when consent was explicitly granted."""
        entry = self._consents.get(user_id, {}).get(consent_type)
        return bool(entry and entry["granted"])

    def delete_user_data(self, user_id: str) -> dict:
        """Erase all known data for ``user_id`` (GDPR Art. 17).

        Returns a report describing what was deleted.
        """
        deleted_consents = sorted(self._consents.pop(user_id, {}).keys())
        deleted_data = self._user_data.pop(user_id, {})
        return {
            "user_id": user_id,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "consents_removed": deleted_consents,
            "data_categories_removed": {
                category: len(items) for category, items in deleted_data.items()
            },
            "total_items_deleted": sum(len(v) for v in deleted_data.values()),
        }


class DataRetentionPolicy:
    """Retention helpers: expire stale records and split archives."""

    def check_retention(self, records: list[dict], max_age_days: float) -> list[dict]:
        """Return records older than ``max_age_days`` (candidates for deletion)."""
        now = datetime.now(timezone.utc)
        expired = []
        for record in records:
            age = _record_age_days(record, now)
            if age is not None and age > max_age_days:
                expired.append(record)
        return expired

    def archive_old_data(
        self, records: list[dict], archive_age_days: float
    ) -> tuple[list[dict], list[dict]]:
        """Split records into ``(active, archived)`` by age threshold."""
        now = datetime.now(timezone.utc)
        active: list[dict] = []
        archived: list[dict] = []
        for record in records:
            age = _record_age_days(record, now)
            if age is not None and age > archive_age_days:
                archived.append(record)
            else:
                active.append(record)
        return active, archived


__all__ = ["DataAnonymizer", "ConsentManager", "DataRetentionPolicy"]
