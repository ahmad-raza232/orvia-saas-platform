"""Lightweight image magic-byte checks. Not antivirus scanning."""

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"
WEBP_RIFF = b"RIFF"
WEBP_TYPE = b"WEBP"

PREFIX_BYTES = 16


def content_matches_declared_type(prefix: bytes, content_type: str) -> bool:
    declared = (content_type or "").split(";")[0].strip().lower()
    if declared == "image/png":
        return prefix.startswith(PNG_MAGIC)
    if declared == "image/jpeg":
        return prefix.startswith(JPEG_MAGIC)
    if declared == "image/webp":
        return prefix.startswith(WEBP_RIFF) and prefix[8:12] == WEBP_TYPE
    return False


def sample_image_bytes(content_type: str, size_bytes: int) -> bytes:
    """Valid magic prefix padded to size_bytes. Used by tests and local memory uploads."""
    declared = (content_type or "").split(";")[0].strip().lower()
    if declared == "image/png":
        prefix = PNG_MAGIC
    elif declared == "image/jpeg":
        prefix = JPEG_MAGIC + b"\xe0"
    elif declared == "image/webp":
        prefix = WEBP_RIFF + b"\x00\x00\x00\x00" + WEBP_TYPE
    else:
        prefix = b""
    if size_bytes <= len(prefix):
        return prefix[: max(size_bytes, 0)]
    return prefix + (b"\0" * (size_bytes - len(prefix)))
