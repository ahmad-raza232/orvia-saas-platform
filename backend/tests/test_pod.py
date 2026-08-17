from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from tests.test_customers import invite_member
from tests.test_riders import assign, create_rider, ofd_shipment
from tests.test_shipment_operations import walk_to
from tests.test_shipments import auth_header, create_org, shipment_payload


def delivered_shipment(client: TestClient, token: str, **overrides) -> dict:
    ofd = ofd_shipment(client, token, **overrides)
    walk_to(client, token, ofd["id"], ["DELIVERED"])
    return client.get(f"/api/v1/shipments/{ofd['id']}", headers=auth_header(token)).json()


def pod_payload(**overrides) -> dict:
    payload = {
        "recipient_name": "Ben Receiver",
        "delivery_note": "Left with security",
        "signature": {
            "file_name": "signature.png",
            "mime_type": "image/png",
            "storage_key": "pods/demo/signature.png",
            "url": "https://storage.example.com/pods/demo/signature.png",
            "file_size": 2048,
            "checksum": "a" * 64,
        },
        "photo": {
            "file_name": "door.jpg",
            "mime_type": "image/jpeg",
            "storage_key": "pods/demo/door.jpg",
            "file_size": 4096,
        },
    }
    payload.update(overrides)
    return payload


def test_tenant_admin_and_ops_manager_can_create_pod(client: TestClient, db: Session) -> None:
    admin, _ = create_org(client, "pod-admin@example.com", "POD Admin", "pod-admin")
    ops = invite_member(client, admin, "pod-ops@example.com", "OPERATIONS_MANAGER")
    me = client.get("/api/v1/auth/me", headers=auth_header(admin)).json()
    shipment = delivered_shipment(client, admin, reference_number="POD-ADMIN")
    created = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod",
        headers=auth_header(admin),
        json=pod_payload(organization_id="ignored", recorded_by_user_id="ignored", delivered_at="2000-01-01T00:00:00Z"),
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["shipment_id"] == shipment["id"]
    assert body["recorded_by_user_id"] == me["user"]["id"]
    assert body["delivered_at"] == shipment["delivered_at"]
    assert body["has_signature"] is True
    assert body["has_photo"] is True
    assert body["rider_id"] is None
    assert "javascript" not in (body["signature"]["url"] or "")

    fetched = client.get(f"/api/v1/shipments/{shipment['id']}/pod", headers=auth_header(admin))
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]

    detail = client.get(f"/api/v1/shipments/{shipment['id']}", headers=auth_header(admin)).json()
    assert detail["pod"]["pod_id"] == body["id"]
    assert detail["pod"]["recipient_name"] == "Ben Receiver"
    assert "signature_storage_key" not in detail["pod"]

    duplicate = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod",
        headers=auth_header(admin),
        json=pod_payload(),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "POD_ALREADY_EXISTS"

    audit = (
        db.query(AuditLog)
        .filter(AuditLog.action == "POD_CREATED", AuditLog.resource_id == body["id"])
        .one()
    )
    assert audit.details["shipment_id"] == shipment["id"]
    assert audit.details["tracking_number"] == shipment["tracking_number"]
    assert audit.details["recipient_name"] == "Ben Receiver"
    assert "signature" not in audit.details
    assert "photo" not in audit.details
    assert "storage_key" not in str(audit.details)

    unchanged = client.get(f"/api/v1/shipments/{shipment['id']}", headers=auth_header(admin)).json()
    assert unchanged["delivered_at"] == shipment["delivered_at"]

    ops_ship = delivered_shipment(client, ops, reference_number="POD-OPS")
    assert client.post(
        f"/api/v1/shipments/{ops_ship['id']}/pod",
        headers=auth_header(ops),
        json=pod_payload(),
    ).status_code == 201


def test_staff_and_customer_cannot_create_pod(client: TestClient) -> None:
    admin, _ = create_org(client, "pod-roles@example.com", "POD Roles", "pod-roles")
    staff = invite_member(client, admin, "pod-staff@example.com", "STAFF")
    buyer = invite_member(client, admin, "pod-buyer@example.com", "CUSTOMER")
    shipment = delivered_shipment(client, admin)
    assert client.post(
        f"/api/v1/shipments/{shipment['id']}/pod",
        headers=auth_header(staff),
        json=pod_payload(),
    ).status_code == 403
    assert client.post(
        f"/api/v1/shipments/{shipment['id']}/pod",
        headers=auth_header(buyer),
        json=pod_payload(),
    ).status_code == 403
    created = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod",
        headers=auth_header(admin),
        json=pod_payload(),
    )
    assert created.status_code == 201
    assert client.get(
        f"/api/v1/shipments/{shipment['id']}/pod",
        headers=auth_header(staff),
    ).status_code == 200
    assert client.get(
        f"/api/v1/shipments/{shipment['id']}/pod",
        headers=auth_header(buyer),
    ).status_code == 403


