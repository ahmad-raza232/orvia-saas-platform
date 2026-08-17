from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.image_magic import sample_image_bytes
from app.core.storage_keys import generate_pod_object_key
from app.main import app
from app.models.audit_log import AuditLog
from app.models.pod_evidence import PodEvidence, PodEvidenceStatus
from app.services.storage_provider import (
    MemoryStorageProvider,
    S3StorageProvider,
    StorageProvider,
    StorageUnavailableError,
    get_memory_storage,
    get_storage_provider,
)
from tests.test_customers import invite_member
from tests.test_pod import delivered_shipment, pod_payload
from tests.test_shipments import auth_header, create_org, shipment_payload


def upload_payload(**overrides) -> dict:
    payload = {
        "type": "SIGNATURE",
        "filename": "signature.png",
        "content_type": "image/png",
        "size_bytes": 12345,
    }
    payload.update(overrides)
    return payload


def create_delivered_pod(client: TestClient, token: str, **overrides) -> tuple[dict, dict]:
    shipment = delivered_shipment(client, token, **overrides)
    created = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod",
        headers=auth_header(token),
        json=pod_payload(),
    )
    assert created.status_code == 201, created.text
    return shipment, created.json()


def simulate_client_upload(object_key: str, content_type: str, size_bytes: int) -> None:
    get_memory_storage().store(
        object_key,
        content_type,
        size_bytes,
        data=sample_image_bytes(content_type, size_bytes),
    )


class FailingStorageProvider(StorageProvider):
    def __init__(self, *, fail_upload: bool = False, fail_head: bool = False, fail_download: bool = False) -> None:
        self.fail_upload = fail_upload
        self.fail_head = fail_head
        self.fail_download = fail_download
        self.inner = MemoryStorageProvider()

    def create_upload_url(self, key: str, content_type: str, expires_in: int):
        if self.fail_upload:
            raise StorageUnavailableError("unavailable")
        return self.inner.create_upload_url(key, content_type, expires_in)

    def head_object(self, key: str):
        if self.fail_head:
            raise StorageUnavailableError("unavailable")
        return self.inner.head_object(key)

    def create_download_url(self, key: str, expires_in: int):
        if self.fail_download:
            raise StorageUnavailableError("unavailable")
        return self.inner.create_download_url(key, expires_in)

    def delete_object(self, key: str) -> None:
        self.inner.delete_object(key)

    def get_object_prefix(self, key: str, max_bytes: int = 16) -> bytes | None:
        if self.fail_head:
            raise StorageUnavailableError("unavailable")
        return self.inner.get_object_prefix(key, max_bytes)


def test_memory_storage_provider_interface() -> None:
    provider = MemoryStorageProvider()
    signed = provider.create_upload_url("org/a/key", "image/png", 300)
    assert signed.method == "PUT"
    assert signed.headers["Content-Type"] == "image/png"
    assert signed.url.startswith("http")
    assert "/_dev/memory/upload/" in signed.url or "memory.invalid" in signed.url or "amazonaws" in signed.url or signed.url.startswith("https://")
    assert "expires=" in signed.url
    assert signed.expires_at > datetime.now(timezone.utc)
    assert provider.head_object("org/a/key") is None
    provider.store("org/a/key", "image/png", 12)
    meta = provider.head_object("org/a/key")
    assert meta is not None
    assert meta.size_bytes == 12
    assert meta.content_type == "image/png"
    download = provider.create_download_url("org/a/key", 120)
    assert download.method == "GET"
    assert download.url.startswith("http")
    assert "/_dev/memory/download/" in download.url
    provider.delete_object("org/a/key")
    assert provider.head_object("org/a/key") is None


def test_s3_provider_requires_configuration(monkeypatch) -> None:
    monkeypatch.setattr(settings, "s3_bucket", None)
    monkeypatch.setattr(settings, "s3_access_key_id", None)
    monkeypatch.setattr(settings, "s3_secret_access_key", None)
    provider = S3StorageProvider()
    with pytest.raises(StorageUnavailableError):
        provider.create_upload_url("organizations/x/key", "image/png", 60)


