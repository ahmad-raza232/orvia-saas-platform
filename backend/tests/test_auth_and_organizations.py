from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.membership import MembershipStatus, OrganizationMembership
from app.models.role import CUSTOMER, Role


def register(client: TestClient, email: str, password: str = "Password123") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Ada",
            "last_name": "Lovelace",
            "phone": "+10000000000",
        },
    )
    return response


def login(client: TestClient, email: str, password: str = "Password123") -> dict:
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_user_registration(client: TestClient) -> None:
    response = register(client, "Ada@Example.com")
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ada@example.com"
    assert "password" not in body
    assert "password_hash" not in body


def test_duplicate_email(client: TestClient) -> None:
    assert register(client, "dup@example.com").status_code == 201
    response = register(client, "DUP@example.com")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_EMAIL"


def test_login_success(client: TestClient) -> None:
    register(client, "login@example.com")
    response = login(client, "login@example.com")
    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"


def test_invalid_login(client: TestClient) -> None:
    register(client, "wrongpass@example.com")
    response = login(client, "wrongpass@example.com", "not-the-password")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_authenticated_me(client: TestClient) -> None:
    register(client, "me@example.com")
    token = login(client, "me@example.com").json()["access_token"]
    response = client.get("/api/v1/auth/me", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "me@example.com"
    assert response.json()["memberships"] == []


def test_unauthorized_request(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_invalid_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers=auth_header("not-a-valid-token"))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_logout(client: TestClient) -> None:
    register(client, "logout@example.com")
    token = login(client, "logout@example.com").json()["access_token"]
    response = client.post("/api/v1/auth/logout", headers=auth_header(token))
    assert response.status_code == 204


def test_organization_creation_and_retrieval(client: TestClient) -> None:
    register(client, "owner@example.com")
    token = login(client, "owner@example.com").json()["access_token"]
    created = client.post(
        "/api/v1/organizations",
        headers=auth_header(token),
        json={"name": "Northwind Logistics", "slug": "northwind"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Northwind Logistics"
    assert body["slug"] == "northwind"
    assert body["status"] == "ACTIVE"

    token = login(client, "owner@example.com").json()["access_token"]
    fetched = client.get("/api/v1/organizations/me", headers=auth_header(token))
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]
    assert fetched.json()["slug"] == "northwind"

    me = client.get("/api/v1/auth/me", headers=auth_header(token))
    assert me.json()["memberships"][0]["role_code"] == "TENANT_ADMIN"


def test_organization_update(client: TestClient) -> None:
    register(client, "update@example.com")
    token = login(client, "update@example.com").json()["access_token"]
    client.post(
        "/api/v1/organizations",
        headers=auth_header(token),
        json={"name": "Old Name", "slug": "old-name"},
    )
    token = login(client, "update@example.com").json()["access_token"]
    updated = client.patch(
        "/api/v1/organizations/me",
        headers=auth_header(token),
        json={"name": "New Name"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "New Name"
    assert updated.json()["slug"] == "old-name"


def test_duplicate_organization_slug(client: TestClient) -> None:
    register(client, "slug-a@example.com")
    token_a = login(client, "slug-a@example.com").json()["access_token"]
    first = client.post(
        "/api/v1/organizations",
        headers=auth_header(token_a),
        json={"name": "Org A", "slug": "shared-slug"},
    )
    assert first.status_code == 201

    register(client, "slug-b@example.com")
    token_b = login(client, "slug-b@example.com").json()["access_token"]
    second = client.post(
        "/api/v1/organizations",
        headers=auth_header(token_b),
        json={"name": "Org B", "slug": "shared-slug"},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DUPLICATE_ORGANIZATION_SLUG"


def test_duplicate_membership(client: TestClient, db: Session) -> None:
    register(client, "member@example.com")
    token = login(client, "member@example.com").json()["access_token"]
    created = client.post(
        "/api/v1/organizations",
        headers=auth_header(token),
        json={"name": "Only One Org", "slug": "only-one"},
    )
    assert created.status_code == 201

    second = client.post(
        "/api/v1/organizations",
        headers=auth_header(token),
        json={"name": "Second Org", "slug": "second-org"},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DUPLICATE_MEMBERSHIP"

    from app.models.user import User

    user = db.query(User).filter(User.email == "member@example.com").one()
    role = db.query(Role).filter(Role.code == CUSTOMER).one()
    db.add(
        OrganizationMembership(
            user_id=user.id,
            organization_id=created.json()["id"],
            role_id=role.id,
            status=MembershipStatus.ACTIVE,
        )
    )
    try:
        db.commit()
        raise AssertionError("duplicate membership should be rejected")
    except IntegrityError:
        db.rollback()


def test_missing_organization_membership(client: TestClient) -> None:
    register(client, "nomember@example.com")
    token = login(client, "nomember@example.com").json()["access_token"]
    response = client.get("/api/v1/organizations/me", headers=auth_header(token))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "MISSING_ORGANIZATION_MEMBERSHIP"


def test_tenant_isolation(client: TestClient) -> None:
    register(client, "user-a@example.com")
    token_a = login(client, "user-a@example.com").json()["access_token"]
    org_a = client.post(
        "/api/v1/organizations",
        headers=auth_header(token_a),
        json={"name": "Organization A", "slug": "organization-a"},
    )
    assert org_a.status_code == 201

    register(client, "user-b@example.com")
    token_b = login(client, "user-b@example.com").json()["access_token"]
    org_b = client.post(
        "/api/v1/organizations",
        headers=auth_header(token_b),
        json={"name": "Organization B", "slug": "organization-b"},
    )
    assert org_b.status_code == 201

    token_a = login(client, "user-a@example.com").json()["access_token"]
    token_b = login(client, "user-b@example.com").json()["access_token"]

    mine = client.get("/api/v1/organizations/me", headers=auth_header(token_a))
    assert mine.status_code == 200
    assert mine.json()["id"] == org_a.json()["id"]
    assert mine.json()["slug"] != org_b.json()["slug"]

    cross = client.get(
        "/api/v1/organizations/me",
        headers={**auth_header(token_a), "X-Organization-Id": org_b.json()["id"]},
    )
    assert cross.status_code == 403

    patched = client.patch(
        "/api/v1/organizations/me",
        headers={**auth_header(token_a), "X-Organization-Id": org_b.json()["id"]},
        json={"name": "Hijacked"},
    )
    assert patched.status_code == 403

    still_b = client.get("/api/v1/organizations/me", headers=auth_header(token_b))
    assert still_b.json()["name"] == "Organization B"


def test_role_restrictions(client: TestClient, db: Session) -> None:
    register(client, "staffish@example.com")
    token = login(client, "staffish@example.com").json()["access_token"]
    created = client.post(
        "/api/v1/organizations",
        headers=auth_header(token),
        json={"name": "Restricted Org", "slug": "restricted-org"},
    )
    assert created.status_code == 201

    from app.models.user import User

    user = db.query(User).filter(User.email == "staffish@example.com").one()
    customer_role = db.query(Role).filter(Role.code == CUSTOMER).one()
    membership = (
        db.query(OrganizationMembership)
        .filter(OrganizationMembership.user_id == user.id)
        .one()
    )
    membership.role_id = customer_role.id
    db.commit()

    token = login(client, "staffish@example.com").json()["access_token"]
    response = client.patch(
        "/api/v1/organizations/me",
        headers=auth_header(token),
        json={"name": "Should Fail"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"

    readable = client.get("/api/v1/organizations/me", headers=auth_header(token))
    assert readable.status_code == 200
    assert readable.json()["name"] == "Restricted Org"
