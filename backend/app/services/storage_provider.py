from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
import logging
import secrets

from app.core.config import settings

logger = logging.getLogger("orvia.storage")


class StorageError(Exception):
    """Base error for object-storage adapters."""


class StorageUnavailableError(StorageError):
    """Raised when object storage cannot be reached or is not configured."""


@dataclass(frozen=True)
class ObjectMeta:
    key: str
    size_bytes: int
    content_type: str | None = None


@dataclass(frozen=True)
class SignedUrl:
    url: str
    method: str
    expires_at: datetime
    headers: dict[str, str] = field(default_factory=dict)


class StorageProvider(ABC):
    """Object-storage adapter. POD services must not call S3 APIs directly."""

    @abstractmethod
    def create_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int,
    ) -> SignedUrl:
        raise NotImplementedError

    @abstractmethod
    def head_object(self, key: str) -> ObjectMeta | None:
        raise NotImplementedError

    @abstractmethod
    def create_download_url(self, key: str, expires_in: int) -> SignedUrl:
        raise NotImplementedError

    @abstractmethod
    def delete_object(self, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_object_prefix(self, key: str, max_bytes: int = 16) -> bytes | None:
        raise NotImplementedError


@dataclass
class _MemoryObject:
    content_type: str
    size_bytes: int
    data: bytes = b""


class MemoryStorageProvider(StorageProvider):
    """In-memory provider for tests and local development without AWS/MinIO."""

    def __init__(self) -> None:
        self._objects: dict[str, _MemoryObject] = {}

    def clear(self) -> None:
        self._objects.clear()

    def store(
        self,
        key: str,
        content_type: str,
        size_bytes: int,
        data: bytes | None = None,
    ) -> None:
        payload = data if data is not None else b"\0" * max(size_bytes, 0)
        self._objects[key] = _MemoryObject(
            content_type=content_type,
            size_bytes=size_bytes if data is None else len(payload),
            data=payload,
        )

    def create_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int,
    ) -> SignedUrl:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        token = secrets.token_urlsafe(16)
        base = (settings.memory_storage_public_base_url or "http://127.0.0.1:8000").rstrip("/")
        url = (
            f"{base}/api/v1/_dev/memory/upload/{quote(key, safe='')}?"
            f"expires={int(expires_at.timestamp())}&nonce={token}"
        )
        return SignedUrl(
            url=url,
            method="PUT",
            expires_at=expires_at,
            headers={"Content-Type": content_type},
        )

    def head_object(self, key: str) -> ObjectMeta | None:
        stored = self._objects.get(key)
        if stored is None:
            return None
        return ObjectMeta(
            key=key,
            size_bytes=stored.size_bytes,
            content_type=stored.content_type,
        )

    def create_download_url(self, key: str, expires_in: int) -> SignedUrl:
        if key not in self._objects:
            raise StorageUnavailableError("Object is not available for download.")
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        token = secrets.token_urlsafe(16)
        base = (settings.memory_storage_public_base_url or "http://127.0.0.1:8000").rstrip("/")
        url = (
            f"{base}/api/v1/_dev/memory/download/{quote(key, safe='')}?"
            f"expires={int(expires_at.timestamp())}&nonce={token}"
        )
        return SignedUrl(url=url, method="GET", expires_at=expires_at, headers={})

    def delete_object(self, key: str) -> None:
        self._objects.pop(key, None)

    def get_object_prefix(self, key: str, max_bytes: int = 16) -> bytes | None:
        stored = self._objects.get(key)
        if stored is None:
            return None
        return stored.data[:max_bytes]