def test_s3_signed_upload_url_generation_is_local(monkeypatch) -> None:
    monkeypatch.setattr(settings, "s3_bucket", "orvia-pod")
    monkeypatch.setattr(settings, "s3_region", "us-east-1")
    monkeypatch.setattr(settings, "s3_access_key_id", "AKIA_TEST_KEY")
    monkeypatch.setattr(settings, "s3_secret_access_key", "wJalrXUtnFEMI/K7MDENG/secret")
    monkeypatch.setattr(settings, "s3_endpoint_url", None)
    monkeypatch.setattr(settings, "s3_force_path_style", False)
    provider = S3StorageProvider()
    signed = provider.create_upload_url(
        "organizations/aaa/shipments/bbb/pod/ccc/ddd",
        "image/png",
        300,
    )
    assert signed.method == "PUT"
    assert signed.headers["Content-Type"] == "image/png"
    assert "orvia-pod" in signed.url
    assert "wJalrXUtnFEMI" not in signed.url
    assert "/secret" not in signed.url
    assert signed.expires_at <= datetime.now(timezone.utc) + timedelta(seconds=301)


def test_object_key_is_generated_without_filename_or_pii() -> None:
    from uuid import uuid4

    org_id, shipment_id, pod_id = uuid4(), uuid4(), uuid4()
    key = generate_pod_object_key(org_id, shipment_id, pod_id)
    assert key.startswith(f"organizations/{org_id}/shipments/{shipment_id}/pod/{pod_id}/")
    assert "signature.png" not in key
    assert "@" not in key
    assert " " not in key
    other = generate_pod_object_key(org_id, shipment_id, pod_id)
    assert key != other


def test_request_upload_creates_pending_and_signed_url(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "pod-up@example.com", "POD Up", "pod-up")
    shipment, pod = create_delivered_pod(client, token, reference_number="POD-UP")
    response = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads",
        headers=auth_header(token),
        json=upload_payload(filename="alice@example.com.png", organization_id="ignored"),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["method"] == "PUT"
    assert body["headers"]["Content-Type"] == "image/png"
    assert body["upload_url"].startswith("http")
    assert "/_dev/memory/upload/" in body["upload_url"]
    assert "alice@example.com" not in body["object_key"]
    assert "signature.png" not in body["object_key"]
    assert str(pod["id"]) in body["object_key"]
    assert "expires_at" in body
    expires = datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00"))
    assert expires > datetime.now(timezone.utc)
    row = db.get(PodEvidence, body["evidence_id"])
    assert row is not None
    assert row.status == PodEvidenceStatus.PENDING.value
    assert row.original_filename == "alice@example.com.png"
    audit = (
        db.query(AuditLog)
        .filter(AuditLog.action == "POD_EVIDENCE_UPLOAD_REQUESTED", AuditLog.resource_id == body["evidence_id"])
        .one()
    )
    assert audit.details["tracking_number"] == shipment["tracking_number"]
    assert "upload_url" not in str(audit.details)
    assert "object_key" not in str(audit.details)


def test_complete_rejects_non_image_bytes_labeled_as_png(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "pod-magic@example.com", "POD Magic", "pod-magic")
    shipment, _pod = create_delivered_pod(client, token)
    requested = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads",
        headers=auth_header(token),
        json=upload_payload(),
    ).json()
    get_memory_storage().store(
        requested["object_key"],
        "image/png",
        12345,
        data=b"<!DOCTYPE html>" + (b"\0" * 12330),
    )
    completed = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads/{requested['upload_id']}/complete",
        headers=auth_header(token),
    )
    assert completed.status_code == 409
    assert completed.json()["error"]["code"] == "POD_EVIDENCE_UPLOAD_FAILED"
    row = db.get(PodEvidence, requested["evidence_id"])
    assert row is not None
    assert row.status == PodEvidenceStatus.FAILED.value
    audit = (
        db.query(AuditLog)
        .filter(AuditLog.action == "POD_EVIDENCE_UPLOAD_FAILED", AuditLog.resource_id == requested["evidence_id"])
        .one()
    )
    assert audit.details["reason"] == "object_magic_invalid"


