from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.rider import ShipmentRiderAssignment
from tests.test_customers import customer_payload, invite_member
from tests.test_shipment_operations import walk_to
from tests.test_shipments import auth_header, create_org, shipment_payload

OFD = ["PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY"]


def rider_payload(**overrides) -> dict:
    payload = {
        "name": "Ali Rider",
        "phone": "+15551110001",
        "email": "ali.rider@example.com",
        "vehicle_type": "MOTORCYCLE",
        "vehicle_number": "ABC-123",
    }
    payload.update(overrides)
    return payload


def create_rider(client: TestClient, token: str, **overrides) -> dict:
    created = client.post("/api/v1/riders", headers=auth_header(token), json=rider_payload(**overrides))
    assert created.status_code == 201, created.text
    return created.json()


def ofd_shipment(client: TestClient, token: str, **overrides) -> dict:
    created = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(**overrides),
    ).json()
    walk_to(client, token, created["id"], OFD)
    return client.get(f"/api/v1/shipments/{created['id']}", headers=auth_header(token)).json()


def assign(client: TestClient, token: str, shipment_id: str, rider_id: str, note: str | None = None):
    payload: dict = {"rider_id": rider_id}
    if note is not None:
        payload["note"] = note
    return client.post(
        f"/api/v1/shipments/{shipment_id}/assign-rider",
        headers=auth_header(token),
        json=payload,
    )


def test_create_rider_requires_auth(client: TestClient) -> None:
    assert client.post("/api/v1/riders", json=rider_payload()).status_code == 401


def test_create_rider_belongs_to_current_organization(client: TestClient) -> None:
    token, org = create_org(client, "rider-a@example.com", "Rider Org A", "rider-org-a")
    body = create_rider(client, token)
    assert body["organization_id"] == org["id"]
    assert body["rider_code"].startswith("RDR-")
    assert len(body["rider_code"]) == 12
    assert body["status"] == "ACTIVE"
    assert "GBQ" not in body["rider_code"]
    fetched = client.get(f"/api/v1/riders/{body['id']}", headers=auth_header(token))
    assert fetched.status_code == 200
    assert fetched.json()["assigned_shipment_count"] == 0


def test_rider_code_unique_and_email_allowed_across_tenants(client: TestClient) -> None:
    token_a, _ = create_org(client, "rcode-a@example.com", "RCode A", "rcode-a")
    token_b, _ = create_org(client, "rcode-b@example.com", "RCode B", "rcode-b")
    first = create_rider(client, token_a)
    second = create_rider(client, token_a, email="other@example.com", phone="+15551110002")
    other = create_rider(client, token_b)
    assert first["rider_code"] != second["rider_code"]
    assert first["email"] == other["email"]


