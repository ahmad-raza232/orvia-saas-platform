from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
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


def shipment_payload(**overrides) -> dict:
    payload = {
        "sender": {
            "name": "Sender One",
            "phone": "+10000000001",
            "address": "1 Origin Street",
            "city": "Lahore",
            "country": "PK",
        },
        "receiver": {
            "name": "Receiver One",
            "phone": "+10000000002",
            "address": "2 Destination Ave",
            "city": "Karachi",
            "country": "PK",
        },
        "parcel": {
            "weight_kg": "2.5",
            "length_cm": "10",
            "width_cm": "8",
            "height_cm": "6",
            "package_type": "small",
            "description": "Documents",
            "quantity": 1,
        },
        "service_type": "STANDARD",
        "reference_number": "ORDER-10023",
    }
    payload.update(overrides)
    return payload


def test_create_shipment_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/shipments", json=shipment_payload())
    assert response.status_code == 401


def test_create_and_get_shipment_uses_current_organization(client: TestClient) -> None:
    token, org = create_org(client, "ship-a@example.com", "Org A", "ship-org-a")
    created = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(status="BOOKED", **{"organization_id": str(uuid4())}),
    )
    # organization_id in the body is ignored extra input; tenant context wins.
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["organization_id"] == org["id"]
    assert body["created_by_user_id"]
    assert body["tracking_number"].startswith("ORVIA-")
    assert body["tracking_number"] != body.get("gbq")
    assert "GBQ" not in body["tracking_number"]
    assert body["status"] == "BOOKED"
    assert len(body["status_history"]) == 1
    assert body["status_history"][0]["previous_status"] is None

    fetched = client.get(f"/api/v1/shipments/{body['id']}", headers=auth_header(token))
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


def test_tenant_isolation_for_shipments(client: TestClient) -> None:
    token_a, _ = create_org(client, "iso-a@example.com", "Iso A", "iso-a")
    token_b, _ = create_org(client, "iso-b@example.com", "Iso B", "iso-b")
    created = client.post(
        "/api/v1/shipments",
        headers=auth_header(token_a),
        json=shipment_payload(),
    ).json()

    assert client.get(f"/api/v1/shipments/{created['id']}", headers=auth_header(token_a)).status_code == 200
    missing = client.get(f"/api/v1/shipments/{created['id']}", headers=auth_header(token_b))
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"

    updated = client.patch(
        f"/api/v1/shipments/{created['id']}",
        headers=auth_header(token_b),
        json={"notes": "hijack"},
    )
    assert updated.status_code == 404

    cancelled = client.post(
        f"/api/v1/shipments/{created['id']}/cancel",
        headers=auth_header(token_b),
        json={},
    )
    assert cancelled.status_code == 404


def test_tracking_unique_and_reference_repeatable(client: TestClient) -> None:
    token_a, _ = create_org(client, "ref-a@example.com", "Ref A", "ref-a")
    token_b, _ = create_org(client, "ref-b@example.com", "Ref B", "ref-b")
    first = client.post("/api/v1/shipments", headers=auth_header(token_a), json=shipment_payload()).json()
    second = client.post("/api/v1/shipments", headers=auth_header(token_a), json=shipment_payload()).json()
    other = client.post("/api/v1/shipments", headers=auth_header(token_b), json=shipment_payload()).json()
    assert first["tracking_number"] != second["tracking_number"]
    assert first["reference_number"] == other["reference_number"] == "ORDER-10023"

    search_a = client.get(
        "/api/v1/shipments",
        headers=auth_header(token_a),
        params={"reference_number": "ORDER-10023"},
    )
    assert search_a.status_code == 200
    assert search_a.json()["total"] == 2
    assert all(item["id"] != other["id"] for item in search_a.json()["items"])

    search_b = client.get(
        "/api/v1/shipments",
        headers=auth_header(token_b),
        params={"q": first["tracking_number"]},
    )
    assert search_b.json()["total"] == 0
    assert search_b.json()["items"] == []


