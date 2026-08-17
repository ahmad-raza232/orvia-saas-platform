from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.models.audit_log import AuditLog
from app.models.organization import Organization, OrganizationStatus
from tests.test_auth_and_organizations import auth_header, login, register
from tests.conftest import CAPTURED_INVITATION_TOKENS
from tests.test_shipments import create_org


def test_health_and_ready(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ok"}


def test_login_and_switch_are_audited_without_secrets(client: TestClient, db: Session) -> None:
    register(client, "audit-login@example.com")
    failed = login(client, "audit-login@example.com", "not-the-password")
    assert failed.status_code == 401
    failed_row = db.query(AuditLog).filter(AuditLog.action == "LOGIN_FAILED").one()
    assert failed_row.details["email"] == "audit-login@example.com"
    assert "password" not in str(failed_row.details).lower()
    assert "token" not in str(failed_row.details).lower()

    ok = login(client, "audit-login@example.com")
    assert ok.status_code == 200
    success = db.query(AuditLog).filter(AuditLog.action == "LOGIN_SUCCEEDED").one()
    assert success.actor_user_id is not None
    assert "password" not in str(success.details).lower()
    assert ok.json()["access_token"] not in str(success.details)


def test_jwt_rejects_missing_exp_and_wrong_typ(client: TestClient) -> None:
    register(client, "jwt-typ@example.com")
    token = login(client, "jwt-typ@example.com").json()["access_token"]
    me = client.get("/api/v1/auth/me", headers=auth_header(token))
    assert me.status_code == 200
    user_id = me.json()["user"]["id"]
    now = datetime.now(timezone.utc)
    missing_exp = jwt.encode(
        {"sub": user_id, "iat": now, "typ": "access"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    assert client.get("/api/v1/auth/me", headers=auth_header(missing_exp)).status_code == 401
    refresh = jwt.encode(
        {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "typ": "refresh",
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    assert client.get("/api/v1/auth/me", headers=auth_header(refresh)).status_code == 401
    expired = jwt.encode(
        {
            "sub": user_id,
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
            "typ": "access",
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    assert client.get("/api/v1/auth/me", headers=auth_header(expired)).status_code == 401
    malformed_sub = jwt.encode(
        {
            "sub": "not-a-uuid",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "typ": "access",
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    bad_sub = client.get("/api/v1/auth/me", headers=auth_header(malformed_sub))
    assert bad_sub.status_code == 401
    assert bad_sub.json()["error"]["code"] == "INVALID_TOKEN"


def test_cannot_accept_invitation_for_suspended_organization(
    client: TestClient, db: Session
) -> None:
    token_a, org = create_org(
        client, "invite-suspend@example.com", "Suspend Invite", "suspend-invite"
    )
    register(client, "invitee-suspend@example.com")
    invited = client.post(
        "/api/v1/organizations/me/members",
        headers=auth_header(token_a),
        json={"email": "invitee-suspend@example.com", "role_code": "STAFF"},
    )
    assert invited.status_code == 201
    assert "token" not in invited.json()
    raw = CAPTURED_INVITATION_TOKENS[-1]
    row = db.get(Organization, org["id"])
    assert row is not None
    row.status = OrganizationStatus.SUSPENDED
    db.commit()
    invitee = login(client, "invitee-suspend@example.com").json()["access_token"]
    accepted = client.post(
        "/api/v1/invitations/accept",
        headers=auth_header(invitee),
        json={"token": raw},
    )
    assert accepted.status_code == 403
    assert accepted.json()["error"]["code"] == "ORGANIZATION_SUSPENDED"


def test_organization_switch_is_audited(client: TestClient, db: Session) -> None:
    token, org = create_org(client, "switch-audit@example.com", "Switch Audit", "switch-audit")
    switched = client.post(
        "/api/v1/auth/switch-organization",
        headers=auth_header(token),
        json={"organization_id": org["id"]},
    )
    assert switched.status_code == 200
    row = (
        db.query(AuditLog)
        .filter(AuditLog.action == "ORGANIZATION_SWITCHED", AuditLog.organization_id == org["id"])
        .one()
    )
    assert row.details["slug"] == "switch-audit"
    assert switched.json()["access_token"] not in str(row.details)


def test_production_settings_reject_unsafe_defaults() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            app_env="production",
            database_url="postgresql+psycopg://orvia:orvia@localhost:5433/orvia",
            jwt_secret="change-me-to-a-long-random-secret",
            email_provider="logging",
            storage_provider="memory",
            debug=False,
        )
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            jwt_algorithm="none",
            database_url="postgresql+psycopg://orvia:orvia@localhost:5433/orvia",
            jwt_secret="dev-secret-not-used-in-prod-0001",
            app_env="development",
        )
    ok = Settings(
        _env_file=None,
        app_env="production",
        database_url="postgresql+psycopg://orvia:orvia@localhost:5433/orvia",
        jwt_secret="a-sufficiently-long-production-jwt-secret-value",
        email_provider="smtp",
        smtp_host="smtp.example.com",
        smtp_from_email="noreply@example.com",
        storage_provider="s3",
        s3_bucket="orvia-pod",
        s3_access_key_id="AKIATEST",
        s3_secret_access_key="storage-secret-not-a-real-key",
        debug=False,
        cors_origins="https://app.example.com",
    )
    assert ok.is_production is True
    assert "s3_secret_access_key" not in repr(ok)
    assert "jwt_secret" not in repr(ok).lower() or ok.jwt_secret not in repr(ok)

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            app_env="production",
            database_url="postgresql+psycopg://orvia:orvia@localhost:5433/orvia",
            jwt_secret="a-sufficiently-long-production-jwt-secret-value",
            email_provider="smtp",
            smtp_host="smtp.example.com",
            smtp_from_email="noreply@example.com",
            storage_provider="s3",
            s3_bucket="orvia-pod",
            s3_access_key_id="AKIATEST",
            s3_secret_access_key="storage-secret-not-a-real-key",
            debug=False,
            cors_origins="*",
        )
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            app_env="production",
            database_url="postgresql+psycopg://orvia:orvia@localhost:5433/orvia",
            jwt_secret="a-sufficiently-long-production-jwt-secret-value",
            email_provider="smtp",
            smtp_host="smtp.example.com",
            smtp_from_email="noreply@example.com",
            storage_provider="memory",
            s3_bucket="orvia-pod",
            s3_access_key_id="AKIATEST",
            s3_secret_access_key="storage-secret-not-a-real-key",
            debug=False,
        )
