from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.events import TEMPLATE_KEYS, TEMPLATE_KEY_TO_EVENT


class NotificationSettingsResponse(BaseModel):
    email: dict[str, bool]


class UpdateNotificationSettingsRequest(BaseModel):
    model_config = {"extra": "ignore"}

    email: dict[str, bool] = Field(default_factory=dict)

    @field_validator("email")
    @classmethod
    def known_template_keys(cls, value: dict[str, bool]) -> dict[str, bool]:
        cleaned: dict[str, bool] = {}
        for key, enabled in value.items():
            if key not in TEMPLATE_KEY_TO_EVENT:
                raise ValueError(f"Unknown notification event: {key}")
            cleaned[key] = bool(enabled)
        return cleaned


class NotificationListItem(BaseModel):
    id: UUID
    organization_id: UUID
    shipment_id: UUID | None
    customer_id: UUID | None
    channel: str
    recipient: str | None
    template_key: str
    event_type: str
    tracking_number: str | None
    status: str
    attempts: int
    sent_at: datetime | None
    last_error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationListItem]
    page: int
    page_size: int
    total: int


class NotificationResponse(NotificationListItem):
    outbox_event_id: UUID
    updated_at: datetime


def default_email_settings() -> dict[str, bool]:
    return {key: True for key in TEMPLATE_KEYS.values()}
