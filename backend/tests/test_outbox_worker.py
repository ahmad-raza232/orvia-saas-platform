from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import logging

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.notification import Notification
from app.models.outbox import OutboxEvent
from app.services.email_provider import EmailDeliveryError, LoggingEmailProvider, SmtpEmailProvider
from app.services.outbox_processor import OutboxProcessor
from app.worker import OutboxWorker, main as worker_main
from tests.test_notifications import FailingEmailProvider, booked_with_customer, process
from tests.test_shipments import auth_header, create_org


FROZEN = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)


def test_worker_processes_pending_event_to_sent(client: TestClient, db: Session, engine) -> None:
    token, _ = create_org(client, "n9-worker@example.com", "N9 Worker", "n9-worker")
    shipment, _ = booked_with_customer(client, token, email="n9-worker@example.com")
    db.commit()
    provider = LoggingEmailProvider()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    processed = OutboxWorker(SessionLocal, provider).run_once()
    assert processed >= 1
    db.expire_all()
    event = db.query(OutboxEvent).filter(OutboxEvent.aggregate_id == shipment["id"]).one()
    note = db.query(Notification).filter(Notification.shipment_id == shipment["id"]).one()
    assert event.status == "PROCESSED"
    assert note.status == "SENT"
    assert provider.sent
    assert shipment["tracking_number"] in provider.sent[0]["subject"]


def test_failed_smtp_retries_with_exponential_backoff(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "n9-back@example.com", "N9 Back", "n9-back")
    shipment, _ = booked_with_customer(client, token, email="n9-back@example.com")
    event = db.query(OutboxEvent).filter(OutboxEvent.aggregate_id == shipment["id"]).one()
    event.available_at = FROZEN
    db.commit()
    clock = {"now": FROZEN}

    def now() -> datetime:
        return clock["now"]

    processor = OutboxProcessor(
        db, FailingEmailProvider(), retry_base_seconds=10, max_attempts=3, clock=now
    )
    assert processor.process_pending(limit=10) == 1
    event = db.query(OutboxEvent).filter(OutboxEvent.aggregate_id == shipment["id"]).one()
    assert event.status == "PENDING"
    assert event.attempts == 1
    assert event.available_at == FROZEN + timedelta(seconds=10)

    assert processor.process_pending(limit=10) == 0
    clock["now"] = FROZEN + timedelta(seconds=10)
    assert processor.process_pending(limit=10) == 1
    db.refresh(event)
    assert event.attempts == 2
    assert event.status == "PENDING"
    assert event.available_at == FROZEN + timedelta(seconds=30)

    clock["now"] = FROZEN + timedelta(seconds=30)
    assert processor.process_pending(limit=10) == 1
    db.refresh(event)
    note = db.query(Notification).filter(Notification.shipment_id == shipment["id"]).one()
    assert event.status == "FAILED"
    assert note.status == "FAILED"
    assert event.attempts == 3
    assert note.attempts == 3


def test_stuck_processing_is_recovered_and_processed(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "n9-stuck@example.com", "N9 Stuck", "n9-stuck")
    shipment, _ = booked_with_customer(client, token, email="n9-stuck@example.com")
    event = db.query(OutboxEvent).filter(OutboxEvent.aggregate_id == shipment["id"]).one()
    event.status = "PROCESSING"
    event.processing_started_at = FROZEN
    event.available_at = FROZEN
    db.commit()

    clock = {"now": FROZEN + timedelta(seconds=301)}
    provider = LoggingEmailProvider()
    processor = OutboxProcessor(
        db,
        provider,
        processing_timeout_seconds=300,
        clock=lambda: clock["now"],
    )
    assert processor.process_pending(limit=10) == 1
    db.expire_all()
    event = db.query(OutboxEvent).filter(OutboxEvent.aggregate_id == shipment["id"]).one()
    note = db.query(Notification).filter(Notification.shipment_id == shipment["id"]).one()
    assert event.status == "PROCESSED"
    assert note.status == "SENT"
    assert event.processing_started_at is None
    assert provider.sent


def test_concurrent_workers_do_not_double_claim(client: TestClient, db: Session, engine) -> None:
    token, _ = create_org(client, "n9-conc@example.com", "N9 Conc", "n9-conc")
    shipment, _ = booked_with_customer(client, token, email="n9-conc@example.com")
    db.commit()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def run() -> None:
        OutboxWorker(SessionLocal, LoggingEmailProvider()).run_once()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: run(), range(2)))

    db.expire_all()
    assert db.query(Notification).filter(Notification.shipment_id == shipment["id"]).count() == 1
    assert (
        db.query(OutboxEvent)
        .filter(OutboxEvent.aggregate_id == shipment["id"])
        .count()
        == 1
    )


def test_duplicate_event_does_not_duplicate_notification(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "n9-dup@example.com", "N9 Dup", "n9-dup")
    shipment, _ = booked_with_customer(client, token, email="n9-dup@example.com")
    provider = LoggingEmailProvider()
    assert process(db, provider) == 1
    assert process(db, provider) == 0
    assert db.query(Notification).filter(Notification.shipment_id == shipment["id"]).count() == 1
    assert db.query(OutboxEvent).filter(OutboxEvent.aggregate_id == shipment["id"]).count() == 1


