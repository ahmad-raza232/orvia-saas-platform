from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.invitation import InvitationStatus, OrganizationInvitation
from app.models.login_attempt import LoginAttemptWindow
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.login_rate_limiter import _key_hash
from tests.conftest import CAPTURED_INVITATION_TOKENS
from tests.test_auth_and_organizations import auth_header, login, register
from tests.test_shipments import create_org


def test_login_rate_limit_locks_after_failed_attempts(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "auth_login_rate_limit_max_attempts", 3)
    monkeypatch.setattr(settings, "auth_login_rate_limit_window_seconds", 120)
    register(client, "limit-user@example.com")
    unknown_body = {"email": "nobody-limit@example.com", "password": "wrong-password"}
    known_body = {"email": "limit-user@example.com", "password": "wrong-password"}

    first_unknown = client.post("/api/v1/auth/login", json=unknown_body)
    first_known = client.post("/api/v1/auth/login", json=known_body)
    assert first_unknown.status_code == 401
    assert first_known.status_code == 401
    assert first_unknown.json()["error"]["code"] == first_known.json()["error"]["code"]
    assert "wrong-password" not in first_known.text

    client.post("/api/v1/auth/login", json=known_body)
    locked = client.post("/api/v1/auth/login", json=known_body)
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "TOO_MANY_REQUESTS"
    assert locked.headers.get("retry-after")
    assert "exists" not in locked.text.lower()

    bypass = client.post(
        "/api/v1/auth/login",
        json={"email": "limit-user@example.com", "password": "Password123"},
        headers={"X-Organization-Id": str(uuid4())},
    )
    assert bypass.status_code == 429

    still_unknown = client.post("/api/v1/auth/login", json=unknown_body)
    assert still_unknown.status_code in {401, 429}


def test_successful_login_resets_rate_limit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "auth_login_rate_limit_max_attempts", 3)
    register(client, "reset-limit@example.com")
    wrong = {"email": "reset-limit@example.com", "password": "not-it"}
    assert client.post("/api/v1/auth/login", json=wrong).status_code == 401
    assert client.post("/api/v1/auth/login", json=wrong).status_code == 401
    ok = login(client, "reset-limit@example.com")
    assert ok.status_code == 200
    assert client.post("/api/v1/auth/login", json=wrong).status_code == 401


def test_rate_limit_window_expiration_resets_counter(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "auth_login_rate_limit_max_attempts", 3)
    monkeypatch.setattr(settings, "auth_login_rate_limit_window_seconds", 60)
    email = "window-limit@example.com"
    register(client, email)
    now = datetime.now(timezone.utc)
    db.add(
        LoginAttemptWindow(
            key_hash=_key_hash(email),
            failed_count=5,
            window_started_at=now - timedelta(minutes=10),
            locked_until=now - timedelta(minutes=1),
        )
    )
    db.commit()
    failed = login(client, email, "wrong-password")
    assert failed.status_code == 401
    ok = login(client, email)
    assert ok.status_code == 200


