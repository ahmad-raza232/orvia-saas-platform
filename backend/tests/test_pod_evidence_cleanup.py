from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import time

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.pod_evidence import PodEvidence, PodEvidenceStatus
from app.services.pod_evidence_cleanup import expire_stale_pending_evidence
from app.services.storage_provider import MemoryStorageProvider, get_memory_storage
from app.worker import OutboxWorker, main as worker_main
from tests.test_pod_storage import create_delivered_pod, simulate_client_upload, upload_payload
from tests.test_shipments import auth_header, create_org


def _request_pending(client: TestClient, token: str, shipment_id: str) -> dict:
    response = client.post(
        f"/api/v1/shipments/{shipment_id}/pod/uploads",
        headers=auth_header(token),
        json=upload_payload(),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _age_pending(db: Session, evidence_id: str, *, older_than_seconds: int) -> PodEvidence:
    row = db.get(PodEvidence, evidence_id)
    assert row is not None
    row.created_at = datetime.now(timezone.utc) - timedelta(seconds=older_than_seconds)
    db.commit()
    db.refresh(row)
    return row


def test_stale_pending_expires_after_ttl(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "c11-ttl@example.com", "C11 TTL", "c11-ttl")
    shipment, _ = create_delivered_pod(client, token)
    pending = _request_pending(client, token, shipment["id"])
    created_before = _age_pending(db, pending["upload_id"], older_than_seconds=120).created_at
    now = datetime.now(timezone.utc)
    result = expire_stale_pending_evidence(db, ttl_seconds=60, batch_size=100, now=now)
    assert result["scanned"] == 1
    assert result["expired"] == 1
    assert result["skipped"] == 0
    db.expire_all()
    row = db.get(PodEvidence, pending["upload_id"])
    assert row is not None
    assert row.status == PodEvidenceStatus.EXPIRED.value
    assert row.expired_at == now
    assert row.created_at == created_before
    assert row.uploaded_at is None
    audit = (
        db.query(AuditLog)
        .filter(AuditLog.action == "POD_EVIDENCE_EXPIRED", AuditLog.resource_id == pending["upload_id"])
        .one()
    )
    assert audit.organization_id is not None
    assert audit.details["evidence_id"] == pending["upload_id"]
    assert audit.details["tracking_number"] == shipment["tracking_number"]
    assert "upload_url" not in str(audit.details)
    assert "download_url" not in str(audit.details)


def test_recent_pending_is_not_expired(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "c11-recent@example.com", "C11 Recent", "c11-recent")
    shipment, _ = create_delivered_pod(client, token)
    pending = _request_pending(client, token, shipment["id"])
    result = expire_stale_pending_evidence(db, ttl_seconds=86_400, batch_size=100)
    assert result["expired"] == 0
    row = db.get(PodEvidence, pending["upload_id"])
    assert row is not None
    assert row.status == PodEvidenceStatus.PENDING.value
    assert row.expired_at is None


def test_uploaded_and_failed_are_never_expired(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "c11-term@example.com", "C11 Term", "c11-term")
    shipment, _ = create_delivered_pod(client, token)
    uploaded_req = _request_pending(client, token, shipment["id"])
    simulate_client_upload(uploaded_req["object_key"], "image/png", 12345)
    completed = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads/{uploaded_req['upload_id']}/complete",
        headers=auth_header(token),
    )
    assert completed.status_code == 200
    failed_req = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads",
        headers=auth_header(token),
        json=upload_payload(type="DELIVERY_PHOTO", filename="door.png", content_type="image/png"),
    ).json()
    client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads/{failed_req['upload_id']}/complete",
        headers=auth_header(token),
    )
    uploaded_row = _age_pending(db, uploaded_req["upload_id"], older_than_seconds=120)
    uploaded_at = uploaded_row.uploaded_at
    created_uploaded = uploaded_row.created_at
    failed_row = _age_pending(db, failed_req["upload_id"], older_than_seconds=120)
    created_failed = failed_row.created_at
    result = expire_stale_pending_evidence(db, ttl_seconds=60, batch_size=100)
    assert result["expired"] == 0
    db.expire_all()
    uploaded = db.get(PodEvidence, uploaded_req["upload_id"])
    failed = db.get(PodEvidence, failed_req["upload_id"])
    assert uploaded is not None and uploaded.status == PodEvidenceStatus.UPLOADED.value
    assert uploaded.uploaded_at == uploaded_at
    assert uploaded.created_at == created_uploaded
    assert uploaded.expired_at is None
    assert failed is not None and failed.status == PodEvidenceStatus.FAILED.value
    assert failed.created_at == created_failed
    assert failed.expired_at is None
    assert db.query(AuditLog).filter(AuditLog.action == "POD_EVIDENCE_EXPIRED").count() == 0