def test_complete_upload_success_and_duplicate_complete(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "pod-ok@example.com", "POD OK", "pod-ok")
    shipment, _pod = create_delivered_pod(client, token)
    requested = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads",
        headers=auth_header(token),
        json=upload_payload(),
    ).json()
    simulate_client_upload(requested["object_key"], "image/png", 12345)
    completed = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads/{requested['upload_id']}/complete",
        headers=auth_header(token),
    )
    assert completed.status_code == 200, completed.text
    body = completed.json()
    assert body["status"] == "UPLOADED"
    assert body["uploaded_at"] is not None
    assert "upload_url" not in body
    again = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads/{requested['upload_id']}/complete",
        headers=auth_header(token),
    )
    assert again.status_code == 200
    assert again.json()["status"] == "UPLOADED"
    assert again.json()["id"] == body["id"]
    audit = (
        db.query(AuditLog)
        .filter(AuditLog.action == "POD_EVIDENCE_UPLOADED", AuditLog.resource_id == body["id"])
        .one()
    )
    assert audit.details["evidence_type"] == "SIGNATURE"
    replacement = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads",
        headers=auth_header(token),
        json=upload_payload(),
    )
    assert replacement.status_code == 409
    assert replacement.json()["error"]["code"] == "POD_EVIDENCE_ALREADY_UPLOADED"


def test_missing_object_marks_failed(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "pod-miss@example.com", "POD Miss", "pod-miss")
    shipment, _pod = create_delivered_pod(client, token)
    requested = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads",
        headers=auth_header(token),
        json=upload_payload(),
    ).json()
    failed = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads/{requested['upload_id']}/complete",
        headers=auth_header(token),
    )
    assert failed.status_code == 409
    assert failed.json()["error"]["code"] == "POD_EVIDENCE_UPLOAD_FAILED"
    row = db.get(PodEvidence, requested["upload_id"])
    assert row is not None
    assert row.status == PodEvidenceStatus.FAILED.value
    assert (
        db.query(AuditLog)
        .filter(AuditLog.action == "POD_EVIDENCE_UPLOAD_FAILED", AuditLog.resource_id == requested["upload_id"])
        .one()
    )
    retry = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads/{requested['upload_id']}/complete",
        headers=auth_header(token),
    )
    assert retry.status_code == 409


def test_wrong_object_metadata_marks_failed(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "pod-meta@example.com", "POD Meta", "pod-meta")
    shipment, _pod = create_delivered_pod(client, token)
    requested = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads",
        headers=auth_header(token),
        json=upload_payload(),
    ).json()
    simulate_client_upload(requested["object_key"], "image/jpeg", 12345)
    failed = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads/{requested['upload_id']}/complete",
        headers=auth_header(token),
    )
    assert failed.status_code == 409
    row = db.get(PodEvidence, requested["upload_id"])
    assert row is not None
    assert row.status == PodEvidenceStatus.FAILED.value

    photo = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads",
        headers=auth_header(token),
        json=upload_payload(type="DELIVERY_PHOTO", filename="door.webp", content_type="image/webp"),
    ).json()
    simulate_client_upload(photo["object_key"], "image/webp", 99_000)
    oversized = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads/{photo['upload_id']}/complete",
        headers=auth_header(token),
    )
    assert oversized.status_code == 409
    row = db.get(PodEvidence, photo["upload_id"])
    assert row is not None
    assert row.status == PodEvidenceStatus.FAILED.value


