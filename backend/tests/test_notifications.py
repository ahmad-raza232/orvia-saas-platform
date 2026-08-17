from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.events import SENSITIVE_PAYLOAD_KEYS, SHIPMENT_BOOKED
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.models.outbox import OutboxEvent
from app.services.email_provider import EmailDeliveryError, EmailProvider, LoggingEmailProvider
from app.services.outbox_processor import OutboxProcessor
from tests.test_customers import customer_payload, invite_member
from tests.test_pod import pod_payload
from tests.test_shipment_operations import walk_to
from tests.test_shipments import auth_header, create_org, shipment_payload


class FailingEmailProvider(EmailProvider):
    def send(self, recipient, subject, body, metadata=None) -> None:
        raise EmailDeliveryError("smtp timeout")


def process(db: Session, provider: EmailProvider | None = None) -> int:
    return OutboxProcessor(db, provider or LoggingEmailProvider()).process_pending(limit=50)


def create_customer(client: TestClient, token: str, **overrides) -> dict:
    created = client.post(
        "/api/v1/customers",
        headers=auth_header(token),
        json=customer_payload(**overrides),
    )
    assert created.status_code == 201, created.text
    return created.json()


def booked_with_customer(client: TestClient, token: str, email: str = "buyer@example.com") -> tuple[dict, dict]:
    customer = create_customer(client, token, email=email)
    shipment = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(customer_id=customer["id"], reference_number="N8"),
    )
    assert shipment.status_code == 201, shipment.text
    return shipment.json(), customer


def test_lifecycle_events_are_tenant_scoped_and_safe(client: TestClient, db: Session) -> None:
    token, org = create_org(client, "n8-life@example.com", "N8 Life", "n8-life")
    shipment, customer = booked_with_customer(client, token)
    events = {
        row.event_type: row
        for row in db.query(OutboxEvent).filter(OutboxEvent.organization_id == org["id"]).all()
    }
    assert set(events) == {SHIPMENT_BOOKED}
    booked = events[SHIPMENT_BOOKED]
    assert booked.payload["tracking_number"] == shipment["tracking_number"]
    assert booked.payload["shipment_id"] == shipment["id"]
    assert booked.payload["customer_id"] == customer["id"]
    assert booked.payload.get("actor_user_id")
    payload_text = str(booked.payload).lower()
    for key in SENSITIVE_PAYLOAD_KEYS:
        assert key not in booked.payload
        assert key not in payload_text
    assert "1 origin street" not in payload_text
    assert "password" not in payload_text

    walk_to(client, token, shipment["id"], ["PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED"])
    types = {
        row.event_type
        for row in db.query(OutboxEvent).filter(OutboxEvent.organization_id == org["id"]).all()
    }
    assert types == {
        "SHIPMENT_BOOKED",
        "SHIPMENT_PICKED_UP",
        "SHIPMENT_IN_TRANSIT",
        "SHIPMENT_OUT_FOR_DELIVERY",
        "SHIPMENT_DELIVERED",
    }
    pod = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod",
        headers=auth_header(token),
        json=pod_payload(),
    )
    assert pod.status_code == 201, pod.text
    types = {
        row.event_type
        for row in db.query(OutboxEvent).filter(OutboxEvent.organization_id == org["id"]).all()
    }
    assert "POD_CREATED" in types

    cancelled = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(reference_number="CXL"),
    ).json()
    assert client.post(
        f"/api/v1/shipments/{cancelled['id']}/cancel",
        headers=auth_header(token),
        json={},
    ).status_code == 200
    cancel_events = (
        db.query(OutboxEvent)
        .filter(OutboxEvent.event_type == "SHIPMENT_CANCELLED", OutboxEvent.aggregate_id == cancelled["id"])
        .count()
    )
    assert cancel_events == 1

    before = db.query(OutboxEvent).count()
    bad = client.post(
        f"/api/v1/shipments/{shipment['id']}/status",
        headers=auth_header(token),
        json={"status": "DELIVERED"},
    )
    assert bad.status_code == 409
    notes = client.patch(
        f"/api/v1/shipments/{shipment['id']}",
        headers=auth_header(token),
        json={"notes": "no event"},
    )
    assert notes.status_code == 200
    client.get(f"/api/v1/shipments/{shipment['id']}", headers=auth_header(token))
    assert db.query(OutboxEvent).count() == before


