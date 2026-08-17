from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.platform_admin import PlatformAdminGrant
from app.models.user import User
from tests.conftest import CAPTURED_INVITATION_TOKENS


def register(client: TestClient, email: str, password: str = "Password123"):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Ada",
            "last_name": "Lovelace",
        },
    )


def login(client: TestClient, email: str, password: str = "Password123"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_org(client: TestClient, email: str, name: str, slug: str) -> tuple[str, dict]:
    register(client, email)
    token = login(client, email).json()["access_token"]
    created = client.post(
        "/api/v1/organizations",
        headers=auth_header(token),
        json={"name": name, "slug": slug},
    )
    token = login(client, email).json()["access_token"]
    return token, created.json()


def grant_platform_admin(db: Session, email: str) -> None:
    user = db.query(User).filter(User.email == email).one()
    db.add(PlatformAdminGrant(user_id=user.id))
    db.commit()


def test_create_organization_and_duplicate_slug(client: TestClient) -> None:
    token_a, org_a = create_org(client, "a@example.com", "ABC Express", "abc-express")
    assert org_a["slug"] == "abc-express"
    mine = client.get("/api/v1/organizations/me", headers=auth_header(token_a))
    assert mine.status_code == 200
    assert mine.json()["id"] == org_a["id"]

    token_b, _ = create_org(client, "b-setup@example.com", "Other Co", "other-co")
    duplicate = client.post(
        "/api/v1/organizations",
        headers=auth_header(login(client, "b-setup@example.com").json()["access_token"]),
        json={"name": "Copy", "slug": "abc-express"},
    )
    # b-setup already has an org, so this hits duplicate membership first.
    assert duplicate.status_code == 409

    register(client, "fresh-slug@example.com")
    token_fresh = login(client, "fresh-slug@example.com").json()["access_token"]
    clash = client.post(
        "/api/v1/organizations",
        headers=auth_header(token_fresh),
        json={"name": "Copycat", "slug": "abc-express"},
    )
    assert clash.status_code == 409
    assert clash.json()["error"]["code"] == "DUPLICATE_ORGANIZATION_SLUG"


def test_reserved_slug_rejected(client: TestClient) -> None:
    register(client, "reserved@example.com")
    token = login(client, "reserved@example.com").json()["access_token"]
    response = client.post(
        "/api/v1/organizations",
        headers=auth_header(token),
        json={"name": "Admin Corp", "slug": "admin"},
    )
    assert response.status_code == 422


def test_tenant_admin_cannot_access_another_organization(client: TestClient) -> None:
    token_a, org_a = create_org(client, "admin-a@example.com", "Company A", "company-a")
    token_b, org_b = create_org(client, "admin-b@example.com", "Company B", "company-b")

    assert client.get("/api/v1/organizations/me", headers=auth_header(token_a)).json()["id"] == org_a["id"]
    cross = client.get(
        "/api/v1/organizations/me",
        headers={**auth_header(token_a), "X-Organization-Id": org_b["id"]},
    )
    assert cross.status_code == 403
    patched = client.patch(
        "/api/v1/organizations/me",
        headers={**auth_header(token_a), "X-Organization-Id": org_b["id"]},
        json={"name": "Hijack"},
    )
    assert patched.status_code == 403
    assert client.get("/api/v1/organizations/me", headers=auth_header(token_b)).json()["name"] == "Company B"


def test_member_list_is_tenant_scoped(client: TestClient) -> None:
    token_a, org_a = create_org(client, "list-a@example.com", "Org A", "org-a-list")
    token_b, org_b = create_org(client, "list-b@example.com", "Org B", "org-b-list")

    members_a = client.get("/api/v1/organizations/me/members", headers=auth_header(token_a))
    assert members_a.status_code == 200
    assert len(members_a.json()) == 1
    assert members_a.json()[0]["email"] == "list-a@example.com"

    cross = client.get(
        "/api/v1/organizations/me/members",
        headers={**auth_header(token_a), "X-Organization-Id": org_b["id"]},
    )
    assert cross.status_code == 403

    members_b = client.get("/api/v1/organizations/me/members", headers=auth_header(token_b))
    member_id_b = members_b.json()[0]["id"]
    stolen = client.patch(
        f"/api/v1/organizations/me/members/{member_id_b}",
        headers=auth_header(token_a),
        json={"role_code": "STAFF"},
    )
    assert stolen.status_code == 404
    removed = client.delete(
        f"/api/v1/organizations/me/members/{member_id_b}",
        headers=auth_header(token_a),
    )
    assert removed.status_code == 404


def test_invite_accept_duplicate_and_role_rules(client: TestClient) -> None:
    token_a, _ = create_org(client, "owner@example.com", "Invite Co", "invite-co")
    register(client, "staff@example.com")

    invited = client.post(
        "/api/v1/organizations/me/members",
        headers=auth_header(token_a),
        json={"email": "staff@example.com", "role_code": "STAFF"},
    )
    assert invited.status_code == 201
    assert "token" not in invited.json()
    assert "token_hash" not in invited.json()
    token_value = CAPTURED_INVITATION_TOKENS[-1]

    duplicate = client.post(
        "/api/v1/organizations/me/members",
        headers=auth_header(token_a),
        json={"email": "STAFF@example.com", "role_code": "STAFF"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_INVITATION"

    forbidden_role = client.post(
        "/api/v1/organizations/me/members",
        headers=auth_header(token_a),
        json={"email": "other@example.com", "role_code": "PLATFORM_SUPER_ADMIN"},
    )
    assert forbidden_role.status_code == 400
    assert forbidden_role.json()["error"]["code"] == "INVALID_ROLE"

    listed = client.get("/api/v1/organizations/me/invitations", headers=auth_header(token_a))
    assert listed.status_code == 200
    assert listed.json()[0]["email"] == "staff@example.com"
    assert "token" not in listed.json()[0]

    staff_token = login(client, "staff@example.com").json()["access_token"]
    accepted = client.post(
        "/api/v1/invitations/accept",
        headers=auth_header(staff_token),
        json={"token": token_value},
    )
    assert accepted.status_code == 200
    assert accepted.json()["role_code"] == "STAFF"
    assert accepted.json()["status"] == "ACTIVE"


def test_member_role_status_and_removal(client: TestClient) -> None:
    token_a, _ = create_org(client, "mgr@example.com", "People Co", "people-co")
    register(client, "worker@example.com")
    invite = client.post(
        "/api/v1/organizations/me/members",
        headers=auth_header(token_a),
        json={"email": "worker@example.com", "role_code": "STAFF"},
    ).json()
    worker_token = login(client, "worker@example.com").json()["access_token"]
    client.post(
        "/api/v1/invitations/accept",
        headers=auth_header(worker_token),
        json={"token": CAPTURED_INVITATION_TOKENS[-1]},
    )
    members = client.get("/api/v1/organizations/me/members", headers=auth_header(token_a)).json()
    worker = next(item for item in members if item["email"] == "worker@example.com")

    platform = client.patch(
        f"/api/v1/organizations/me/members/{worker['id']}",
        headers=auth_header(token_a),
        json={"role_code": "PLATFORM_SUPER_ADMIN"},
    )
    assert platform.status_code == 400

    changed = client.patch(
        f"/api/v1/organizations/me/members/{worker['id']}",
        headers=auth_header(token_a),
        json={"role_code": "OPERATIONS_MANAGER"},
    )
    assert changed.status_code == 200
    assert changed.json()["role_code"] == "OPERATIONS_MANAGER"

    suspended = client.patch(
        f"/api/v1/organizations/me/members/{worker['id']}",
        headers=auth_header(token_a),
        json={"status": "SUSPENDED"},
    )
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "SUSPENDED"
    blocked = client.get("/api/v1/organizations/me", headers=auth_header(worker_token))
    assert blocked.status_code == 403

    reactivated = client.patch(
        f"/api/v1/organizations/me/members/{worker['id']}",
        headers=auth_header(token_a),
        json={"status": "ACTIVE"},
    )
    assert reactivated.json()["status"] == "ACTIVE"

    removed = client.delete(
        f"/api/v1/organizations/me/members/{worker['id']}",
        headers=auth_header(token_a),
    )
    assert removed.status_code == 204
    remaining = client.get("/api/v1/organizations/me/members", headers=auth_header(token_a)).json()
    assert all(item["email"] != "worker@example.com" for item in remaining)


def test_multi_organization_user_list_and_switch(client: TestClient) -> None:
    token_a, org_a = create_org(client, "multi-a@example.com", "Company A", "multi-company-a")
    token_b, org_b = create_org(client, "multi-b@example.com", "Company B", "multi-company-b")

    invite = client.post(
        "/api/v1/organizations/me/members",
        headers=auth_header(token_a),
        json={"email": "multi-b@example.com", "role_code": "STAFF"},
    ).json()
    client.post(
        "/api/v1/invitations/accept",
        headers=auth_header(token_b),
        json={"token": CAPTURED_INVITATION_TOKENS[-1]},
    )

    orgs = client.get("/api/v1/auth/organizations", headers=auth_header(token_b))
    assert orgs.status_code == 200
    slugs = {item["slug"] for item in orgs.json()}
    assert slugs == {"multi-company-a", "multi-company-b"}
    assert all(item["id"] in {org_a["id"], org_b["id"]} for item in orgs.json())

    switched = client.post(
        "/api/v1/auth/switch-organization",
        headers=auth_header(token_b),
        json={"organization_id": org_a["id"]},
    )
    assert switched.status_code == 200
    token_switched = switched.json()["access_token"]
    current = client.get("/api/v1/organizations/me", headers=auth_header(token_switched))
    assert current.json()["id"] == org_a["id"]
    me = client.get("/api/v1/auth/me", headers=auth_header(token_switched))
    assert me.json()["current_organization_id"] == org_a["id"]

    denied = client.post(
        "/api/v1/auth/switch-organization",
        headers=auth_header(token_a),
        json={"organization_id": org_b["id"]},
    )
    assert denied.status_code == 403

    unknown = client.post(
        "/api/v1/auth/switch-organization",
        headers=auth_header(token_a),
        json={"organization_id": str(uuid4())},
    )
    assert unknown.status_code == 403


def test_platform_super_admin_org_lifecycle(client: TestClient, db: Session) -> None:
    token_a, org_a = create_org(client, "tenant@example.com", "Tenant Co", "tenant-co")
    register(client, "platform@example.com")
    grant_platform_admin(db, "platform@example.com")
    platform_token = login(client, "platform@example.com").json()["access_token"]

    listed = client.get("/api/v1/platform/organizations", headers=auth_header(platform_token))
    assert listed.status_code == 200
    assert any(item["id"] == org_a["id"] for item in listed.json())

    detail = client.get(
        f"/api/v1/platform/organizations/{org_a['id']}",
        headers=auth_header(platform_token),
    )
    assert detail.status_code == 200

    tenant_suspend = client.post(
        f"/api/v1/platform/organizations/{org_a['id']}/suspend",
        headers=auth_header(token_a),
    )
    assert tenant_suspend.status_code == 403

    suspended = client.post(
        f"/api/v1/platform/organizations/{org_a['id']}/suspend",
        headers=auth_header(platform_token),
    )
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "SUSPENDED"

    blocked = client.get("/api/v1/organizations/me", headers=auth_header(token_a))
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "ORGANIZATION_SUSPENDED"

    reactivated = client.post(
        f"/api/v1/platform/organizations/{org_a['id']}/reactivate",
        headers=auth_header(platform_token),
    )
    assert reactivated.json()["status"] == "ACTIVE"
    restored = client.get("/api/v1/organizations/me", headers=auth_header(token_a))
    assert restored.status_code == 200


def test_audit_log_for_organization_actions(client: TestClient, db: Session) -> None:
    token_a, org_a = create_org(client, "audit@example.com", "Audit Co", "audit-co")
    created_logs = (
        db.query(AuditLog)
        .filter(AuditLog.action == "ORGANIZATION_CREATED", AuditLog.organization_id == org_a["id"])
        .all()
    )
    assert created_logs

    client.patch(
        "/api/v1/organizations/me",
        headers=auth_header(token_a),
        json={"name": "Audit Company"},
    )
    assert db.query(AuditLog).filter(AuditLog.action == "ORGANIZATION_UPDATED").count() >= 1

    register(client, "audit-staff@example.com")
    invite = client.post(
        "/api/v1/organizations/me/members",
        headers=auth_header(token_a),
        json={"email": "audit-staff@example.com", "role_code": "STAFF"},
    ).json()
    assert db.query(AuditLog).filter(AuditLog.action == "MEMBER_INVITED").count() >= 1

    staff_token = login(client, "audit-staff@example.com").json()["access_token"]
    client.post(
        "/api/v1/invitations/accept",
        headers=auth_header(staff_token),
        json={"token": CAPTURED_INVITATION_TOKENS[-1]},
    )
    members = client.get("/api/v1/organizations/me/members", headers=auth_header(token_a)).json()
    staff = next(item for item in members if item["email"] == "audit-staff@example.com")
    client.patch(
        f"/api/v1/organizations/me/members/{staff['id']}",
        headers=auth_header(token_a),
        json={"role_code": "CUSTOMER", "status": "SUSPENDED"},
    )
    assert db.query(AuditLog).filter(AuditLog.action == "MEMBER_ROLE_CHANGED").count() >= 1
    assert db.query(AuditLog).filter(AuditLog.action == "MEMBER_SUSPENDED").count() >= 1

    client.delete(
        f"/api/v1/organizations/me/members/{staff['id']}",
        headers=auth_header(token_a),
    )
    assert db.query(AuditLog).filter(AuditLog.action == "MEMBER_REMOVED").count() >= 1

    register(client, "audit-platform@example.com")
    grant_platform_admin(db, "audit-platform@example.com")
    platform_token = login(client, "audit-platform@example.com").json()["access_token"]
    client.post(
        f"/api/v1/platform/organizations/{org_a['id']}/suspend",
        headers=auth_header(platform_token),
    )
    client.post(
        f"/api/v1/platform/organizations/{org_a['id']}/reactivate",
        headers=auth_header(platform_token),
    )
    assert db.query(AuditLog).filter(AuditLog.action == "ORGANIZATION_SUSPENDED").count() >= 1
    assert db.query(AuditLog).filter(AuditLog.action == "ORGANIZATION_REACTIVATED").count() >= 1
