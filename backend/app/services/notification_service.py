from uuid import UUID

from sqlalchemy.orm import Session

from app.core.events import TEMPLATE_KEYS, TEMPLATE_KEY_TO_EVENT
from app.core.exceptions import NotFoundError
from app.models.notification import Notification
from app.repositories.notification_repository import (
    NotificationRepository,
    NotificationSettingRepository,
)
from app.services.audit_service import AuditService


class NotificationSettingsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = NotificationSettingRepository(db)
        self.audit = AuditService(db)

    def is_email_enabled(self, organization_id: UUID, event_type: str) -> bool:
        row = self.settings.get(organization_id, event_type)
        if row is None:
            return True
        return bool(row.email_enabled)

    def get_email_settings(self, organization_id: UUID) -> dict[str, bool]:
        rows = {row.event_type: row.email_enabled for row in self.settings.list_for_organization(organization_id)}
        return {TEMPLATE_KEYS[event_type]: bool(rows.get(event_type, True)) for event_type in TEMPLATE_KEYS}

    def update_email_settings(
        self,
        organization_id: UUID,
        email: dict[str, bool],
        actor_user_id: UUID | None = None,
    ) -> dict[str, bool]:
        changed = []
        for template_key, enabled in email.items():
            event_type = TEMPLATE_KEY_TO_EVENT.get(template_key)
            if event_type is None:
                continue
            self.settings.upsert(organization_id, event_type, bool(enabled))
            changed.append(template_key)
        if changed:
            self.audit.record(
                action="NOTIFICATION_SETTINGS_UPDATED",
                resource_type="notification_settings",
                resource_id=str(organization_id),
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                details={"keys": sorted(changed)},
            )
        self.db.commit()
        return self.get_email_settings(organization_id)


class NotificationQueryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.notifications = NotificationRepository(db)

    def list_for_organization(self, organization_id: UUID, **filters) -> tuple[list[Notification], int]:
        return self.notifications.list_for_organization(organization_id, **filters)

    def get_for_organization(self, notification_id: UUID, organization_id: UUID) -> Notification:
        notification = self.notifications.get_for_organization(notification_id, organization_id)
        if notification is None:
            raise NotFoundError("Notification not found.")
        return notification
