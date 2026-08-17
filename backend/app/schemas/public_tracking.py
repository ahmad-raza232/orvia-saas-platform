from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PublicTrackingHistoryItem(BaseModel):
    status: str
    previous_status: str | None = None
    note: str | None = None
    created_at: datetime


class PublicTrackingResponse(BaseModel):
    """Sanitized Softorica SaaS tracking payload for the public /track page.

    Intentionally omits organization IDs, CRM customer records, rider PII,
    emails, and full street addresses.
    """

    tracking_number: str
    status: str
    service_type: str
    origin_city: str
    destination_city: str
    receiver_name: str
    reference_number: str | None = None
    pieces: int = Field(ge=1)
    package_type: str | None = None
    created_at: datetime
    picked_up_at: datetime | None = None
    in_transit_at: datetime | None = None
    out_for_delivery_at: datetime | None = None
    delivered_at: datetime | None = None
    cancelled_at: datetime | None = None
    has_pod: bool = False
    history: list[PublicTrackingHistoryItem] = []