def test_rider_search_pagination_status_and_no_delete(client: TestClient) -> None:
    token, _ = create_org(client, "rsearch@example.com", "RSearch", "rsearch")
    created = [
        create_rider(client, token, name=f"Rider {index}", email=f"r{index}@example.com", phone=f"+1555111001{index}")
        for index in range(3)
    ]
    deactivated = client.post(
        f"/api/v1/riders/{created[2]['id']}/deactivate",
        headers=auth_header(token),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "INACTIVE"

    page1 = client.get("/api/v1/riders", headers=auth_header(token), params={"page": 1, "page_size": 2})
    assert page1.json()["total"] == 3
    assert len(page1.json()["items"]) == 2
    page2 = client.get("/api/v1/riders", headers=auth_header(token), params={"page": 2, "page_size": 2})
    assert len(page2.json()["items"]) == 1

    by_name = client.get("/api/v1/riders", headers=auth_header(token), params={"q": "Rider 1"})
    assert by_name.json()["total"] == 1
    inactive = client.get("/api/v1/riders", headers=auth_header(token), params={"status": "INACTIVE"})
    assert inactive.json()["total"] == 1
    oversized = client.get("/api/v1/riders", headers=auth_header(token), params={"page_size": 1000})
    assert oversized.status_code == 422

    deleted = client.delete(f"/api/v1/riders/{created[0]['id']}", headers=auth_header(token))
    assert deleted.status_code == 405


def test_deactivate_reactivate_and_audits(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "rstat@example.com", "RStat", "rstat")
    rider = create_rider(client, token)
    client.patch(f"/api/v1/riders/{rider['id']}", headers=auth_header(token), json={"name": "Updated Rider"})
    client.post(f"/api/v1/riders/{rider['id']}/deactivate", headers=auth_header(token))
    reactivated = client.post(f"/api/v1/riders/{rider['id']}/reactivate", headers=auth_header(token))
    assert reactivated.json()["status"] == "ACTIVE"
    actions = {row.action for row in db.query(AuditLog).filter(AuditLog.resource_id == rider["id"]).all()}
    assert actions >= {"RIDER_CREATED", "RIDER_UPDATED", "RIDER_DEACTIVATED", "RIDER_REACTIVATED"}


def test_assignment_only_at_out_for_delivery(client: TestClient) -> None:
    token, _ = create_org(client, "rassign@example.com", "RAssign", "rassign")
    rider = create_rider(client, token)
    booked = client.post("/api/v1/shipments", headers=auth_header(token), json=shipment_payload()).json()
    draft = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(status="DRAFT", reference_number="DRAFT-1"),
    ).json()
    cancelled = client.post("/api/v1/shipments", headers=auth_header(token), json=shipment_payload(reference_number="CXL")).json()
    client.post(f"/api/v1/shipments/{cancelled['id']}/cancel", headers=auth_header(token), json={})

    picked = client.post("/api/v1/shipments", headers=auth_header(token), json=shipment_payload(reference_number="P1")).json()
    walk_to(client, token, picked["id"], ["PICKED_UP"])
    transit = client.post("/api/v1/shipments", headers=auth_header(token), json=shipment_payload(reference_number="T1")).json()
    walk_to(client, token, transit["id"], ["PICKED_UP", "IN_TRANSIT"])
    delivered = ofd_shipment(client, token, reference_number="D1")
    walk_to(client, token, delivered["id"], ["DELIVERED"])

    for shipment_id in [draft["id"], booked["id"], picked["id"], transit["id"], delivered["id"], cancelled["id"]]:
        response = assign(client, token, shipment_id, rider["id"])
        assert response.status_code == 409, shipment_id
        assert response.json()["error"]["code"] == "SHIPMENT_NOT_ASSIGNABLE"

    ofd = ofd_shipment(client, token, reference_number="OFD-1")
    ok = assign(client, token, ofd["id"], rider["id"], "Last mile")
    assert ok.status_code == 200, ok.text
    assert ok.json()["rider_id"] == rider["id"]
    assert ok.json()["rider"]["rider_code"] == rider["rider_code"]
    assert ok.json()["rider"]["name"] == rider["name"]
    assert "phone" not in ok.json()["rider"]


def test_inactive_rider_cannot_receive_new_assignment(client: TestClient) -> None:
    token, _ = create_org(client, "rinact@example.com", "RInact", "rinact")
    rider = create_rider(client, token)
    ofd = ofd_shipment(client, token)
    client.post(f"/api/v1/riders/{rider['id']}/deactivate", headers=auth_header(token))
    blocked = assign(client, token, ofd["id"], rider["id"])
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "RIDER_INACTIVE"


def test_deactivation_preserves_current_assignment(client: TestClient) -> None:
    token, _ = create_org(client, "rkeep@example.com", "RKeep", "rkeep")
    rider = create_rider(client, token)
    ofd = ofd_shipment(client, token)
    assign(client, token, ofd["id"], rider["id"])
    client.post(f"/api/v1/riders/{rider['id']}/deactivate", headers=auth_header(token))
    fetched = client.get(f"/api/v1/shipments/{ofd['id']}", headers=auth_header(token)).json()
    assert fetched["rider_id"] == rider["id"]