def test_download_only_for_uploaded_and_audited(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "pod-dl@example.com", "POD DL", "pod-dl")
    shipment, _pod = create_delivered_pod(client, token)
    requested = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads",
        headers=auth_header(token),
        json=upload_payload(),
    ).json()
    pending_dl = client.get(
        f"/api/v1/shipments/{shipment['id']}/pod/evidence/{requested['upload_id']}/download",
        headers=auth_header(token),
    )
    assert pending_dl.status_code == 409
    simulate_client_upload(requested["object_key"], "image/png", 12345)
    client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads/{requested['upload_id']}/complete",
        headers=auth_header(token),
    )
    downloaded = client.get(
        f"/api/v1/shipments/{shipment['id']}/pod/evidence/{requested['upload_id']}/download",
        headers=auth_header(token),
    )
    assert downloaded.status_code == 200, downloaded.text
    body = downloaded.json()
    assert body["method"] == "GET"
    assert body["download_url"].startswith("http")
    assert "/_dev/memory/download/" in body["download_url"]
    assert "AKIA" not in body["download_url"]
    expires = datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00"))
    assert expires > datetime.now(timezone.utc)
    audit = (
        db.query(AuditLog)
        .filter(AuditLog.action == "POD_EVIDENCE_DOWNLOAD_REQUESTED", AuditLog.resource_id == requested["upload_id"])
        .one()
    )
    assert "download_url" not in str(audit.details)


def test_tenant_isolation_for_upload_complete_and_download(client: TestClient) -> None:
    token_a, _ = create_org(client, "pod-st-a@example.com", "POD ST A", "pod-st-a")
    token_b, _ = create_org(client, "pod-st-b@example.com", "POD ST B", "pod-st-b")
    ship_a, _ = create_delivered_pod(client, token_a, reference_number="ISO-A")
    ship_b, _ = create_delivered_pod(client, token_b, reference_number="ISO-B")
    headers = {"Authorization": auth_header(token_a)["Authorization"]}
    requested = client.post(
        f"/api/v1/shipments/{ship_a['id']}/pod/uploads",
        headers=headers,
        json=upload_payload(),
    )
    assert requested.status_code == 201
    upload_id = requested.json()["upload_id"]
    object_key = requested.json()["object_key"]
    simulate_client_upload(object_key, "image/png", 12345)
    client.post(
        f"/api/v1/shipments/{ship_a['id']}/pod/uploads/{upload_id}/complete",
        headers=headers,
        json={},
    )

    assert client.post(
        f"/api/v1/shipments/{ship_a['id']}/pod/uploads",
        headers=auth_header(token_b),
        json=upload_payload(),
    ).status_code == 404
    assert client.post(
        f"/api/v1/shipments/{ship_a['id']}/pod/uploads/{upload_id}/complete",
        headers=auth_header(token_b),
    ).status_code == 404
    assert client.get(
        f"/api/v1/shipments/{ship_a['id']}/pod/evidence",
        headers=auth_header(token_b),
    ).status_code == 404
    missing = client.get(
        f"/api/v1/shipments/{ship_a['id']}/pod/evidence/{upload_id}/download",
        headers=auth_header(token_b),
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"
    assert client.post(
        f"/api/v1/shipments/{ship_b['id']}/pod/uploads/{upload_id}/complete",
        headers=auth_header(token_a),
    ).status_code == 404


def test_delivered_and_pod_required(client: TestClient) -> None:
    token, _ = create_org(client, "pod-req@example.com", "POD Req", "pod-req")
    booked = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json=shipment_payload(reference_number="NOT-DELIVERED"),
    ).json()
    not_delivered = client.post(
        f"/api/v1/shipments/{booked['id']}/pod/uploads",
        headers=auth_header(token),
        json=upload_payload(),
    )
    assert not_delivered.status_code == 409
    assert not_delivered.json()["error"]["code"] == "POD_NOT_ALLOWED"

    delivered = delivered_shipment(client, token, reference_number="NO-POD")
    missing_pod = client.post(
        f"/api/v1/shipments/{delivered['id']}/pod/uploads",
        headers=auth_header(token),
        json=upload_payload(),
    )
    assert missing_pod.status_code == 404
    assert missing_pod.json()["error"]["code"] == "NOT_FOUND"