def test_logging_provider_still_works_without_smtp(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "n9-log@example.com", "N9 Log", "n9-log")
    shipment, _ = booked_with_customer(client, token, email="n9-log@example.com")
    provider = LoggingEmailProvider()
    OutboxProcessor(db, provider).process_pending(limit=10)
    note = db.query(Notification).filter(Notification.shipment_id == shipment["id"]).one()
    assert note.status == "SENT"
    assert provider.sent[0]["recipient"] == "n9-log@example.com"


def test_smtp_configuration_validation_and_password_not_logged(monkeypatch, caplog) -> None:
    monkeypatch.setattr(settings, "smtp_host", None)
    monkeypatch.setattr(settings, "smtp_from_email", None)
    monkeypatch.setattr(settings, "smtp_from", "")
    monkeypatch.setattr(settings, "smtp_password", "super-secret-smtp-password")
    with caplog.at_level(logging.DEBUG):
        try:
            SmtpEmailProvider().send("buyer@example.com", "Hello", "Body")
            raise AssertionError("expected EmailDeliveryError")
        except EmailDeliveryError as exc:
            assert "SMTP_HOST" in str(exc)
            assert "super-secret-smtp-password" not in str(exc)
    assert "super-secret-smtp-password" not in caplog.text
    assert "super-secret-smtp-password" not in repr(settings)

    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_from_email", "noreply@example.com")

    class Boom:
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("auth failed super-secret-smtp-password")

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

    monkeypatch.setattr("app.services.email_provider.smtplib.SMTP", Boom)
    with caplog.at_level(logging.DEBUG):
        try:
            SmtpEmailProvider().send("buyer@example.com", "Hello", "Body")
            raise AssertionError("expected EmailDeliveryError")
        except EmailDeliveryError as exc:
            assert str(exc) == "Email delivery failed."
            assert "super-secret-smtp-password" not in str(exc)
    assert "super-secret-smtp-password" not in caplog.text


def test_worker_tenant_isolation_and_graceful_stop(client: TestClient, db: Session, engine) -> None:
    token_a, org_a = create_org(client, "n9-iso-a@example.com", "N9 Iso A", "n9-iso-a")
    token_b, org_b = create_org(client, "n9-iso-b@example.com", "N9 Iso B", "n9-iso-b")
    ship_a, _ = booked_with_customer(client, token_a, email="a@example.com")
    ship_b, _ = booked_with_customer(client, token_b, email="b@example.com")
    provider = LoggingEmailProvider()
    OutboxProcessor(db, provider).process_pending(limit=50)
    notes = db.query(Notification).all()
    assert {str(note.organization_id) for note in notes} == {org_a["id"], org_b["id"]}
    listed_a = client.get("/api/v1/notifications", headers=auth_header(token_a)).json()
    listed_b = client.get("/api/v1/notifications", headers=auth_header(token_b)).json()
    assert listed_a["total"] == 1
    assert listed_b["total"] == 1
    assert listed_a["items"][0]["shipment_id"] == ship_a["id"]
    assert listed_b["items"][0]["shipment_id"] == ship_b["id"]

    worker = OutboxWorker(
        sessionmaker(bind=engine, autoflush=False, autocommit=False),
        LoggingEmailProvider(),
        poll_interval_seconds=30,
    )
    worker.stop()
    worker.run_forever()
    assert worker._stop.is_set()


def test_poison_processor_error_is_bounded_by_max_attempts(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "n9-poison@example.com", "N9 Poison", "n9-poison")
    shipment, _ = booked_with_customer(client, token, email="n9-poison@example.com")
    event = db.query(OutboxEvent).filter(OutboxEvent.aggregate_id == shipment["id"]).one()
    event.available_at = FROZEN
    db.commit()
    clock = {"now": FROZEN}

    class ExplodingProcessor(OutboxProcessor):
        def _process_event(self, event, *, now):
            raise RuntimeError("poison payload")

    processor = ExplodingProcessor(
        db, LoggingEmailProvider(), retry_base_seconds=10, max_attempts=3, clock=lambda: clock["now"]
    )
    assert processor.process_pending(limit=10) == 1
    db.refresh(event)
    assert event.status == "PENDING"
    assert event.attempts == 1
    assert event.last_error == "PROCESSOR_ERROR"
    assert event.available_at == FROZEN + timedelta(seconds=10)

    clock["now"] = FROZEN + timedelta(seconds=10)
    assert processor.process_pending(limit=10) == 1
    db.refresh(event)
    assert event.attempts == 2
    clock["now"] = FROZEN + timedelta(seconds=40)
    assert processor.process_pending(limit=10) == 1
    db.refresh(event)
    assert event.status == "FAILED"
    assert event.attempts == 3


def test_worker_main_exits_when_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "outbox_worker_enabled", False)
    assert settings.outbox_worker_enabled is False
    worker_main()


def test_outbox_worker_migration_upgrade_downgrade_reupgrade(engine) -> None:
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect, text

    backend_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    engine.dispose()
    try:
        command.downgrade(cfg, "008_notifications_and_outbox")
        columns = {column["name"] for column in inspect(engine).get_columns("outbox_events")}
        assert "processing_started_at" not in columns
        command.upgrade(cfg, "head")
        columns = {column["name"] for column in inspect(engine).get_columns("outbox_events")}
        assert "processing_started_at" in columns
        command.downgrade(cfg, "008_notifications_and_outbox")
        command.upgrade(cfg, "head")
        with engine.connect() as connection:
            version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert version != "008_notifications_and_outbox"
    finally:
        command.upgrade(cfg, "head")
        engine.dispose()