def test_expired_cleanup_is_idempotent(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "c11-idemp@example.com", "C11 Idemp", "c11-idemp")
    shipment, _ = create_delivered_pod(client, token)
    pending = _request_pending(client, token, shipment["id"])
    _age_pending(db, pending["upload_id"], older_than_seconds=120)
    first_now = datetime.now(timezone.utc)
    first = expire_stale_pending_evidence(db, ttl_seconds=60, now=first_now)
    assert first["expired"] == 1
    row = db.get(PodEvidence, pending["upload_id"])
    assert row is not None
    expired_at = row.expired_at
    second = expire_stale_pending_evidence(
        db, ttl_seconds=60, now=first_now + timedelta(days=1)
    )
    assert second["expired"] == 0
    db.expire_all()
    row = db.get(PodEvidence, pending["upload_id"])
    assert row is not None
    assert row.status == PodEvidenceStatus.EXPIRED.value
    assert row.expired_at == expired_at
    assert (
        db.query(AuditLog)
        .filter(AuditLog.action == "POD_EVIDENCE_EXPIRED", AuditLog.resource_id == pending["upload_id"])
        .count()
        == 1
    )


def test_cleanup_respects_batch_size_across_runs(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "c11-batch@example.com", "C11 Batch", "c11-batch")
    shipment, _ = create_delivered_pod(client, token)
    ids = []
    for index in range(3):
        pending = client.post(
            f"/api/v1/shipments/{shipment['id']}/pod/uploads",
            headers=auth_header(token),
            json=upload_payload(filename=f"sign-{index}.png"),
        ).json()
        ids.append(pending["upload_id"])
        _age_pending(db, pending["upload_id"], older_than_seconds=120)
    first = expire_stale_pending_evidence(db, ttl_seconds=60, batch_size=2)
    assert first["scanned"] == 2
    assert first["expired"] == 2
    remaining = [db.get(PodEvidence, item_id) for item_id in ids]
    assert sum(1 for row in remaining if row is not None and row.status == "PENDING") == 1
    second = expire_stale_pending_evidence(db, ttl_seconds=60, batch_size=2)
    assert second["expired"] == 1
    db.expire_all()
    assert all(
        db.get(PodEvidence, item_id).status == PodEvidenceStatus.EXPIRED.value for item_id in ids
    )


def test_concurrent_cleanup_does_not_double_expire(client: TestClient, db: Session, engine) -> None:
    token, _ = create_org(client, "c11-conc@example.com", "C11 Conc", "c11-conc")
    shipment, _ = create_delivered_pod(client, token)
    pending = _request_pending(client, token, shipment["id"])
    _age_pending(db, pending["upload_id"], older_than_seconds=120)
    db.commit()
    db.rollback()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def run() -> dict[str, int]:
        session = SessionLocal()
        try:
            return expire_stale_pending_evidence(session, ttl_seconds=60, batch_size=100)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sum(item["expired"] for item in results) == 1
    db.expire_all()
    row = db.get(PodEvidence, pending["upload_id"])
    assert row is not None
    assert row.status == PodEvidenceStatus.EXPIRED.value
    assert (
        db.query(AuditLog)
        .filter(AuditLog.action == "POD_EVIDENCE_EXPIRED", AuditLog.resource_id == pending["upload_id"])
        .count()
        == 1
    )


