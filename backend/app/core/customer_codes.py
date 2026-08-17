import secrets

from app.core.tracking import ALPHABET

CUSTOMER_CODE_PREFIX = "CUS"
CUSTOMER_CODE_LENGTH = 8


def generate_customer_code() -> str:
    """Tenant customer code: CUS-XXXXXXXX. Non-sequential; uniqueness is enforced per organization."""
    body = "".join(secrets.choice(ALPHABET) for _ in range(CUSTOMER_CODE_LENGTH))
    return f"{CUSTOMER_CODE_PREFIX}-{body}"
