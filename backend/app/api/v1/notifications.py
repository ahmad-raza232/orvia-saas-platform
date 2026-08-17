from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import TenantContext, require_roles
from app.core.events import TEMPLATE_KEY_TO_EVENT
from app.db.database import get_db
from app.models.role import (
    NOTIFICATION_READ_ROLES,
    NOTIFICATION_SETTINGS_WRITE_ROLES,
)
from app.schemas.notification import (
    NotificationListItem,
    NotificationListResponse,
    NotificationResponse,
    NotificationSettingsResponse,
    UpdateNotificationSettingsRequest,
)
from app.services.notification_service import NotificationQueryService, NotificationSettingsService

router = APIRouter(prefix="/notifications", tags=["notifications"])

require_notification_read = require_roles(*NOTIFICATION_READ_ROLES)
require_settings_write = require_roles(*NOTIFICATION_SETTINGS_WRITE_ROLES)


@router.get(
    "/settings",
    response_model=NotificationSettingsResponse,
    summary="Get notification settings",
    description="Returns email enablement per event type for the current organization. Missing rows use defaults (enabled).",
)
def get_notification_settings(
    ctx: TenantContext = Depends(require_notification_read),
    db: Session = Depends(get_db),
) -> NotificationSettingsResponse:
    email = NotificationSettingsService(db).get_email_settings(ctx.organization.id)
    return NotificationSettingsResponse(email=email)


@router.patch(
    "/settings",
    response_model=NotificationSettingsResponse,
    summary="Update notification settings",
    description="Tenant admins can enable or disable email notifications per event type. Organization is taken from membership context.",
)
def update_notification_settings(
    payload: UpdateNotificationSettingsRequest,
    ctx: TenantContext = Depends(require_settings_write),
    db: Session = Depends(get_db),
) -> NotificationSettingsResponse:
    email = NotificationSettingsService(db).update_email_settings(
        ctx.organization.id,
        payload.email,
        actor_user_id=ctx.user.id,
    )
    return NotificationSettingsResponse(email=email)


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List notifications",
    description="Tenant-scoped notification delivery history. Never includes provider credentials.",
)
def list_notifications(
    ctx: TenantContext = Depends(require_notification_read),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Literal["PENDING", "SENDING", "SENT", "FAILED", "SKIPPED"] | None = Query(
        default=None, alias="status"
    ),
    channel: Literal["EMAIL"] | None = Query(default=None),
    event_type: str | None = Query(default=None),
) -> NotificationListResponse:
    resolved_event = None
    if event_type:
        resolved_event = TEMPLATE_KEY_TO_EVENT.get(event_type, event_type)
    items, total = NotificationQueryService(db).list_for_organization(
        ctx.organization.id,
        page=page,
        page_size=page_size,
        status=status_filter,
        channel=channel,
        event_type=resolved_event,
    )
    return NotificationListResponse(
        items=[NotificationListItem.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Get a notification",
    description="Returns one notification in the current organization. Other tenants receive 404.",
)
def get_notification(
    notification_id: UUID,
    ctx: TenantContext = Depends(require_notification_read),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    notification = NotificationQueryService(db).get_for_organization(
        notification_id, ctx.organization.id
    )
    return NotificationResponse.model_validate(notification)