def test_update_cancel_history_and_audit(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "flow@example.com", "Flow Co", "flow-co")
    draft = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(status="DRAFT"),
    )
    assert draft.status_code == 201
    shipment_id = draft.json()["id"]
    assert len(draft.json()["status_history"]) == 1

    updated = client.patch(
        f"/api/v1/shipments/{shipment_id}",
        headers=auth_header(token),
        json={"notes": "hold at lobby", "parcel": {"weight_kg": "3.25"}, "status_history": []},
    )
    assert updated.status_code == 200
    assert updated.json()["notes"] == "hold at lobby"
    assert float(updated.json()["parcel"]["weight_kg"]) == 3.25
    assert updated.json()["tracking_number"] == draft.json()["tracking_number"]
    assert len(updated.json()["status_history"]) == 1

    booked = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(status="BOOKED", reference_number="BOOK-1"),
    ).json()
    limited = client.patch(
        f"/api/v1/shipments/{booked['id']}",
        headers=auth_header(token),
        json={"notes": "gate code 12", "receiver": {"phone": "+19999999999"}},
    )
    assert limited.status_code == 200
    blocked_booked = client.patch(
        f"/api/v1/shipments/{booked['id']}",
        headers=auth_header(token),
        json={"parcel": {"weight_kg": "9"}},
    )
    assert blocked_booked.status_code == 409

    cancelled = client.post(
        f"/api/v1/shipments/{booked['id']}/cancel",
        headers=auth_header(token),
        json={"note": "customer withdrew"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    assert len(cancelled.json()["status_history"]) == 2
    assert cancelled.json()["status_history"][-1]["new_status"] == "CANCELLED"

    locked = client.patch(
        f"/api/v1/shipments/{booked['id']}",
        headers=auth_header(token),
        json={"notes": "too late"},
    )
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "SHIPMENT_NOT_EDITABLE"

    recancel = client.post(
        f"/api/v1/shipments/{booked['id']}/cancel",
        headers=auth_header(token),
        json={},
    )
    assert recancel.status_code == 409

    actions = {row.action for row in db.query(AuditLog).all()}
    assert "SHIPMENT_CREATED" in actions
    assert "SHIPMENT_UPDATED" in actions
    assert "SHIPMENT_CANCELLED" in actions
    assert "SHIPMENT_STATUS_CHANGED" in actions


def test_validation_rejects_bad_parcel_values(client: TestClient) -> None:
    token, _ = create_org(client, "valid@example.com", "Valid Co", "valid-co")
    negative_weight = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(parcel={"weight_kg": "-1", "quantity": 1}),
    )
    assert negative_weight.status_code == 422

    negative_dim = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(
            parcel={"weight_kg": "1", "length_cm": "-2", "width_cm": "1", "height_cm": "1", "quantity": 1}
        ),
    )
    assert negative_dim.status_code == 422

    bad_qty = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(parcel={"weight_kg": "1", "quantity": 0}),
    )
    assert bad_qty.status_code == 422


def test_pagination_filters_and_search(client: TestClient) -> None:
    token, _ = create_org(client, "page@example.com", "Page Co", "page-co")
    created = []
    for index in range(3):
        payload = shipment_payload(
            status="DRAFT" if index == 0 else "BOOKED",
            reference_number=f"REF-{index}",
        )
        payload["receiver"]["name"] = f"Receiver {index}"
        payload["receiver"]["phone"] = f"+1555000000{index}"
        created.append(
            client.post("/api/v1/shipments", headers=auth_header(token), json=payload).json()
        )

    page1 = client.get("/api/v1/shipments", headers=auth_header(token), params={"page": 1, "page_size": 2})
    assert page1.status_code == 200
    assert page1.json()["page"] == 1
    assert page1.json()["page_size"] == 2
    assert page1.json()["total"] == 3
    assert len(page1.json()["items"]) == 2

    page2 = client.get("/api/v1/shipments", headers=auth_header(token), params={"page": 2, "page_size": 2})
    assert len(page2.json()["items"]) == 1

    drafts = client.get("/api/v1/shipments", headers=auth_header(token), params={"status": "DRAFT"})
    assert drafts.json()["total"] == 1
    assert drafts.json()["items"][0]["status"] == "DRAFT"

    by_tracking = client.get(
        "/api/v1/shipments",
        headers=auth_header(token),
        params={"q": created[1]["tracking_number"]},
    )
    assert by_tracking.json()["total"] == 1
    assert by_tracking.json()["items"][0]["tracking_number"] == created[1]["tracking_number"]

    oversized = client.get("/api/v1/shipments", headers=auth_header(token), params={"page_size": 1000})
    assert oversized.status_code == 422


