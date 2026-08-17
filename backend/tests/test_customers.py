from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from tests.conftest import CAPTURED_INVITATION_TOKENS
from tests.test_shipments import auth_header, create_org, login, register, shipment_payload


def customer_payload(**overrides) -> dict:
    payload = {
        "name": "John Buyer",
        "phone": "+15550000001",
        "email": "john@example.com",
        "company_name": "Buyer Co",
        "city": "Lahore",
        "country": "PK",
        "postal_code": "54000",
    }
    payload.update(overrides)
    return payload


def invite_member(client: TestClient, admin_token: str, email: str, role_code: str) -> str:
    register(client, email)
    invite = client.post(
        "/api/v1/organizations/me/members",
        headers=auth_header(admin_token),
        json={"email": email, "role_code": role_code},
    )
    assert invite.status_code == 201
    assert "token" not in invite.json()
    token = login(client, email).json()["access_token"]
    client.post(
        "/api/v1/invitations/accept",
        headers=auth_header(token),
        json={"token": CAPTURED_INVITATION_TOKENS[-1]},
    )
    return token


def test_create_customer_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/customers", json=customer_payload())
    assert response.status_code == 401


def test_create_customer_belongs_to_current_organization(client: TestClient) -> None:
    token, org = create_org(client, "cust-a@example.com", "Cust Org A", "cust-org-a")
    created = client.post(
        "/api/v1/customers",
        headers=auth_header(token),
        json=customer_payload(organization_id=str(uuid4())),
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["organization_id"] == org["id"]
    assert body["created_by_user_id"]
    assert body["customer_code"].startswith("CUS-")
    assert len(body["customer_code"]) == 12
    assert body["status"] == "ACTIVE"
    assert body["email"] == "john@example.com"
    assert "GBQ" not in body["customer_code"]

    fetched = client.get(f"/api/v1/customers/{body['id']}", headers=auth_header(token))
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]
    assert fetched.json()["shipment_count"] == 0


def test_customer_code_unique_within_tenant(client: TestClient) -> None:
    token, _ = create_org(client, "codes@example.com", "Code Co", "code-co")
    first = client.post("/api/v1/customers", headers=auth_header(token), json=customer_payload()).json()
    second = client.post(
        "/api/v1/customers",
        headers=auth_header(token),
        json=customer_payload(email="other@example.com", phone="+15550000002"),
    ).json()
    assert first["customer_code"] != second["customer_code"]


def test_same_email_allowed_across_tenants(client: TestClient) -> None:
    token_a, _ = create_org(client, "email-a@example.com", "Email A", "email-a")
    token_b, _ = create_org(client, "email-b@example.com", "Email B", "email-b")
    a = client.post("/api/v1/customers", headers=auth_header(token_a), json=customer_payload())
    b = client.post("/api/v1/customers", headers=auth_header(token_b), json=customer_payload())
    assert a.status_code == 201
    assert b.status_code == 201
    assert a.json()["email"] == b.json()["email"]