def test_assignment_history_reassignment_duplicate_and_unassign(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "rhist@example.com", "RHist", "rhist")
    rider_a = create_rider(client, token, email="a@example.com", phone="+15551112221")
    rider_b = create_rider(client, token, email="b@example.com", phone="+15551112222")
    ofd = ofd_shipment(client, token)

    first = assign(client, token, ofd["id"], rider_a["id"], "First rider")
    assert first.status_code == 200
    duplicate = assign(client, token, ofd["id"], rider_a["id"])
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "RIDER_ALREADY_ASSIGNED"

    second = assign(client, token, ofd["id"], rider_b["id"], "Handoff")
    assert second.status_code == 200
    assert second.json()["rider_id"] == rider_b["id"]

    history = client.get(f"/api/v1/shipments/{ofd['id']}/rider-history", headers=auth_header(token))
    assert history.status_code == 200
    items = history.json()["items"]
    assert len(items) == 2
    assert items[0]["rider_id"] == rider_a["id"]
    assert items[0]["unassigned_at"]
    assert items[1]["rider_id"] == rider_b["id"]
    assert items[1]["unassigned_at"] is None
    assert [item["assigned_at"] for item in items] == sorted(item["assigned_at"] for item in items)
    active = db.query(ShipmentRiderAssignment).filter(ShipmentRiderAssignment.unassigned_at.is_(None)).count()
    assert active == 1

    unassigned = client.post(
        f"/api/v1/shipments/{ofd['id']}/unassign-rider",
        headers=auth_header(token),
        json={},
    )
    assert unassigned.status_code == 200
    assert unassigned.json()["rider_id"] is None
    history_after = client.get(
        f"/api/v1/shipments/{ofd['id']}/rider-history",
        headers=auth_header(token),
    ).json()["items"]
    assert len(history_after) == 2
    assert all(item["unassigned_at"] for item in history_after)

    none = client.post(
        f"/api/v1/shipments/{ofd['id']}/unassign-rider",
        headers=auth_header(token),
        json={},
    )
    assert none.status_code == 409

    actions = {row.action for row in db.query(AuditLog).filter(AuditLog.resource_id == ofd["id"]).all()}
    assert "RIDER_ASSIGNED_TO_SHIPMENT" in actions
    assert "RIDER_UNASSIGNED_FROM_SHIPMENT" in actions


def test_unassign_rejected_after_delivered_or_cancelled(client: TestClient) -> None:
    token, _ = create_org(client, "runass@example.com", "RUnass", "runass")
    rider = create_rider(client, token)
    ofd = ofd_shipment(client, token)
    assign(client, token, ofd["id"], rider["id"])
    walk_to(client, token, ofd["id"], ["DELIVERED"])
    delivered = client.post(
        f"/api/v1/shipments/{ofd['id']}/unassign-rider",
        headers=auth_header(token),
        json={},
    )
    assert delivered.status_code == 409
    assert delivered.json()["error"]["code"] == "SHIPMENT_NOT_UNASSIGNABLE"
    still = client.get(f"/api/v1/shipments/{ofd['id']}", headers=auth_header(token)).json()
    assert still["rider_id"] == rider["id"]

    cancelled = client.post("/api/v1/shipments", headers=auth_header(token), json=shipment_payload(reference_number="CX")).json()
    client.post(f"/api/v1/shipments/{cancelled['id']}/cancel", headers=auth_header(token), json={})
    blocked = client.post(
        f"/api/v1/shipments/{cancelled['id']}/unassign-rider",
        headers=auth_header(token),
        json={},
    )
    assert blocked.status_code == 409