def test_staff_can_create_but_cannot_cancel(client: TestClient) -> None:
    token_admin, _ = create_org(client, "boss@example.com", "Staff Co", "staff-co")
    register(client, "clerk@example.com")
    invite = client.post(
        "/api/v1/organizations/me/members",
        headers=auth_header(token_admin),
        json={"email": "clerk@example.com", "role_code": "STAFF"},
    ).json()
    staff_token = login(client, "clerk@example.com").json()["access_token"]
    client.post(
        "/api/v1/invitations/accept",
        headers=auth_header(staff_token),
        json={"token": CAPTURED_INVITATION_TOKENS[-1]},
    )
    created = client.post(
        "/api/v1/shipments",
        headers=auth_header(staff_token),
        json=shipment_payload(),
    )
    assert created.status_code == 201
    cancelled = client.post(
        f"/api/v1/shipments/{created.json()['id']}/cancel",
        headers=auth_header(staff_token),
        json={},
    )
    assert cancelled.status_code == 403


def test_customer_cannot_access_shipments(client: TestClient) -> None:
    token_admin, _ = create_org(client, "cust-admin@example.com", "Cust Co", "cust-co")
    register(client, "buyer@example.com")
    invite = client.post(
        "/api/v1/organizations/me/members",
        headers=auth_header(token_admin),
        json={"email": "buyer@example.com", "role_code": "CUSTOMER"},
    ).json()
    buyer_token = login(client, "buyer@example.com").json()["access_token"]
    client.post(
        "/api/v1/invitations/accept",
        headers=auth_header(buyer_token),
        json={"token": CAPTURED_INVITATION_TOKENS[-1]},
    )
    created = client.post(
        "/api/v1/shipments",
        headers=auth_header(buyer_token),
        json=shipment_payload(),
    )
    assert created.status_code == 403
    listed = client.get("/api/v1/shipments", headers=auth_header(buyer_token))
    assert listed.status_code == 403


def test_create_shipment_cod_pickup_and_independent_parties(client: TestClient) -> None:
    token, _org = create_org(
        client, "ship-cod@example.com", "COD Org", "ship-cod-org"
    )
    created = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(
            status="BOOKED",
            pickup_at="2030-01-15T09:00:00",
            cod_amount="1250.50",
            currency="PKR",
            sender={
                "name": "Independent Sender",
                "phone": "+10000000011",
                "address": "Sender Road 1",
                "city": "Lahore",
                "country": "PK",
            },
            receiver={
                "name": "Independent Receiver",
                "phone": "+10000000022",
                "address": "Receiver Road 9",
                "city": "Karachi",
                "country": "PK",
            },
        ),
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["tracking_number"].startswith("ORVIA-")
    assert body["sender"]["name"] == "Independent Sender"
    assert body["receiver"]["name"] == "Independent Receiver"
    assert body["sender"]["name"] != body["receiver"]["name"]
    assert body["sender"]["city"] == "Lahore"
    assert body["receiver"]["city"] == "Karachi"
    assert str(body["cod_amount"]) in {"1250.50", "1250.5"}
    assert body["currency"] == "PKR"
    assert body["pickup_at"] is not None
    assert "2030-01-15" in body["pickup_at"]

    prepaid = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(
            status="BOOKED",
            pickup_at="2030-01-16T09:00:00",
            cod_amount=None,
            currency=None,
            reference_number="PREPAID-1",
        ),
    )
    assert prepaid.status_code == 201, prepaid.text
    prepaid_body = prepaid.json()
    assert prepaid_body["cod_amount"] is None
    assert prepaid_body["currency"] is None

    listed = client.get("/api/v1/shipments", headers=auth_header(token))
    assert listed.status_code == 200
    ids = {item["id"] for item in listed.json()["items"]}
    assert body["id"] in ids

    detail = client.get(f"/api/v1/shipments/{body['id']}", headers=auth_header(token))
    assert detail.status_code == 200
    assert detail.json()["sender"]["name"] == "Independent Sender"
    assert detail.json()["receiver"]["name"] == "Independent Receiver"

    missing_currency = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(cod_amount="10.00", currency=None),
    )
    assert missing_currency.status_code == 422
