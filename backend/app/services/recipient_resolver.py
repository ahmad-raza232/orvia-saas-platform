from dataclasses import dataclass
import re

from app.models.shipment import Shipment

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class RecipientResolution:
    email: str | None
    customer_id: object | None
    customer_name: str | None
    skipped_reason: str | None

    @property
    def skipped(self) -> bool:
        return self.skipped_reason is not None


def _is_safe_email(value: str) -> bool:
    cleaned = value.strip()
    if not cleaned or any(ch in cleaned for ch in ("\r", "\n", ",", ";", " ")):
        return False
    if len(cleaned) > 255:
        return False
    return bool(_EMAIL.match(cleaned))


class RecipientResolver:
    """Resolves the customer email for shipment notifications. Never invents addresses."""

    def resolve_email(self, shipment: Shipment) -> RecipientResolution:
        customer = shipment.customer
        if customer is None:
            return RecipientResolution(None, None, None, "NO_CUSTOMER")
        if not customer.email:
            return RecipientResolution(None, customer.id, customer.name, "MISSING_CUSTOMER_EMAIL")
        if not _is_safe_email(customer.email):
            return RecipientResolution(None, customer.id, customer.name, "INVALID_CUSTOMER_EMAIL")
        return RecipientResolution(
            customer.email.strip().lower(),
            customer.id,
            customer.name,
            None,
        )
