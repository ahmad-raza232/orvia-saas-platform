import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_access_token(*, subject: str, organization_id: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "typ": "access",
    }
    if organization_id:
        payload["org"] = organization_id
    algorithm = settings.jwt_algorithm
    if algorithm.upper() == "NONE":
        raise ValueError("JWT_ALGORITHM cannot be none")
    return jwt.encode(payload, settings.jwt_secret, algorithm=algorithm)


def decode_access_token(token: str) -> dict:
    algorithm = settings.jwt_algorithm
    if algorithm.upper() == "NONE":
        raise jwt.InvalidTokenError("JWT_ALGORITHM cannot be none")
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[algorithm],
        options={"require": ["exp", "iat", "sub", "typ"]},
        leeway=0,
    )
    if payload.get("typ") != "access":
        raise jwt.InvalidTokenError("Invalid token type")
    issued_at = payload.get("iat")
    if issued_at is not None:
        now = datetime.now(timezone.utc).timestamp()
        if float(issued_at) > now + 60:
            raise jwt.InvalidTokenError("Token iat is in the future")
    subject = payload.get("sub")
    if not subject:
        raise jwt.InvalidTokenError("Token sub is missing")
    return payload


def generate_invitation_token() -> str:
    return secrets.token_urlsafe(32)


def hash_invitation_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
