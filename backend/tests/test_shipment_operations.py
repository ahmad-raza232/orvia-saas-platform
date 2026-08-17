from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from tests.test_customers import customer_payload, invite_member
from tests.test_shipments import auth_header, create_org, shipment_payload


def change_status(client: TestClient, token: str, shipment_id: str, status: str, note: str | None = None):
    payload: dict = {"status": status}
    if note is not None:
        payload["note"] = note
    return client.post(
        f"/api/v1/shipments/{shipment_id}/status",
        headers=auth_header(token),
        json=payload,
    )


def walk_to(client: TestClient, token: str, shipment_id: str, statuses: list[str]) -> None:
    for status in statuses:
        response = change_status(client, token, shipment_id, status, note=f"Moved to {status}")
        assert response.status_code == 200, response.text
        assert response.json()["status"] == status


def test_operational_happy_path_timestamps_history_and_audit(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "ops-happy@example.com", "Ops Happy", "ops-happy")
    created = client.post("/api/v1/shipments", headers=auth_header(token), json=shipment_payload()).json()
    shipment_id = created["id"]
    assert created["picked_up_at"] is None
    assert created["status_history"][0]["previous_status"] is None
    assert created["status_history"][0]["new_status"] == "BOOKED"

    picked = change_status(client, token, shipment_id, "PICKED_UP", "Picked up from customer")
    assert picked.status_code == 200, picked.text
    body = picked.json()
    assert body["status"] == "PICKED_UP"
    assert body["picked_up_at"]
    assert body["in_transit_at"] is None
    first_picked = body["picked_up_at"]

    transit = change_status(client, token, shipment_id, "IN_TRANSIT", "Departed Lahore hub")
    assert transit.status_code == 200
    assert transit.json()["in_transit_at"]
    assert transit.json()["picked_up_at"] == first_picked

    ofd = change_status(client, token, shipment_id, "OUT_FOR_DELIVERY", "Out for delivery")
    assert ofd.status_code == 200
    assert ofd.json()["out_for_delivery_at"]
    assert ofd.json()["picked_up_at"] == first_picked

    delivered = change_status(client, token, shipment_id, "DELIVERED", "Delivered to recipient")
    assert delivered.status_code == 200
    assert delivered.json()["status"] == "DELIVERED"
    assert delivered.json()["delivered_at"]
    assert delivered.json()["picked_up_at"] == first_picked
    assert delivered.json()["cancelled_at"] is None

    history = client.get(f"/api/v1/shipments/{shipment_id}/history", headers=auth_header(token))
    assert history.status_code == 200
    items = history.json()["items"]
    assert [item["to_status"] for item in items] == [
        "BOOKED",
        "PICKED_UP",
        "IN_TRANSIT",
        "OUT_FOR_DELIVERY",
        "DELIVERED",
    ]
    assert [item["from_status"] for item in items] == [
        None,
        "BOOKED",
        "PICKED_UP",
        "IN_TRANSIT",
        "OUT_FOR_DELIVERY",
    ]
    created_at = [item["created_at"] for item in items]
    assert created_at == sorted(created_at)
    assert items[1]["note"] == "Picked up from customer"
    assert items[1]["changed_by_user_id"]

    assert change_status(client, token, shipment_id, "IN_TRANSIT").status_code == 409
    cancelled = client.post(
        f"/api/v1/shipments/{shipment_id}/cancel",
        headers=auth_header(token),
        json={},
    )
    assert cancelled.status_code == 409
    assert cancelled.json()["error"]["code"] == "SHIPMENT_NOT_CANCELLABLE"

    notes = client.patch(
        f"/api/v1/shipments/{shipment_id}",
        headers=auth_header(token),
        json={"notes": "left at door"},
    )
    assert notes.status_code == 200
    blocked = client.patch(
        f"/api/v1/shipments/{shipment_id}",
        headers=auth_header(token),
        json={"parcel": {"weight_kg": "9"}},
    )
    assert blocked.status_code == 409

    actions = [
        row.action
        for row in db.query(AuditLog).filter(AuditLog.resource_id == shipment_id).all()
    ]
    assert actions.count("SHIPMENT_STATUS_CHANGED") == 4
    changed = (
        db.query(AuditLog)
        .filter(AuditLog.action == "SHIPMENT_STATUS_CHANGED", AuditLog.resource_id == shipment_id)
        .all()
    )
    assert all(row.details.get("tracking_number") for row in changed)
    assert {row.details["to"] for row in changed} == {
        "PICKED_UP",
        "IN_TRANSIT",
        "OUT_FOR_DELIVERY",
        "DELIVERED",
    }