def test_rbac_upload_and_download(client: TestClient) -> None:
    admin, _ = create_org(client, "pod-rbac@example.com", "POD RBAC", "pod-rbac")
    ops = invite_member(client, admin, "pod-rbac-ops@example.com", "OPERATIONS_MANAGER")
    staff = invite_member(client, admin, "pod-rbac-staff@example.com", "STAFF")
    buyer = invite_member(client, admin, "pod-rbac-buyer@example.com", "CUSTOMER")
    shipment, _ = create_delivered_pod(client, admin)
    assert client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads",
        headers=auth_header(staff),
        json=upload_payload(),
    ).status_code == 403
    assert client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads",
        headers=auth_header(buyer),
        json=upload_payload(),
    ).status_code == 403
    requested = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads",
        headers=auth_header(ops),
        json=upload_payload(type="DELIVERY_PHOTO", filename="door.jpg", content_type="image/jpeg"),
    )
    assert requested.status_code == 201, requested.text
    simulate_client_upload(requested.json()["object_key"], "image/jpeg", 12345)
    assert client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads/{requested.json()['upload_id']}/complete",
        headers=auth_header(staff),
    ).status_code == 403
    completed = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads/{requested.json()['upload_id']}/complete",
        headers=auth_header(ops),
    )
    assert completed.status_code == 200
    evidence_id = completed.json()["id"]
    assert client.get(
        f"/api/v1/shipments/{shipment['id']}/pod/evidence/{evidence_id}/download",
        headers=auth_header(staff),
    ).status_code == 200
    assert client.get(
        f"/api/v1/shipments/{shipment['id']}/pod/evidence/{evidence_id}/download",
        headers=auth_header(buyer),
    ).status_code == 403
    listed = client.get(
        f"/api/v1/shipments/{shipment['id']}/pod/evidence",
        headers=auth_header(staff),
    )
    assert listed.status_code == 200
    assert listed.json()["items"][0]["status"] == "UPLOADED"


def test_mime_and_size_validation(client: TestClient) -> None:
    token, _ = create_org(client, "pod-mime@example.com", "POD MIME", "pod-mime")
    shipment, _ = create_delivered_pod(client, token)
    url = f"/api/v1/shipments/{shipment['id']}/pod/uploads"
    headers = auth_header(token)
    rejected = [
        upload_payload(content_type="application/octet-stream"),
        upload_payload(content_type="application/pdf", filename="file.pdf"),
        upload_payload(filename="signature.exe", content_type="image/png"),
        upload_payload(filename="signature.jpg", content_type="image/png"),
        upload_payload(size_bytes=settings.pod_signature_max_bytes + 1),
        upload_payload(
            type="DELIVERY_PHOTO",
            filename="door.png",
            content_type="image/png",
            size_bytes=settings.pod_photo_max_bytes + 1,
        ),
    ]
    for payload in rejected:
        response = client.post(url, headers=headers, json=payload)
        assert response.status_code == 422, payload
    for mime, filename in (("image/jpeg", "sign.jpg"), ("image/png", "sign.png"), ("image/webp", "sign.webp")):
        response = client.post(
            url,
            headers=headers,
            json=upload_payload(content_type=mime, filename=filename, type="SIGNATURE"),
        )
        assert response.status_code == 201, response.text


def test_evidence_immutability(client: TestClient) -> None:
    token, _ = create_org(client, "pod-imm@example.com", "POD Imm", "pod-imm")
    shipment, _ = create_delivered_pod(client, token)
    requested = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads",
        headers=auth_header(token),
        json=upload_payload(),
    ).json()
    simulate_client_upload(requested["object_key"], "image/png", 12345)
    evidence_id = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads/{requested['upload_id']}/complete",
        headers=auth_header(token),
    ).json()["id"]
    patched = client.patch(
        f"/api/v1/shipments/{shipment['id']}/pod/evidence/{evidence_id}",
        headers=auth_header(token),
        json={"status": "FAILED"},
    )
    assert patched.status_code in {404, 405}
    deleted = client.delete(
        f"/api/v1/shipments/{shipment['id']}/pod/evidence/{evidence_id}",
        headers=auth_header(token),
    )
    assert deleted.status_code in {404, 405}


