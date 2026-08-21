"""Unit tests for security: JWT auth, password hashing, privacy, RBAC."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import HTTPException


class TestTokenAuth:
    def test_create_and_verify_roundtrip(self):
        from app.auth import create_access_token, verify_token

        token = create_access_token({"sub": "user-123", "role": "user"})
        payload = verify_token(token)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "user"
        assert payload["type"] == "access"

    def test_expired_token_rejected(self):
        from app.auth import create_access_token, verify_token

        token = create_access_token({"sub": "u1"}, expires_delta=timedelta(seconds=-30))
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401

    def test_garbage_token_rejected(self):
        from app.auth import verify_token

        with pytest.raises(HTTPException) as exc_info:
            verify_token("not.a.jwt")
        assert exc_info.value.status_code == 401

    def test_wrong_token_type_rejected(self):
        from app.auth import create_access_token, create_refresh_token, verify_token

        refresh = create_refresh_token({"sub": "u1"})
        with pytest.raises(HTTPException):
            verify_token(refresh, expected_type="access")
        payload = verify_token(refresh, expected_type="refresh")
        assert payload["type"] == "refresh"

    def test_tampered_signature_rejected(self):
        from app.auth import create_access_token, verify_token

        token = create_access_token({"sub": "u1"})
        header, body, signature = token.split(".")
        with pytest.raises(HTTPException):
            verify_token(f"{header}.{body}.AAAA{signature[4:]}")


class TestPasswordHashing:
    def test_hash_and_verify(self):
        from app.auth import hash_password, verify_password

        hashed = hash_password("S3cure-Passw0rd!")
        assert hashed != "S3cure-Passw0rd!"
        assert verify_password(hashed, "S3cure-Passw0rd!")

    def test_wrong_password_fails(self):
        from app.auth import hash_password, verify_password

        hashed = hash_password("correct-horse")
        assert not verify_password(hashed, "wrong-battery")

    def test_hashes_are_salted_and_unique(self):
        from app.auth import hash_password

        assert hash_password("same-input") != hash_password("same-input")

    def test_malformed_hash_returns_false(self):
        from app.auth import verify_password

        assert not verify_password("not-a-valid-hash", "anything")


class TestDataAnonymizer:
    def test_anonymize_user_hides_identifiers(self):
        from app.core.privacy import DataAnonymizer

        anonymizer = DataAnonymizer(salt="test-salt")
        result = anonymizer.anonymize_user(
            {"email": "jane@example.com", "user_id": 42, "rating": 4.5}
        )
        assert result["email"] != "jane@example.com"
        assert result["user_id"] != 42
        assert len(str(result["user_id"])) == 12
        assert result["rating"] == 4.5

    def test_anonymization_is_deterministic_with_same_salt(self):
        from app.core.privacy import DataAnonymizer

        first = DataAnonymizer(salt="s").anonymize_user({"email": "a@b.c"})
        second = DataAnonymizer(salt="s").anonymize_user({"email": "a@b.c"})
        assert first["email"] == second["email"]

    def test_pseudonymize_preserves_joins(self):
        from app.core.privacy import DataAnonymizer

        records = [{"user_id": "u1"}, {"user_id": "u2"}, {"user_id": "u1"}]
        pseudonymous = DataAnonymizer().pseudonymize(records, ["user_id"])
        assert pseudonymous[0]["user_id"] == pseudonymous[2]["user_id"]
        assert pseudonymous[0]["user_id"] != pseudonymous[1]["user_id"]
        assert all(r["user_id"] != original for r, original in zip(pseudonymous, ["u1", "u2", "u1"]))

    def test_k_anonymity_suppresses_small_groups(self):
        from app.core.privacy import DataAnonymizer

        records = [
            {"zip": "11111", "age": 30},
            {"zip": "11111", "age": 31},
            {"zip": "22222", "age": 40},
        ]
        anonymized = DataAnonymizer().k_anonymize(records, ["zip"], k=2)
        assert anonymized[2]["zip"] is None
        assert anonymized[0]["zip"] == "11111"


class TestConsentManager:
    def test_consent_lifecycle(self):
        from app.core.privacy import ConsentManager

        manager = ConsentManager()
        manager.record_consent("u1", "analytics", granted=True)
        assert manager.check_consent("u1", "analytics")
        manager.record_consent("u1", "analytics", granted=False)
        assert not manager.check_consent("u1", "analytics")

    def test_unknown_consent_defaults_to_false(self):
        from app.core.privacy import ConsentManager

        manager = ConsentManager()
        assert not manager.check_consent("nobody", "marketing")

    def test_invalid_consent_type_raises(self):
        from app.core.privacy import ConsentManager

        manager = ConsentManager()
        with pytest.raises(ValueError):
            manager.record_consent("u1", "telepathy", granted=True)

    def test_delete_user_data_report(self):
        from app.core.privacy import ConsentManager

        manager = ConsentManager()
        manager.record_consent("u1", "personalization", granted=True)
        manager.register_data("u1", "ratings", [1, 2, 3])
        report = manager.delete_user_data("u1")
        assert report["total_items_deleted"] == 3
        assert "personalization" in report["consents_removed"]
        assert not manager.check_consent("u1", "personalization")


class TestRBAC:
    def test_admin_has_all_permissions(self):
        from app.auth.models import UserRole
        from app.middleware.rbac import Permission, get_role_permissions

        permissions = get_role_permissions(UserRole.ADMIN)
        assert permissions == frozenset(Permission)

    def test_user_cannot_admin_or_moderate(self):
        from app.auth.models import UserRole
        from app.middleware.rbac import Permission, get_role_permissions

        permissions = get_role_permissions(UserRole.USER)
        assert Permission.ADMIN not in permissions
        assert Permission.MODERATE not in permissions
        assert {Permission.READ, Permission.WRITE} <= permissions

    def test_moderator_can_moderate_but_not_admin(self):
        from app.auth.models import UserRole
        from app.middleware.rbac import Permission, get_role_permissions

        permissions = get_role_permissions(UserRole.MODERATOR)
        assert Permission.MODERATE in permissions
        assert Permission.ADMIN not in permissions

    def test_unknown_role_yields_no_permissions(self):
        from app.middleware.rbac import get_role_permissions

        assert get_role_permissions("ghost") == frozenset()

    def test_require_role_factory_returns_callable(self):
        from app.auth.models import UserRole
        from app.middleware.rbac import require_role

        checker = require_role(UserRole.ADMIN)
        assert callable(checker)
