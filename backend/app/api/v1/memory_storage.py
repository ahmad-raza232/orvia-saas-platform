"""Development-only HTTP bridge for MemoryStorageProvider signed URLs.

Enabled only when STORAGE_PROVIDER=memory and APP_ENV is not production.
Does not replace S3 signed URLs and does not expose credentials.

Query params ``expires`` (unix timestamp) must be present and not past.
``nonce`` is required on the URL (issued by MemoryStorageProvider) but is not a
cryptographic signature — memory storage is for local/dev only.
"""

from datetime import datetime, timezone
from urllib.parse import unquote

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.services.storage_provider import get_memory_storage

router = APIRouter(prefix="/_dev/memory", tags=["dev-memory-storage"])


def _memory_enabled() -> bool:
    provider = (settings.storage_provider or "memory").strip().lower()
    return provider == "memory" and not settings.is_production


def _expiry_ok(request: Request) -> bool:
    expires_raw = request.query_params.get("expires")
    nonce = request.query_params.get("nonce")
    if not expires_raw or not nonce:
        return False
    try:
        expires_at = int(expires_raw)
    except (TypeError, ValueError):
        return False
    now = int(datetime.now(timezone.utc).timestamp())
    return expires_at >= now


@router.put("/upload/{object_key:path}", status_code=status.HTTP_204_NO_CONTENT)
async def memory_upload(object_key: str, request: Request) -> Response:
    if not _memory_enabled():
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "NOT_FOUND", "message": "Not Found"}},
        )
    if not _expiry_ok(request):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "Upload URL is missing, invalid, or expired.",
                }
            },
        )
    key = unquote(object_key)
    body = await request.body()
    content_type = request.headers.get("content-type") or "application/octet-stream"
    get_memory_storage().store(key, content_type.split(";")[0].strip(), len(body), data=body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/download/{object_key:path}")
async def memory_download(object_key: str, request: Request) -> Response:
    if not _memory_enabled():
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "NOT_FOUND", "message": "Not Found"}},
        )
    if not _expiry_ok(request):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "Download URL is missing, invalid, or expired.",
                }
            },
        )
    key = unquote(object_key)
    stored = get_memory_storage()._objects.get(key)
    if stored is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "NOT_FOUND", "message": "Object not found."}},
        )
    return Response(
        content=stored.data,
        media_type=stored.content_type or "application/octet-stream",
        status_code=status.HTTP_200_OK,
    )