def test_storage_failure_on_signed_url_marks_failed(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "pod-fail@example.com", "POD Fail", "pod-fail")
    shipment, _ = create_delivered_pod(client, token)
    boom = FailingStorageProvider(fail_upload=True)
    app.dependency_overrides[get_storage_provider] = lambda: boom
    try:
        response = client.post(
            f"/api/v1/shipments/{shipment['id']}/pod/uploads",
            headers=auth_header(token),
            json=upload_payload(),
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "STORAGE_UNAVAILABLE"
    finally:
        app.dependency_overrides.pop(get_storage_provider, None)
    failed = db.query(PodEvidence).filter(PodEvidence.shipment_id == shipment["id"]).one()
    assert failed.status == PodEvidenceStatus.FAILED.value
    assert (
        db.query(AuditLog)
        .filter(AuditLog.action == "POD_EVIDENCE_UPLOAD_FAILED", AuditLog.resource_id == str(failed.id))
        .one()
    )


def test_storage_failure_on_complete_keeps_pending(client: TestClient, db: Session) -> None:
    token, _ = create_org(client, "pod-head@example.com", "POD Head", "pod-head")
    shipment, _ = create_delivered_pod(client, token)
    requested = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads",
        headers=auth_header(token),
        json=upload_payload(),
    ).json()
    boom = FailingStorageProvider(fail_head=True)
    app.dependency_overrides[get_storage_provider] = lambda: boom
    try:
        response = client.post(
            f"/api/v1/shipments/{shipment['id']}/pod/uploads/{requested['upload_id']}/complete",
            headers=auth_header(token),
        )
        assert response.status_code == 503
    finally:
        app.dependency_overrides.pop(get_storage_provider, None)
    row = db.get(PodEvidence, requested["upload_id"])
    assert row is not None
    assert row.status == PodEvidenceStatus.PENDING.value


def test_get_pod_includes_evidence_metadata(client: TestClient) -> None:
    token, _ = create_org(client, "pod-get@example.com", "POD Get", "pod-get")
    shipment, _ = create_delivered_pod(client, token)
    requested = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads",
        headers=auth_header(token),
        json=upload_payload(),
    ).json()
    simulate_client_upload(requested["object_key"], "image/png", 12345)
    client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads/{requested['upload_id']}/complete",
        headers=auth_header(token),
    )
    fetched = client.get(f"/api/v1/shipments/{shipment['id']}/pod", headers=auth_header(token))
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["evidence"][0]["status"] == "UPLOADED"
    assert "upload_url" not in body["evidence"][0]
    assert "object_key" not in body["evidence"][0]


def test_two_pending_uploads_are_separate_ids(client: TestClient) -> None:
    token, _ = create_org(client, "pod-two@example.com", "POD Two", "pod-two")
    shipment, _ = create_delivered_pod(client, token)
    first = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads",
        headers=auth_header(token),
        json=upload_payload(),
    ).json()
    second = client.post(
        f"/api/v1/shipments/{shipment['id']}/pod/uploads",
        headers=auth_header(token),
        json=upload_payload(),
    ).json()
    assert first["upload_id"] != second["upload_id"]
    assert first["object_key"] != second["object_key"]


def test_pod_storage_migration_upgrade_downgrade_reupgrade(engine) -> None:
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect, text

    backend_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    engine.dispose()
    try:
        command.downgrade(cfg, "009_outbox_worker_hardening")
        assert "pod_evidence" not in inspect(engine).get_table_names()
        command.upgrade(cfg, "head")
        inspector = inspect(engine)
        assert "pod_evidence" in inspector.get_table_names()
        index_names = {index["name"] for index in inspector.get_indexes("pod_evidence")}
        assert "ix_pod_evidence_organization_id" in index_names
        assert "uq_pod_evidence_uploaded_type" in index_names
        command.downgrade(cfg, "009_outbox_worker_hardening")
        assert "pod_evidence" not in inspect(engine).get_table_names()
        command.upgrade(cfg, "head")
        with engine.connect() as connection:
            version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert version != "009_outbox_worker_hardening"
    finally:
        command.upgrade(cfg, "head")
        engine.dispose()