def test_draft_and_booked_cancellation_sets_cancelled_at(client: TestClient) -> None:
    token, _ = create_org(client, "ops-cancel@example.com", "Ops Cancel", "ops-cancel")
    draft = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(status="DRAFT"),
    ).json()
    cancelled_draft = client.post(
        f"/api/v1/shipments/{draft['id']}/cancel",
        headers=auth_header(token),
        json={"note": "abandoned draft"},
    )
    assert cancelled_draft.status_code == 200
    assert cancelled_draft.json()["status"] == "CANCELLED"
    assert cancelled_draft.json()["cancelled_at"]

    booked = client.post("/api/v1/shipments", headers=auth_header(token), json=shipment_payload()).json()
    cancelled_booked = client.post(
        f"/api/v1/shipments/{booked['id']}/cancel",
        headers=auth_header(token),
        json={},
    )
    assert cancelled_booked.status_code == 200
    assert cancelled_booked.json()["cancelled_at"]
    recancel = client.post(
        f"/api/v1/shipments/{booked['id']}/cancel",
        headers=auth_header(token),
        json={},
    )
    assert recancel.status_code == 409
    reopen = change_status(client, token, booked["id"], "BOOKED")
    assert reopen.status_code == 409
    assert reopen.json()["error"]["code"] == "SHIPMENT_INVALID_TRANSITION"


def test_invalid_status_transitions_rejected(client: TestClient) -> None:
    token, _ = create_org(client, "ops-bad@example.com", "Ops Bad", "ops-bad")
    draft = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(status="DRAFT"),
    ).json()
    booked = client.post("/api/v1/shipments", headers=auth_header(token), json=shipment_payload()).json()

    cases = [
        (draft["id"], "DELIVERED"),
        (booked["id"], "IN_TRANSIT"),
        (booked["id"], "DELIVERED"),
        (booked["id"], "BOOKED"),
        (booked["id"], "CANCELLED"),
        (draft["id"], "DRAFT"),
    ]
    for shipment_id, status in cases:
        response = change_status(client, token, shipment_id, status)
        assert response.status_code == 409, (status, response.text)
        assert response.json()["error"]["code"] == "SHIPMENT_INVALID_TRANSITION"

    walk_to(client, token, booked["id"], ["PICKED_UP"])
    skip = change_status(client, token, booked["id"], "DELIVERED")
    assert skip.status_code == 409
    same = change_status(client, token, booked["id"], "PICKED_UP")
    assert same.status_code == 409
    cancel_picked = client.post(
        f"/api/v1/shipments/{booked['id']}/cancel",
        headers=auth_header(token),
        json={},
    )
    assert cancel_picked.status_code == 409


def test_status_history_is_immutable_through_api(client: TestClient) -> None:
    token, _ = create_org(client, "ops-hist@example.com", "Ops Hist", "ops-hist")
    created = client.post("/api/v1/shipments", headers=auth_header(token), json=shipment_payload()).json()
    history_url = f"/api/v1/shipments/{created['id']}/history"
    assert client.patch(history_url, headers=auth_header(token), json={"items": []}).status_code == 405
    assert client.delete(history_url, headers=auth_header(token)).status_code == 405
    assert client.post(history_url, headers=auth_header(token), json={}).status_code == 405
    patched = client.patch(
        f"/api/v1/shipments/{created['id']}",
        headers=auth_header(token),
        json={"notes": "keep history", "status_history": []},
    )
    assert patched.status_code == 200
    history = client.get(history_url, headers=auth_header(token)).json()["items"]
    assert len(history) == 1


def test_staff_and_operations_manager_can_change_status_customer_cannot(client: TestClient) -> None:
    admin_token, _ = create_org(client, "ops-roles@example.com", "Ops Roles", "ops-roles")
    staff_token = invite_member(client, admin_token, "ops-staff@example.com", "STAFF")
    ops_token = invite_member(client, admin_token, "ops-manager@example.com", "OPERATIONS_MANAGER")
    buyer_token = invite_member(client, admin_token, "ops-buyer@example.com", "CUSTOMER")

    staff_ship = client.post(
        "/api/v1/shipments",
        headers=auth_header(staff_token),
        json=shipment_payload(reference_number="STAFF-1"),
    ).json()
    assert change_status(client, staff_token, staff_ship["id"], "PICKED_UP").status_code == 200

    ops_ship = client.post(
        "/api/v1/shipments",
        headers=auth_header(ops_token),
        json=shipment_payload(reference_number="OPS-1"),
    ).json()
    assert change_status(client, ops_token, ops_ship["id"], "PICKED_UP").status_code == 200

    admin_ship = client.post(
        "/api/v1/shipments",
        headers=auth_header(admin_token),
        json=shipment_payload(reference_number="ADMIN-1"),
    ).json()
    assert change_status(client, admin_token, admin_ship["id"], "PICKED_UP").status_code == 200

    assert change_status(client, buyer_token, admin_ship["id"], "IN_TRANSIT").status_code == 403
    assert client.get(
        f"/api/v1/shipments/{admin_ship['id']}/history",
        headers=auth_header(buyer_token),
    ).status_code == 403