def test_duplicate_email_rejected_within_tenant(client: TestClient) -> None:
    token, _ = create_org(client, "dup@example.com", "Dup Co", "dup-co")
    first = client.post("/api/v1/customers", headers=auth_header(token), json=customer_payload())
    assert first.status_code == 201
    duplicate = client.post(
        "/api/v1/customers",
        headers=auth_header(token),
        json=customer_payload(name="Other John", phone="+15550000099"),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_CUSTOMER_EMAIL"


def test_customer_search_pagination_and_status_filter(client: TestClient) -> None:
    token, _ = create_org(client, "search@example.com", "Search Co", "search-co")
    created = []
    for index in range(3):
        created.append(
            client.post(
                "/api/v1/customers",
                headers=auth_header(token),
                json=customer_payload(
                    name=f"Buyer {index}",
                    email=f"buyer{index}@example.com",
                    phone=f"+1555000001{index}",
                    company_name="Acme Logistics" if index == 1 else "Other Co",
                ),
            ).json()
        )

    deactivated = client.post(
        f"/api/v1/customers/{created[2]['id']}/deactivate",
        headers=auth_header(token),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "INACTIVE"

    page1 = client.get("/api/v1/customers", headers=auth_header(token), params={"page": 1, "page_size": 2})
    assert page1.status_code == 200
    assert page1.json()["page"] == 1
    assert page1.json()["page_size"] == 2
    assert page1.json()["total"] == 3
    assert len(page1.json()["items"]) == 2

    page2 = client.get("/api/v1/customers", headers=auth_header(token), params={"page": 2, "page_size": 2})
    assert len(page2.json()["items"]) == 1

    by_name = client.get("/api/v1/customers", headers=auth_header(token), params={"q": "Buyer 1"})
    assert by_name.json()["total"] == 1
    assert by_name.json()["items"][0]["name"] == "Buyer 1"

    by_company = client.get("/api/v1/customers", headers=auth_header(token), params={"q": "Acme"})
    assert by_company.json()["total"] == 1

    by_code = client.get(
        "/api/v1/customers",
        headers=auth_header(token),
        params={"q": created[0]["customer_code"]},
    )
    assert by_code.json()["total"] == 1

    inactive = client.get("/api/v1/customers", headers=auth_header(token), params={"status": "INACTIVE"})
    assert inactive.json()["total"] == 1
    assert inactive.json()["items"][0]["id"] == created[2]["id"]

    oversized = client.get("/api/v1/customers", headers=auth_header(token), params={"page_size": 1000})
    assert oversized.status_code == 422

    sorted_names = client.get(
        "/api/v1/customers",
        headers=auth_header(token),
        params={"sort": "name", "order": "asc"},
    )
    names = [item["name"] for item in sorted_names.json()["items"]]
    assert names == sorted(names)


def test_deactivate_and_reactivate_customer(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "status@example.com", "Status Co", "status-co")
    created = client.post("/api/v1/customers", headers=auth_header(token), json=customer_payload()).json()
    deactivated = client.post(
        f"/api/v1/customers/{created['id']}/deactivate",
        headers=auth_header(token),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "INACTIVE"
    reactivated = client.post(
        f"/api/v1/customers/{created['id']}/reactivate",
        headers=auth_header(token),
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "ACTIVE"
    actions = {row.action for row in db.query(AuditLog).filter(AuditLog.resource_id == created["id"]).all()}
    assert "CUSTOMER_CREATED" in actions
    assert "CUSTOMER_DEACTIVATED" in actions
    assert "CUSTOMER_REACTIVATED" in actions


def test_customer_cannot_be_hard_deleted(client: TestClient) -> None:
    token, _ = create_org(client, "nodelete@example.com", "No Delete Co", "no-delete-co")
    created = client.post("/api/v1/customers", headers=auth_header(token), json=customer_payload()).json()
    deleted = client.delete(f"/api/v1/customers/{created['id']}", headers=auth_header(token))
    assert deleted.status_code == 405
    still_there = client.get(f"/api/v1/customers/{created['id']}", headers=auth_header(token))
    assert still_there.status_code == 200


def test_audit_log_on_customer_update(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "upd-audit@example.com", "Upd Co", "upd-co")
    created = client.post("/api/v1/customers", headers=auth_header(token), json=customer_payload()).json()
    updated = client.patch(
        f"/api/v1/customers/{created['id']}",
        headers=auth_header(token),
        json={"name": "Updated Buyer"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated Buyer"
    assert (
        db.query(AuditLog)
        .filter(AuditLog.action == "CUSTOMER_UPDATED", AuditLog.resource_id == created["id"])
        .count()
        == 1
    )


def test_inactive_customer_cannot_be_assigned_to_new_shipment(client: TestClient) -> None:
    token, _ = create_org(client, "inactive-ship@example.com", "Inactive Ship", "inactive-ship")
    customer = client.post("/api/v1/customers", headers=auth_header(token), json=customer_payload()).json()
    client.post(f"/api/v1/customers/{customer['id']}/deactivate", headers=auth_header(token))
    created = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(customer_id=customer["id"]),
    )
    assert created.status_code == 409
    assert created.json()["error"]["code"] == "CUSTOMER_INACTIVE"


def test_active_customer_assigned_to_shipment(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "assign@example.com", "Assign Co", "assign-co")
    customer = client.post("/api/v1/customers", headers=auth_header(token), json=customer_payload()).json()
    created = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(customer_id=customer["id"]),
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["customer_id"] == customer["id"]
    assert body["customer"]["customer_code"] == customer["customer_code"]
    assert body["customer"]["name"] == customer["name"]
    assert "email" not in body["customer"]
    assert "phone" not in body["customer"]

    listed = client.get("/api/v1/shipments", headers=auth_header(token))
    assert listed.json()["items"][0]["customer_id"] == customer["id"]
    assert listed.json()["items"][0]["customer_code"] == customer["customer_code"]
    assert listed.json()["items"][0]["customer_name"] == customer["name"]

    detail = client.get(f"/api/v1/customers/{customer['id']}", headers=auth_header(token)).json()
    assert detail["shipment_count"] == 1
    assert detail["active_shipment_count"] == 1
    assert detail["latest_shipment_at"]

    assert (
        db.query(AuditLog)
        .filter(AuditLog.action == "SHIPMENT_CUSTOMER_ASSIGNED", AuditLog.resource_id == body["id"])
        .count()
        == 1
    )


def test_existing_shipments_without_customer_id_still_work(client: TestClient) -> None:
    token, _ = create_org(client, "legacy@example.com", "Legacy Co", "legacy-co")
    created = client.post("/api/v1/shipments", headers=auth_header(token), json=shipment_payload())
    assert created.status_code == 201
    body = created.json()
    assert body["customer_id"] is None
    assert body["customer"] is None
    fetched = client.get(f"/api/v1/shipments/{body['id']}", headers=auth_header(token))
    assert fetched.status_code == 200
    listed = client.get("/api/v1/shipments", headers=auth_header(token))
    assert listed.json()["items"][0]["customer_id"] is None


def test_customer_shipment_list_is_tenant_scoped_and_paginated(client: TestClient) -> None:
    token, _ = create_org(client, "cust-ship@example.com", "Cust Ship Co", "cust-ship-co")
    customer = client.post("/api/v1/customers", headers=auth_header(token), json=customer_payload()).json()
    other = client.post(
        "/api/v1/customers",
        headers=auth_header(token),
        json=customer_payload(email="other@example.com", phone="+15550000002"),
    ).json()
    for _ in range(3):
        client.post(
            "/api/v1/shipments",
            headers=auth_header(token),
            json=shipment_payload(customer_id=customer["id"]),
        )
    client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(customer_id=other["id"]),
    )

    page1 = client.get(
        f"/api/v1/customers/{customer['id']}/shipments",
        headers=auth_header(token),
        params={"page": 1, "page_size": 2},
    )
    assert page1.status_code == 200
    assert page1.json()["total"] == 3
    assert len(page1.json()["items"]) == 2
    assert all(item["customer_id"] == customer["id"] for item in page1.json()["items"])

    page2 = client.get(
        f"/api/v1/customers/{customer['id']}/shipments",
        headers=auth_header(token),
        params={"page": 2, "page_size": 2},
    )
    assert len(page2.json()["items"]) == 1


def test_staff_cannot_deactivate_customer(client: TestClient) -> None:
    admin_token, _ = create_org(client, "staff-admin@example.com", "Staff Cust", "staff-cust")
    staff_token = invite_member(client, admin_token, "staff-cust@example.com", "STAFF")
    created = client.post("/api/v1/customers", headers=auth_header(staff_token), json=customer_payload())
    assert created.status_code == 201
    updated = client.patch(
        f"/api/v1/customers/{created.json()['id']}",
        headers=auth_header(staff_token),
        json={"name": "Staff Updated"},
    )
    assert updated.status_code == 200
    deactivated = client.post(
        f"/api/v1/customers/{created.json()['id']}/deactivate",
        headers=auth_header(staff_token),
    )
    assert deactivated.status_code == 403


def test_customer_role_cannot_use_customer_management(client: TestClient) -> None:
    admin_token, _ = create_org(client, "role-admin@example.com", "Role Cust", "role-cust")
    created = client.post("/api/v1/customers", headers=auth_header(admin_token), json=customer_payload()).json()
    buyer_token = invite_member(client, admin_token, "buyer-cust@example.com", "CUSTOMER")
    assert client.post("/api/v1/customers", headers=auth_header(buyer_token), json=customer_payload()).status_code == 403
    assert client.get("/api/v1/customers", headers=auth_header(buyer_token)).status_code == 403
    assert client.get(f"/api/v1/customers/{created['id']}", headers=auth_header(buyer_token)).status_code == 403
    assert client.patch(
        f"/api/v1/customers/{created['id']}",
        headers=auth_header(buyer_token),
        json={"name": "Nope"},
    ).status_code == 403
    assert client.post(
        f"/api/v1/customers/{created['id']}/deactivate",
        headers=auth_header(buyer_token),
    ).status_code == 403
    assert client.get(
        f"/api/v1/customers/{created['id']}/shipments",
        headers=auth_header(buyer_token),
    ).status_code == 403


def test_cross_tenant_customer_and_shipment_isolation(client: TestClient) -> None:
    token_a, _ = create_org(client, "iso-cust-a@example.com", "Iso Cust A", "iso-cust-a")
    token_b, _ = create_org(client, "iso-cust-b@example.com", "Iso Cust B", "iso-cust-b")

    customer_a = client.post(
        "/api/v1/customers",
        headers=auth_header(token_a),
        json=customer_payload(email="a@example.com"),
    ).json()
    customer_b = client.post(
        "/api/v1/customers",
        headers=auth_header(token_b),
        json=customer_payload(email="b@example.com"),
    ).json()

    shipment_a = client.post(
        "/api/v1/shipments",
        headers=auth_header(token_a),
        json=shipment_payload(customer_id=customer_a["id"]),
    ).json()
    shipment_b = client.post(
        "/api/v1/shipments",
        headers=auth_header(token_b),
        json=shipment_payload(customer_id=customer_b["id"]),
    ).json()

    assert client.get(f"/api/v1/customers/{customer_a['id']}", headers=auth_header(token_a)).status_code == 200
    missing_customer = client.get(f"/api/v1/customers/{customer_b['id']}", headers=auth_header(token_a))
    assert missing_customer.status_code == 404
    assert missing_customer.json()["error"]["code"] == "NOT_FOUND"

    update_b = client.patch(
        f"/api/v1/customers/{customer_b['id']}",
        headers=auth_header(token_a),
        json={"name": "Hijack"},
    )
    assert update_b.status_code == 404

    deactivate_b = client.post(
        f"/api/v1/customers/{customer_b['id']}/deactivate",
        headers=auth_header(token_a),
    )
    assert deactivate_b.status_code == 404

    assert client.get(f"/api/v1/shipments/{shipment_a['id']}", headers=auth_header(token_a)).status_code == 200
    missing_shipment = client.get(f"/api/v1/shipments/{shipment_b['id']}", headers=auth_header(token_a))
    assert missing_shipment.status_code == 404
    assert missing_shipment.json()["error"]["code"] == "NOT_FOUND"

    assign_cross = client.post(
        "/api/v1/shipments",
        headers=auth_header(token_a),
        json=shipment_payload(customer_id=customer_b["id"]),
    )
    assert assign_cross.status_code == 404
    assert assign_cross.json()["error"]["code"] == "NOT_FOUND"

    patch_cross = client.patch(
        f"/api/v1/shipments/{shipment_a['id']}",
        headers=auth_header(token_a),
        json={"customer_id": customer_b["id"]},
    )
    assert patch_cross.status_code == 404

    shipments_b = client.get(
        f"/api/v1/customers/{customer_b['id']}/shipments",
        headers=auth_header(token_a),
    )
    assert shipments_b.status_code == 404

    listed_a = client.get("/api/v1/customers", headers=auth_header(token_a)).json()
    assert listed_a["total"] == 1
    assert listed_a["items"][0]["id"] == customer_a["id"]

    assert client.get(f"/api/v1/customers/{customer_a['id']}", headers=auth_header(token_b)).status_code == 404
    assert client.get(f"/api/v1/shipments/{shipment_a['id']}", headers=auth_header(token_b)).status_code == 404
    assert client.get(
        f"/api/v1/customers/{customer_a['id']}/shipments",
        headers=auth_header(token_b),
    ).status_code == 404