def test_customer_email_sent_missing_email_skipped(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "n8-mail@example.com", "N8 Mail", "n8-mail")
    provider = LoggingEmailProvider()
    shipment, customer = booked_with_customer(client, token, email="notify-me@example.com")
    assert process(db, provider) >= 1
    sent = db.query(Notification).filter(Notification.shipment_id == shipment["id"]).one()
    assert sent.status == "SENT"
    assert sent.recipient == "notify-me@example.com"
    assert str(sent.customer_id) == customer["id"]
    assert sent.attempts == 1
    assert provider.sent[0]["recipient"] == "notify-me@example.com"
    assert shipment["tracking_number"] in provider.sent[0]["subject"]

    bare = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(reference_number="NO-CUST"),
    ).json()
    assert process(db, LoggingEmailProvider()) >= 1
    skipped = db.query(Notification).filter(Notification.shipment_id == bare["id"]).one()
    assert skipped.status == "SKIPPED"
    assert skipped.last_error == "NO_CUSTOMER"
    assert skipped.recipient is None


def test_notifications_are_idempotent_and_retries_are_bounded(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "n8-retry@example.com", "N8 Retry", "n8-retry")
    shipment, _ = booked_with_customer(client, token, email="retry@example.com")
    failing = FailingEmailProvider()
    assert process(db, failing) == 1
    first = db.query(Notification).filter(Notification.shipment_id == shipment["id"]).one()
    assert first.status == "FAILED"
    assert first.attempts == 1
    outbox = db.query(OutboxEvent).filter(OutboxEvent.event_type == SHIPMENT_BOOKED).one()
    assert outbox.status == "PENDING"
    assert outbox.attempts == 1

    assert process(db, failing) == 1
    db.refresh(first)
    db.refresh(outbox)
    assert first.attempts == 2
    assert outbox.attempts == 2
    assert outbox.status == "PENDING"

    status_before = client.get(
        f"/api/v1/shipments/{shipment['id']}", headers=auth_header(token)
    ).json()["status"]
    assert process(db, failing) == 1
    db.refresh(first)
    db.refresh(outbox)
    assert first.attempts == 3
    assert first.status == "FAILED"
    assert outbox.status == "FAILED"
    assert outbox.attempts == 3
    after = client.get(f"/api/v1/shipments/{shipment['id']}", headers=auth_header(token)).json()
    assert after["status"] == status_before == "BOOKED"

    assert process(db, LoggingEmailProvider()) == 0
    assert db.query(Notification).filter(Notification.shipment_id == shipment["id"]).count() == 1

    other, _ = booked_with_customer(client, token, email="once@example.com")
    provider = LoggingEmailProvider()
    assert process(db, provider) == 1
    assert process(db, provider) == 0
    assert db.query(Notification).filter(Notification.shipment_id == other["id"]).count() == 1
    assert db.query(Notification).filter(Notification.shipment_id == other["id"]).one().status == "SENT"


def test_notification_settings_rbac_and_disable(client: TestClient, db: Session) -> None:
    admin, org = create_org(client, "n8-set@example.com", "N8 Set", "n8-set")
    ops = invite_member(client, admin, "n8-ops@example.com", "OPERATIONS_MANAGER")
    staff = invite_member(client, admin, "n8-staff@example.com", "STAFF")
    buyer = invite_member(client, admin, "n8-buy@example.com", "CUSTOMER")
    settings = client.get("/api/v1/notifications/settings", headers=auth_header(admin))
    assert settings.status_code == 200
    assert settings.json()["email"]["shipment.booked"] is True
    assert client.get("/api/v1/notifications/settings", headers=auth_header(ops)).status_code == 200
    assert client.get("/api/v1/notifications/settings", headers=auth_header(staff)).status_code == 403
    assert client.get("/api/v1/notifications", headers=auth_header(staff)).status_code == 403
    assert client.get("/api/v1/notifications/settings", headers=auth_header(buyer)).status_code == 403
    assert client.patch(
        "/api/v1/notifications/settings",
        headers=auth_header(ops),
        json={"email": {"shipment.booked": False}},
    ).status_code == 403
    assert client.patch(
        "/api/v1/notifications/settings",
        headers=auth_header(staff),
        json={"email": {"shipment.booked": False}},
    ).status_code == 403
    updated = client.patch(
        "/api/v1/notifications/settings",
        headers=auth_header(admin),
        json={"email": {"shipment.booked": False}, "organization_id": str(org["id"])},
    )
    assert updated.status_code == 200
    assert updated.json()["email"]["shipment.booked"] is False
    assert (
        db.query(AuditLog).filter(AuditLog.action == "NOTIFICATION_SETTINGS_UPDATED").count()
        == 1
    )

    shipment, _ = booked_with_customer(client, admin, email="disabled@example.com")
    process(db, LoggingEmailProvider())
    note = db.query(Notification).filter(Notification.shipment_id == shipment["id"]).one()
    assert note.status == "SKIPPED"
    assert note.last_error == "EVENT_DISABLED"