def test_expired_evidence_cannot_be_completed_or_downloaded(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "c11-api@example.com", "C11 API", "c11-api")
    shipment, _ = create_delivered_pod(client, token)
    pending = _request_pending(client, token, shipment["id"])
    simulate_client_upload(pending["object_key"], "image/png", 12345)
    _age_pending(db, pending["upload_id"], older_than_seconds=120)
    expire_stale_pending_evidence(db, ttl_seconds=60)
    completed = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads/{pending['upload_id']}/complete",
        headers=auth_header(token),
    )
    assert completed.status_code == 409
    assert completed.json()["error"]["code"] == "POD_EVIDENCE_EXPIRED"
    downloaded = client.get(
        f"/api/v1/shipments/{shipment['id']}/pod/evidence/{pending['upload_id']}/download",
        headers=auth_header(token),
    )
    assert downloaded.status_code == 409
    assert downloaded.json()["error"]["code"] == "POD_EVIDENCE_EXPIRED"
    db.expire_all()
    row = db.get(PodEvidence, pending["upload_id"])
    assert row is not None
    assert row.status == PodEvidenceStatus.EXPIRED.value


def test_cleanup_keeps_tenant_isolation(client: TestClient, db: Session) -> None:
    token_a, org_a = create_org(client, "c11-iso-a@example.com", "C11 Iso A", "c11-iso-a")
    token_b, org_b = create_org(client, "c11-iso-b@example.com", "C11 Iso B", "c11-iso-b")
    ship_a, _ = create_delivered_pod(client, token_a, reference_number="C11-A")
    ship_b, _ = create_delivered_pod(client, token_b, reference_number="C11-B")
    pending_a = _request_pending(client, token_a, ship_a["id"])
    pending_b = _request_pending(client, token_b, ship_b["id"])
    _age_pending(db, pending_a["upload_id"], older_than_seconds=120)
    _age_pending(db, pending_b["upload_id"], older_than_seconds=120)
    expire_stale_pending_evidence(db, ttl_seconds=60)
    row_a = db.get(PodEvidence, pending_a["upload_id"])
    row_b = db.get(PodEvidence, pending_b["upload_id"])
    assert row_a is not None and str(row_a.organization_id) == org_a["id"]
    assert row_b is not None and str(row_b.organization_id) == org_b["id"]
    assert client.post(
        f"/api/v1/shipments/{ship_a['id']}/pod/uploads/{pending_a['upload_id']}/complete",
        headers=auth_header(token_b),
    ).status_code == 404
    assert client.get(
        f"/api/v1/shipments/{ship_a['id']}/pod/evidence/{pending_a['upload_id']}/download",
        headers=auth_header(token_b),
    ).status_code == 404
    audits = db.query(AuditLog).filter(AuditLog.action == "POD_EVIDENCE_EXPIRED").all()
    orgs = {str(item.organization_id) for item in audits}
    assert orgs == {org_a["id"], org_b["id"]}


def test_cleanup_does_not_delete_storage_objects(client: TestClient, db: Session, monkeypatch) -> None:
    token, _ = create_org(client, "c11-store@example.com", "C11 Store", "c11-store")
    shipment, _ = create_delivered_pod(client, token)
    pending = _request_pending(client, token, shipment["id"])
    simulate_client_upload(pending["object_key"], "image/png", 12345)
    deletes: list[str] = []
    original = MemoryStorageProvider.delete_object

    def spy(self: MemoryStorageProvider, key: str) -> None:
        deletes.append(key)
        original(self, key)

    monkeypatch.setattr(MemoryStorageProvider, "delete_object", spy)
    _age_pending(db, pending["upload_id"], older_than_seconds=120)
    expire_stale_pending_evidence(db, ttl_seconds=60)
    assert deletes == []
    assert get_memory_storage().head_object(pending["object_key"]) is not None


def test_worker_continues_if_cleanup_raises(monkeypatch) -> None:
    monkeypatch.setattr(settings, "outbox_worker_enabled", True)
    monkeypatch.setattr(settings, "pod_evidence_cleanup_enabled", True)
    monkeypatch.setattr(settings, "pod_evidence_cleanup_interval_seconds", 0)
    calls = {"outbox": 0, "cleanup": 0}

    def ok_outbox(self: OutboxWorker) -> int:
        calls["outbox"] += 1
        return 1

    def boom(self: OutboxWorker) -> dict[str, int]:
        calls["cleanup"] += 1
        raise RuntimeError("cleanup exploded")

    monkeypatch.setattr(OutboxWorker, "run_once", ok_outbox)
    monkeypatch.setattr(OutboxWorker, "run_cleanup_once", boom)
    worker = OutboxWorker()
    worker.run_cycle()
    worker.run_cycle()
    assert calls["outbox"] == 2
    assert calls["cleanup"] == 2


