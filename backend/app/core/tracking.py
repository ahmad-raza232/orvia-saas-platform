import re
import secrets

TRACKING_PREFIX = "ORVIA"
TRACKING_BODY_LENGTH = 10
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# ORVIA- + 10 Crockford-style chars (no 0/O/1/I)
ORVIA_TRACKING_RE = re.compile(
    rf"^{TRACKING_PREFIX}-[{ALPHABET}]{{{TRACKING_BODY_LENGTH}}}$"
)
# Legacy GoBurq public tracking (unchanged contract)
GBQ_TRACKING_RE = re.compile(r"^GBQ\d{7,}$", re.IGNORECASE)


def generate_tracking_number(prefix: str = TRACKING_PREFIX) -> str:
    """
    Public Softorica SaaS tracking id: ORVIA-XXXXXXXXXX

    The body is 10 characters from a Crockford-style alphabet (no 0/O/1/I).
    It is non-sequential. Never generates GBQ IDs.
    """
    body = "".join(secrets.choice(ALPHABET) for _ in range(TRACKING_BODY_LENGTH))
    return f"{prefix}-{body}"


def normalize_tracking_number(value: str) -> str:
    return (value or "").strip().upper()


def is_orvia_tracking_number(value: str) -> bool:
    return bool(ORVIA_TRACKING_RE.match(normalize_tracking_number(value)))


def is_gbq_tracking_number(value: str) -> bool:
    cleaned = normalize_tracking_number(value)
    return bool(GBQ_TRACKING_RE.match(cleaned)) and len(cleaned) >= 10