def test_history_pagination_filters_and_cross_tenant(client: TestClient, db: Session) -> None:
    token_a, org_a = create_org(client, "n8-a@example.com", "N8 A", "n8-a")
    token_b, org_b = create_org(client, "n8-b@example.com", "N8 B", "n8-b")
    first, _ = booked_with_customer(client, token_a, email="a1@example.com")
    second, _ = booked_with_customer(client, token_a, email="a2@example.com")
    other, _ = booked_with_customer(client, token_b, email="b1@example.com")
    process(db, LoggingEmailProvider())

    listed = client.get(
        "/api/v1/notifications?page=1&page_size=1&status=SENT&channel=EMAIL&event_type=shipment.booked",
        headers=auth_header(token_a),
    )
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert body["total"] == 2
    assert len(body["items"]) == 1
    assert body["items"][0]["organization_id"] == org_a["id"]
    assert "smtp_password" not in listed.text.lower()
    assert "smtp_host" not in listed.text.lower()

    page2 = client.get(
        "/api/v1/notifications?page=2&page_size=1",
        headers=auth_header(token_a),
    ).json()
    assert page2["total"] == 2
    assert page2["items"][0]["id"] != body["items"][0]["id"]

    foreign = client.get("/api/v1/notifications", headers=auth_header(token_b)).json()
    assert foreign["total"] == 1
    assert foreign["items"][0]["organization_id"] == org_b["id"]
    assert {item["shipment_id"] for item in foreign["items"]} == {other["id"]}

    a_item = body["items"][0]["id"]
    assert client.get(f"/api/v1/notifications/{a_item}", headers=auth_header(token_b)).status_code == 404
    assert client.get(f"/api/v1/notifications/{a_item}", headers=auth_header(token_a)).status_code == 200


def test_concurrent_processing_does_not_duplicate_notification(client: TestClient, db: Session, engine) -> None:
    token, _ = create_org(client, "n8-conc@example.com", "N8 Conc", "n8-conc")
    shipment, _ = booked_with_customer(client, token, email="conc@example.com")
    db.commit()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def run() -> None:
        session = SessionLocal()
        try:
            OutboxProcessor(session, LoggingEmailProvider()).process_pending(limit=10)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: run(), range(2)))

    db.expire_all()
    assert db.query(Notification).filter(Notification.shipment_id == shipment["id"]).count() == 1
    assert (
        db.query(OutboxEvent)
        .filter(OutboxEvent.event_type == SHIPMENT_BOOKED, OutboxEvent.aggregate_id == shipment["id"])
        .count()
        == 1
    )


def test_notification_migration_upgrade_downgrade_reupgrade(engine) -> None:
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect, text

    backend_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    engine.dispose()
    try:
        command.downgrade(cfg, "007_proof_of_delivery")
        tables = set(inspect(engine).get_table_names())
        assert "outbox_events" not in tables
        assert "notifications" not in tables
        assert "notification_settings" not in tables
        command.upgrade(cfg, "head")
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert {"outbox_events", "notifications", "notification_settings"} <= tables
        command.downgrade(cfg, "007_proof_of_delivery")
        command.upgrade(cfg, "head")
        with engine.connect() as connection:
            version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert version != "007_proof_of_delivery"
    finally:
        command.upgrade(cfg, "head")
        engine.dispose()