def test_rider_shipment_list_filter_and_customer_still_work(client: TestClient) -> None:
    token, _ = create_org(client, "rlist@example.com", "RList", "rlist")
    rider = create_rider(client, token)
    customer = client.post("/api/v1/customers", headers=auth_header(token), json=customer_payload()).json()
    first = ofd_shipment(client, token, customer_id=customer["id"], reference_number="R1")
    second = ofd_shipment(client, token, reference_number="R2")
    assign(client, token, first["id"], rider["id"])
    assign(client, token, second["id"], rider["id"])

    listed = client.get(
        f"/api/v1/riders/{rider['id']}/shipments",
        headers=auth_header(token),
        params={"page": 1, "page_size": 1},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 2
    assert len(listed.json()["items"]) == 1
    assert all(item["rider_id"] == rider["id"] for item in listed.json()["items"])

    filtered = client.get("/api/v1/shipments", headers=auth_header(token), params={"rider_id": rider["id"]})
    assert filtered.json()["total"] == 2
    detail = client.get(f"/api/v1/customers/{customer['id']}", headers=auth_header(token)).json()
    assert detail["shipment_count"] == 1
    history = client.get(f"/api/v1/shipments/{first['id']}/history", headers=auth_header(token)).json()["items"]
    assert [item["to_status"] for item in history][-1] == "OUT_FOR_DELIVERY"


def test_staff_can_view_but_cannot_assign_or_create(client: TestClient) -> None:
    admin, _ = create_org(client, "rstaff-admin@example.com", "RStaff", "rstaff")
    staff = invite_member(client, admin, "rstaff@example.com", "STAFF")
    ops = invite_member(client, admin, "rops@example.com", "OPERATIONS_MANAGER")
    rider = create_rider(client, admin)
    ofd = ofd_shipment(client, admin)

    assert client.get("/api/v1/riders", headers=auth_header(staff)).status_code == 200
    assert client.get(f"/api/v1/riders/{rider['id']}", headers=auth_header(staff)).status_code == 200
    assert client.post("/api/v1/riders", headers=auth_header(staff), json=rider_payload(email="x@example.com")).status_code == 403
    assert client.patch(
        f"/api/v1/riders/{rider['id']}",
        headers=auth_header(staff),
        json={"name": "Nope"},
    ).status_code == 403
    assert assign(client, staff, ofd["id"], rider["id"]).status_code == 403
    assert assign(client, ops, ofd["id"], rider["id"]).status_code == 200
    assert assign(client, admin, ofd_shipment(client, admin, reference_number="ADM")["id"], rider["id"]).status_code == 200


def test_customer_role_cannot_access_riders(client: TestClient) -> None:
    admin, _ = create_org(client, "rcust-admin@example.com", "RCust", "rcust")
    rider = create_rider(client, admin)
    buyer = invite_member(client, admin, "rcust-buyer@example.com", "CUSTOMER")
    assert client.get("/api/v1/riders", headers=auth_header(buyer)).status_code == 403
    assert client.get(f"/api/v1/riders/{rider['id']}", headers=auth_header(buyer)).status_code == 403
    ofd = ofd_shipment(client, admin)
    assert assign(client, buyer, ofd["id"], rider["id"]).status_code == 403


def test_cross_tenant_rider_and_assignment_isolation(client: TestClient) -> None:
    token_a, _ = create_org(client, "riso-a@example.com", "RIso A", "riso-a")
    token_b, _ = create_org(client, "riso-b@example.com", "RIso B", "riso-b")
    rider_a = create_rider(client, token_a, email="a@example.com")
    rider_b = create_rider(client, token_b, email="b@example.com")
    ship_a = ofd_shipment(client, token_a)
    ship_b = ofd_shipment(client, token_b)

    assert client.get(f"/api/v1/riders/{rider_a['id']}", headers=auth_header(token_a)).status_code == 200
    missing = client.get(f"/api/v1/riders/{rider_b['id']}", headers=auth_header(token_a))
    assert missing.status_code == 404
    assert client.patch(
        f"/api/v1/riders/{rider_b['id']}",
        headers=auth_header(token_a),
        json={"name": "Hijack"},
    ).status_code == 404

    assert assign(client, token_a, ship_a["id"], rider_a["id"]).status_code == 200
    assert assign(client, token_a, ship_a["id"], rider_b["id"]).status_code == 404
    assert assign(client, token_a, ship_b["id"], rider_a["id"]).status_code == 404
    assert client.get(f"/api/v1/riders/{rider_b['id']}/shipments", headers=auth_header(token_a)).status_code == 404
    assert client.get(
        f"/api/v1/shipments/{ship_b['id']}/rider-history",
        headers=auth_header(token_a),
    ).status_code == 404

    listed = client.get(f"/api/v1/riders/{rider_a['id']}/shipments", headers=auth_header(token_a)).json()
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == ship_a["id"]

    assert client.get(f"/api/v1/riders/{rider_a['id']}", headers=auth_header(token_b)).status_code == 404
    assert assign(client, token_b, ship_a["id"], rider_b["id"]).status_code == 404
    assert client.get(
        f"/api/v1/shipments/{ship_a['id']}/rider-history",
        headers=auth_header(token_b),
    ).status_code == 404
