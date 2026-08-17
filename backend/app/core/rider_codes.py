import secrets

from app.core.tracking import ALPHABET

RIDER_CODE_PREFIX = "RDR"
RIDER_CODE_LENGTH = 8


def generate_rider_code() -> str:
    """Tenant rider code: RDR-XXXXXXXX. Non-sequential; uniqueness is enforced per organization."""
    body = "".join(secrets.choice(ALPHABET) for _ in range(RIDER_CODE_LENGTH))
    return f"{RIDER_CODE_PREFIX}-{body}"