def test_jwt_claim_and_algorithm_rejections(client: TestClient) -> None:
    register(client, "jwt-more@example.com")
    token = login(client, "jwt-more@example.com").json()["access_token"]
    user_id = client.get("/api/v1/auth/me", headers=auth_header(token)).json()["user"]["id"]
    now = datetime.now(timezone.utc)
    base = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "typ": "access",
    }
    missing_sub = jwt.encode(
        {"iat": now, "exp": now + timedelta(minutes=5), "typ": "access"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    assert client.get("/api/v1/auth/me", headers=auth_header(missing_sub)).status_code == 401

    bad_sig = jwt.encode(base, "other-secret-not-the-configured-one", algorithm=settings.jwt_algorithm)
    assert client.get("/api/v1/auth/me", headers=auth_header(bad_sig)).status_code == 401

    hs384 = jwt.encode(base, settings.jwt_secret, algorithm="HS384")
    assert client.get("/api/v1/auth/me", headers=auth_header(hs384)).status_code == 401

    none_token = jwt.encode(base, key=None, algorithm="none")
    assert client.get("/api/v1/auth/me", headers=auth_header(none_token)).status_code == 401

    future_iat = jwt.encode(
        {
            "sub": user_id,
            "iat": now + timedelta(hours=2),
            "exp": now + timedelta(hours=3),
            "typ": "access",
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    assert client.get("/api/v1/auth/me", headers=auth_header(future_iat)).status_code == 401
    assert client.get("/api/v1/auth/me", headers=auth_header(token)).status_code == 200


def test_invitation_token_not_in_response_or_logs(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    token_a, _ = create_org(client, "invite-hide@example.com", "Hide Invite", "hide-invite")
    register(client, "invitee-hide@example.com")
    with caplog.at_level("INFO"):
        invited = client.post(
            "/api/v1/organizations/me/members",
            headers=auth_header(token_a),
            json={"email": "invitee-hide@example.com", "role_code": "STAFF"},
        )
    assert invited.status_code == 201
    body = invited.json()
    raw = CAPTURED_INVITATION_TOKENS[-1]
    assert "token" not in body
    assert raw not in invited.text
    assert raw not in caplog.text
    listed = client.get("/api/v1/organizations/me/invitations", headers=auth_header(token_a))
    assert raw not in listed.text
    invitee = login(client, "invitee-hide@example.com").json()["access_token"]
    accepted = client.post(
        "/api/v1/invitations/accept",
        headers=auth_header(invitee),
        json={"token": raw},
    )
    assert accepted.status_code == 200
    reused = client.post(
        "/api/v1/invitations/accept",
        headers=auth_header(invitee),
        json={"token": raw},
    )
    assert reused.status_code == 400


def test_expired_and_cross_tenant_invitation(
    client: TestClient, db: Session
) -> None:
    token_a, _ = create_org(client, "invite-exp@example.com", "Exp Invite", "exp-invite")
    token_b, _ = create_org(client, "invite-other@example.com", "Other Invite", "other-invite")
    register(client, "invitee-exp@example.com")
    invited = client.post(
        "/api/v1/organizations/me/members",
        headers=auth_header(token_a),
        json={"email": "invitee-exp@example.com", "role_code": "STAFF"},
    )
    assert invited.status_code == 201
    raw = CAPTURED_INVITATION_TOKENS[-1]
    row = db.query(OrganizationInvitation).one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    invitee = login(client, "invitee-exp@example.com").json()["access_token"]
    expired = client.post(
        "/api/v1/invitations/accept",
        headers=auth_header(invitee),
        json={"token": raw},
    )
    assert expired.status_code == 410

    register(client, "stranger-invite@example.com")
    second = client.post(
        "/api/v1/organizations/me/members",
        headers=auth_header(token_a),
        json={"email": "stranger-invite@example.com", "role_code": "STAFF"},
    )
    assert second.status_code == 201
    stolen = CAPTURED_INVITATION_TOKENS[-1]
    cross = client.post(
        "/api/v1/invitations/accept",
        headers=auth_header(token_b),
        json={"token": stolen},
    )
    assert cross.status_code == 400


def test_new_password_minimum_does_not_break_existing_hashes(
    client: TestClient, db: Session
) -> None:
    short = client.post(
        "/api/v1/auth/register",
        json={
            "email": "short-pass@example.com",
            "password": "Pass1234",
            "first_name": "Short",
            "last_name": "Pass",
        },
    )
    assert short.status_code == 422
    user = User(
        email="legacy-pass@example.com",
        password_hash=hash_password("Pass1234"),
        first_name="Legacy",
        last_name="User",
    )
    db.add(user)
    db.commit()
    ok = login(client, "legacy-pass@example.com", "Pass1234")
    assert ok.status_code == 200


def test_member_list_page_size_is_bounded(client: TestClient) -> None:
    token, _ = create_org(client, "page-admin@example.com", "Page Co", "page-co")
    oversized = client.get(
        "/api/v1/organizations/me/members",
        headers=auth_header(token),
        params={"page_size": 101},
    )
    assert oversized.status_code == 422
    invalid = client.get(
        "/api/v1/organizations/me/members",
        headers=auth_header(token),
        params={"page": 0},
    )
    assert invalid.status_code == 422
    ok = client.get(
        "/api/v1/organizations/me/members",
        headers=auth_header(token),
        params={"page": 1, "page_size": 100},
    )
    assert ok.status_code == 200
    assert isinstance(ok.json(), list)


def test_ready_does_not_leak_database_details(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class Boom:
        def connect(self):
            raise RuntimeError("postgresql+psycopg://orvia:orvia@localhost:5433/orvia")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("app.main.engine", Boom())
    ready = client.get("/ready")
    assert ready.status_code == 503
    assert ready.json() == {"status": "unavailable"}
    assert "orvia:orvia" not in ready.text
    assert "postgresql" not in ready.text
    health = client.get("/health")
    assert health.status_code == 200


def test_audit_records_are_organization_scoped(client: TestClient, db: Session) -> None:
    token_a, org_a = create_org(client, "audit-a@example.com", "Audit A", "audit-a-org")
    _token_b, org_b = create_org(client, "audit-b@example.com", "Audit B", "audit-b-org")
    org_a_id = UUID(org_a["id"])
    org_b_id = UUID(org_b["id"])
    row_b = (
        db.query(AuditLog)
        .filter(AuditLog.organization_id == org_b_id, AuditLog.action == "ORGANIZATION_CREATED")
        .one()
    )
    service = AuditService(db)
    assert service.get_for_organization(row_b.id, org_a_id) is None
    assert service.get_for_organization(row_b.id, org_b_id) is not None
    leaked = service.list_for_organization(org_a_id)
    assert all(item.organization_id == org_a_id for item in leaked)
    assert all(item.id != row_b.id for item in leaked)


def test_logout_is_stateless_and_token_still_works(client: TestClient) -> None:
    register(client, "logout-user@example.com")
    token = login(client, "logout-user@example.com").json()["access_token"]
    gone = client.post("/api/v1/auth/logout", headers=auth_header(token))
    assert gone.status_code == 204
    still = client.get("/api/v1/auth/me", headers=auth_header(token))
    assert still.status_code == 200


def test_development_settings_remain_usable() -> None:
    dev = Settings(
        _env_file=None,
        app_env="development",
        database_url="postgresql+psycopg://orvia:orvia@localhost:5433/orvia",
        jwt_secret="dev-secret-not-used-in-prod-0001",
        email_provider="logging",
        storage_provider="memory",
        debug=True,
    )
    assert dev.is_production is False