class S3StorageProvider(StorageProvider):
    """S3-compatible provider (AWS S3 or MinIO). Credentials stay in configuration."""

    def __init__(self) -> None:
        self._client = None

    def _require_config(self) -> None:
        if not (settings.s3_bucket or "").strip():
            raise StorageUnavailableError("Object storage is not configured.")
        if not (settings.s3_access_key_id or "").strip() or not (
            settings.s3_secret_access_key or ""
        ).strip():
            raise StorageUnavailableError("Object storage is not configured.")

    def _get_client(self):
        if self._client is not None:
            return self._client
        self._require_config()
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise StorageUnavailableError("Object storage is not configured.") from exc

        client_kwargs: dict = {
            "service_name": "s3",
            "region_name": settings.s3_region or "us-east-1",
            "aws_access_key_id": settings.s3_access_key_id,
            "aws_secret_access_key": settings.s3_secret_access_key,
            "config": Config(
                signature_version="s3v4",
                connect_timeout=5,
                read_timeout=10,
                retries={"max_attempts": 2},
                s3={
                    "addressing_style": (
                        "path" if settings.s3_force_path_style else "auto"
                    )
                },
            ),
        }
        endpoint = (settings.s3_endpoint_url or "").strip()
        if endpoint:
            client_kwargs["endpoint_url"] = endpoint
        self._client = boto3.client(**client_kwargs)
        return self._client

    def create_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int,
    ) -> SignedUrl:
        client = self._get_client()
        try:
            url = client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": settings.s3_bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
                HttpMethod="PUT",
            )
        except Exception:
            logger.warning("storage.upload_url_failed")
            raise StorageUnavailableError("Object storage is unavailable.") from None
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        return SignedUrl(
            url=url,
            method="PUT",
            expires_at=expires_at,
            headers={"Content-Type": content_type},
        )

    def head_object(self, key: str) -> ObjectMeta | None:
        client = self._get_client()
        try:
            response = client.head_object(Bucket=settings.s3_bucket, Key=key)
        except Exception as exc:
            error_code = ""
            if hasattr(exc, "response"):
                error_code = str(
                    (exc.response or {}).get("Error", {}).get("Code", "")
                )
            if error_code in {"404", "NoSuchKey", "NotFound"}:
                return None
            logger.warning("storage.head_failed")
            raise StorageUnavailableError("Object storage is unavailable.") from None
        size = int(response.get("ContentLength") or 0)
        content_type = response.get("ContentType")
        return ObjectMeta(key=key, size_bytes=size, content_type=content_type)

    def create_download_url(self, key: str, expires_in: int) -> SignedUrl:
        client = self._get_client()
        try:
            url = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.s3_bucket, "Key": key},
                ExpiresIn=expires_in,
                HttpMethod="GET",
            )
        except Exception:
            logger.warning("storage.download_url_failed")
            raise StorageUnavailableError("Object storage is unavailable.") from None
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        return SignedUrl(url=url, method="GET", expires_at=expires_at, headers={})

    def delete_object(self, key: str) -> None:
        client = self._get_client()
        try:
            client.delete_object(Bucket=settings.s3_bucket, Key=key)
        except Exception:
            logger.warning("storage.delete_failed")
            raise StorageUnavailableError("Object storage is unavailable.") from None

    def get_object_prefix(self, key: str, max_bytes: int = 16) -> bytes | None:
        client = self._get_client()
        try:
            response = client.get_object(
                Bucket=settings.s3_bucket,
                Key=key,
                Range=f"bytes=0-{max(0, max_bytes - 1)}",
            )
            body = response["Body"].read(max_bytes)
        except Exception as exc:
            error_code = ""
            if hasattr(exc, "response"):
                error_code = str((exc.response or {}).get("Error", {}).get("Code", ""))
            if error_code in {"404", "NoSuchKey", "NotFound", "InvalidRange"}:
                return None
            logger.warning("storage.prefix_failed")
            raise StorageUnavailableError("Object storage is unavailable.") from None
        return body


_memory_provider: MemoryStorageProvider | None = None


def get_memory_storage() -> MemoryStorageProvider:
    global _memory_provider
    if _memory_provider is None:
        _memory_provider = MemoryStorageProvider()
    return _memory_provider


def reset_memory_storage() -> None:
    get_memory_storage().clear()


def get_storage_provider() -> StorageProvider:
    provider = (settings.storage_provider or "memory").strip().lower()
    if provider == "s3":
        return S3StorageProvider()
    return get_memory_storage()