def test_cross_tenant_status_and_history_isolation(client: TestClient) -> None:
    token_a, _ = create_org(client, "ops-iso-a@example.com", "Ops Iso A", "ops-iso-a")
    token_b, _ = create_org(client, "ops-iso-b@example.com", "Ops Iso B", "ops-iso-b")
    ship_a = client.post("/api/v1/shipments", headers=auth_header(token_a), json=shipment_payload()).json()
    ship_b = client.post("/api/v1/shipments", headers=auth_header(token_b), json=shipment_payload()).json()

    assert client.get(f"/api/v1/shipments/{ship_a['id']}", headers=auth_header(token_a)).status_code == 200
    missing = client.get(f"/api/v1/shipments/{ship_b['id']}", headers=auth_header(token_a))
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"

    assert change_status(client, token_a, ship_a["id"], "PICKED_UP").status_code == 200
    cross_status = change_status(client, token_a, ship_b["id"], "PICKED_UP")
    assert cross_status.status_code == 404
    assert cross_status.json()["error"]["code"] == "NOT_FOUND"

    hist_a = client.get(f"/api/v1/shipments/{ship_a['id']}/history", headers=auth_header(token_a))
    assert hist_a.status_code == 200
    hist_b = client.get(f"/api/v1/shipments/{ship_b['id']}/history", headers=auth_header(token_a))
    assert hist_b.status_code == 404

    listed = client.get("/api/v1/shipments", headers=auth_header(token_a), params={"status": "PICKED_UP"})
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == ship_a["id"]

    assert client.get(f"/api/v1/shipments/{ship_a['id']}", headers=auth_header(token_b)).status_code == 404
    assert change_status(client, token_b, ship_a["id"], "IN_TRANSIT").status_code == 404
    assert client.get(
        f"/api/v1/shipments/{ship_a['id']}/history",
        headers=auth_header(token_b),
    ).status_code == 404


def test_status_filter_and_pagination_still_work(client: TestClient) -> None:
    token, _ = create_org(client, "ops-page@example.com", "Ops Page", "ops-page")
    created = []
    for index in range(3):
        created.append(
            client.post(
                "/api/v1/shipments",
                headers=auth_header(token),
                json=shipment_payload(reference_number=f"OPS-{index}"),
            ).json()
        )
    walk_to(client, token, created[0]["id"], ["PICKED_UP"])
    walk_to(client, token, created[1]["id"], ["PICKED_UP", "IN_TRANSIT"])

    picked = client.get("/api/v1/shipments", headers=auth_header(token), params={"status": "PICKED_UP"})
    assert picked.json()["total"] == 1
    assert picked.json()["items"][0]["id"] == created[0]["id"]

    transit = client.get("/api/v1/shipments", headers=auth_header(token), params={"status": "IN_TRANSIT"})
    assert transit.json()["total"] == 1

    page1 = client.get("/api/v1/shipments", headers=auth_header(token), params={"page": 1, "page_size": 2})
    assert page1.json()["total"] == 3
    assert len(page1.json()["items"]) == 2


def test_customer_assignment_survives_operations(client: TestClient) -> None:
    token, _ = create_org(client, "ops-cust@example.com", "Ops Cust", "ops-cust")
    customer = client.post("/api/v1/customers", headers=auth_header(token), json=customer_payload()).json()
    inactive = client.post(
        "/api/v1/customers",
        headers=auth_header(token),
        json=customer_payload(email="inactive@example.com", phone="+15550000002"),
    ).json()
    client.post(f"/api/v1/customers/{inactive['id']}/deactivate", headers=auth_header(token))

    with_customer = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(customer_id=customer["id"]),
    )
    assert with_customer.status_code == 201
    assert change_status(client, token, with_customer.json()["id"], "PICKED_UP").status_code == 200
    assert with_customer.json()["customer_id"] == customer["id"]

    rejected = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(customer_id=inactive["id"]),
    )
    assert rejected.status_code == 409

    legacy = client.post("/api/v1/shipments", headers=auth_header(token), json=shipment_payload())
    assert legacy.status_code == 201
    assert legacy.json()["customer_id"] is None
    advanced = change_status(client, token, legacy.json()["id"], "PICKED_UP")
    assert advanced.status_code == 200
    assert advanced.json()["customer_id"] is None


def test_draft_can_be_booked_through_status_endpoint(client: TestClient) -> None:
    token, _ = create_org(client, "ops-book@example.com", "Ops Book", "ops-book")
    draft = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(status="DRAFT"),
    ).json()
    booked = change_status(client, token, draft["id"], "BOOKED", "Ready to ship")
    assert booked.status_code == 200
    assert booked.json()["status"] == "BOOKED"
    assert booked.json()["picked_up_at"] is None