def test_pod_only_when_delivered(client: TestClient) -> None:
    token, _ = create_org(client, "pod-status@example.com", "POD Status", "pod-status")
    booked = client.post("/api/v1/shipments", headers=auth_header(token), json=shipment_payload()).json()
    assert client.get(f"/api/v1/shipments/{booked['id']}/pod", headers=auth_header(token)).status_code == 404
    cancelled = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(reference_number="CXL"),
    ).json()
    client.post(f"/api/v1/shipments/{cancelled['id']}/cancel", headers=auth_header(token), json={})
    walking = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(reference_number="WALK"),
    ).json()
    for status in ["PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY"]:
        walk_to(client, token, walking["id"], [status])
        response = client.post(
            f"/api/v1/shipments/{walking['id']}/pod",
            headers=auth_header(token),
            json=pod_payload(),
        )
        assert response.status_code == 409, status
        assert response.json()["error"]["code"] == "POD_NOT_ALLOWED"
    for shipment_id in [booked["id"], cancelled["id"]]:
        response = client.post(
            f"/api/v1/shipments/{shipment_id}/pod",
            headers=auth_header(token),
            json=pod_payload(),
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "POD_NOT_ALLOWED"


def test_pod_is_immutable_and_has_no_mutation_endpoints(client: TestClient) -> None:
    token, _ = create_org(client, "pod-immut@example.com", "POD Immut", "pod-immut")
    shipment = delivered_shipment(client, token)
    created = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod",
        headers=auth_header(token),
        json=pod_payload(),
    )
    assert created.status_code == 201
    url = f"/api/v1/shipments/{shipment['id']}/pod"
    assert client.patch(url, headers=auth_header(token), json={"recipient_name": "Nope"}).status_code == 405
    assert client.delete(url, headers=auth_header(token)).status_code == 405


def test_pod_preserves_rider_and_works_without_one(client: TestClient) -> None:
    token, _ = create_org(client, "pod-rider@example.com", "POD Rider", "pod-rider")
    rider = create_rider(client, token)
    ofd = ofd_shipment(client, token, reference_number="WITH-RIDER")
    assign(client, token, ofd["id"], rider["id"])
    walk_to(client, token, ofd["id"], ["DELIVERED"])
    with_rider = client.post(
        f"/api/v1/shipments/{ofd['id']}/pod",
        headers=auth_header(token),
        json=pod_payload(),
    )
    assert with_rider.status_code == 201
    assert with_rider.json()["rider_id"] == rider["id"]
    assert with_rider.json()["rider_code"] == rider["rider_code"]
    assert with_rider.json()["rider_name"] == rider["name"]

    bare = delivered_shipment(client, token, reference_number="NO-RIDER")
    without = client.post(
        f"/api/v1/shipments/{bare['id']}/pod",
        headers=auth_header(token),
        json={"recipient_name": "No Rider"},
    )
    assert without.status_code == 201
    assert without.json()["rider_id"] is None
    assert without.json()["has_signature"] is False


def test_pod_metadata_validation(client: TestClient) -> None:
    token, _ = create_org(client, "pod-meta@example.com", "POD Meta", "pod-meta")
    shipment = delivered_shipment(client, token)
    bad_mime = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod",
        headers=auth_header(token),
        json=pod_payload(signature={"file_name": "x.png", "mime_type": "text/html", "storage_key": "pods/x"}),
    )
    assert bad_mime.status_code == 422
    bad_url = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod",
        headers=auth_header(token),
        json=pod_payload(
            signature={
                "file_name": "x.png",
                "mime_type": "image/png",
                "storage_key": "pods/x",
                "url": "javascript:alert(1)",
            }
        ),
    )
    assert bad_url.status_code == 422
    traversal = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod",
        headers=auth_header(token),
        json=pod_payload(
            photo={"file_name": "../secret.png", "mime_type": "image/png", "storage_key": "pods/x"}
        ),
    )
    assert traversal.status_code == 422


def test_cross_tenant_pod_isolation(client: TestClient) -> None:
    token_a, _ = create_org(client, "pod-iso-a@example.com", "POD Iso A", "pod-iso-a")
    token_b, _ = create_org(client, "pod-iso-b@example.com", "POD Iso B", "pod-iso-b")
    ship_a = delivered_shipment(client, token_a)
    ship_b = delivered_shipment(client, token_b)
    created = client.post(
        f"/api/v1/shipments/{ship_a['id']}/pod",
        headers=auth_header(token_a),
        json=pod_payload(),
    )
    assert created.status_code == 201
    assert client.get(f"/api/v1/shipments/{ship_a['id']}/pod", headers=auth_header(token_a)).status_code == 200
    missing_get = client.get(f"/api/v1/shipments/{ship_a['id']}/pod", headers=auth_header(token_b))
    assert missing_get.status_code == 404
    missing_post = client.post(
        f"/api/v1/shipments/{ship_a['id']}/pod",
        headers=auth_header(token_b),
        json=pod_payload(),
    )
    assert missing_post.status_code == 404
    assert client.get(f"/api/v1/shipments/{ship_b['id']}/pod", headers=auth_header(token_a)).status_code == 404
    assert client.post(
        f"/api/v1/shipments/{ship_b['id']}/pod",
        headers=auth_header(token_a),
        json=pod_payload(),
    ).status_code == 404


def test_pod_migration_upgrade_and_downgrade(engine) -> None:
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect, text

    backend_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    engine.dispose()
    try:
        command.downgrade(cfg, "006_riders_and_assignments")
        assert "proof_of_deliveries" not in inspect(engine).get_table_names()
        command.upgrade(cfg, "head")
        inspector = inspect(engine)
        assert "proof_of_deliveries" in inspector.get_table_names()
        index_names = {index["name"] for index in inspector.get_indexes("proof_of_deliveries")}
        assert "uq_pod_shipment_id" in index_names
        assert "ix_pod_organization_id" in index_names
        with engine.connect() as connection:
            version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert version != "006_riders_and_assignments"
    finally:
        command.upgrade(cfg, "head")
        engine.dispose()