def test_worker_cleanup_configuration_and_interval(monkeypatch) -> None:
    monkeypatch.setattr(settings, "pod_evidence_cleanup_enabled", False)
    worker = OutboxWorker()
    assert worker.maybe_run_cleanup() is None
    monkeypatch.setattr(settings, "pod_evidence_cleanup_enabled", True)
    monkeypatch.setattr(settings, "pod_evidence_cleanup_interval_seconds", 3600)
    calls = {"cleanup": 0}

    def fake_cleanup(self: OutboxWorker) -> dict[str, int]:
        calls["cleanup"] += 1
        return {"scanned": 0, "expired": 0, "skipped": 0}

    monkeypatch.setattr(OutboxWorker, "run_cleanup_once", fake_cleanup)
    assert worker.maybe_run_cleanup() == {"scanned": 0, "expired": 0, "skipped": 0}
    assert worker.maybe_run_cleanup() is None
    worker._last_cleanup_monotonic = time.monotonic() - 3601
    assert worker.maybe_run_cleanup() is not None
    assert calls["cleanup"] == 2
    assert settings.pod_evidence_pending_ttl_seconds == 86_400
    assert settings.pod_evidence_cleanup_batch_size == 100


def test_worker_starts_and_disabled_outbox_still_exits(monkeypatch) -> None:
    worker = OutboxWorker()
    worker.stop()
    worker.run_forever()
    assert worker._stop.is_set()
    monkeypatch.setattr(settings, "outbox_worker_enabled", False)
    worker_main()


def test_cleanup_uses_configured_batch_size(client: TestClient, db: Session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "pod_evidence_cleanup_batch_size", 1)
    monkeypatch.setattr(settings, "pod_evidence_pending_ttl_seconds", 60)
    token, _ = create_org(client, "c11-cfg@example.com", "C11 Cfg", "c11-cfg")
    shipment, _ = create_delivered_pod(client, token)
    first = _request_pending(client, token, shipment["id"])
    second = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads",
        headers=auth_header(token),
        json=upload_payload(filename="two.png"),
    ).json()
    _age_pending(db, first["upload_id"], older_than_seconds=120)
    _age_pending(db, second["upload_id"], older_than_seconds=120)
    result = expire_stale_pending_evidence(db)
    assert result["scanned"] == 1
    assert result["expired"] == 1


def test_no_public_expire_endpoint(client: TestClient) -> None:
    token, _ = create_org(client, "c11-http@example.com", "C11 HTTP", "c11-http")
    shipment, _ = create_delivered_pod(client, token)
    pending = _request_pending(client, token, shipment["id"])
    for method, path in (
        ("POST", f"/api/v1/shipments/{shipment['id']}/pod/evidence/{pending['upload_id']}/expire"),
        ("POST", "/api/v1/pod-evidence/cleanup"),
        ("DELETE", f"/api/v1/shipments/{shipment['id']}/pod/evidence/{pending['upload_id']}"),
    ):
        response = client.request(method, path, headers=auth_header(token))
        assert response.status_code in {404, 405}


def test_pod_evidence_cleanup_migration_upgrade_downgrade_reupgrade(engine) -> None:
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect, text

    backend_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    engine.dispose()
    try:
        command.downgrade(cfg, "010_pod_object_storage")
        columns = {column["name"] for column in inspect(engine).get_columns("pod_evidence")}
        assert "expired_at" not in columns
        command.upgrade(cfg, "head")
        inspector = inspect(engine)
        columns = {column["name"] for column in inspector.get_columns("pod_evidence")}
        assert "expired_at" in columns
        index_names = {index["name"] for index in inspector.get_indexes("pod_evidence")}
        assert "ix_pod_evidence_status_created_at" in index_names
        command.downgrade(cfg, "010_pod_object_storage")
        columns = {column["name"] for column in inspect(engine).get_columns("pod_evidence")}
        assert "expired_at" not in columns
        command.upgrade(cfg, "head")
        with engine.connect() as connection:
            version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert version == "012_login_rate_limits"
    finally:
        command.upgrade(cfg, "head")
        engine.dispose()
