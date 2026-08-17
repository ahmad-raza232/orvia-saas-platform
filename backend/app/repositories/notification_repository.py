from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationSetting


class NotificationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, notification_id: UUID) -> Notification | None:
        return self.db.get(Notification, notification_id)

    def get_for_organization(
        self, notification_id: UUID, organization_id: UUID
    ) -> Notification | None:
        return (
            self.db.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.organization_id == organization_id,
            )
            .one_or_none()
        )

    def get_by_outbox_channel(self, outbox_event_id: UUID, channel: str) -> Notification | None:
        return (
            self.db.query(Notification)
            .filter(
                Notification.outbox_event_id == outbox_event_id,
                Notification.channel == channel,
            )
            .one_or_none()
        )

    def create(self, notification: Notification) -> Notification:
        self.db.add(notification)
        self.db.flush()
        return notification

    def list_for_organization(
        self,
        organization_id: UUID,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        channel: str | None = None,
        event_type: str | None = None,
    ) -> tuple[list[Notification], int]:
        stmt: Select[tuple[Notification]] = select(Notification).where(
            Notification.organization_id == organization_id
        )
        if status:
            stmt = stmt.where(Notification.status == status)
        if channel:
            stmt = stmt.where(Notification.channel == channel)
        if event_type:
            stmt = stmt.where(Notification.event_type == event_type)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int(self.db.execute(count_stmt).scalar_one())
        rows = (
            self.db.execute(
                stmt.order_by(Notification.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        return list(rows), total


class NotificationSettingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, organization_id: UUID, event_type: str) -> NotificationSetting | None:
        return (
            self.db.query(NotificationSetting)
            .filter(
                NotificationSetting.organization_id == organization_id,
                NotificationSetting.event_type == event_type,
            )
            .one_or_none()
        )

    def list_for_organization(self, organization_id: UUID) -> list[NotificationSetting]:
        return (
            self.db.query(NotificationSetting)
            .filter(NotificationSetting.organization_id == organization_id)
            .all()
        )

    def upsert(self, organization_id: UUID, event_type: str, email_enabled: bool) -> NotificationSetting:
        row = self.get(organization_id, event_type)
        if row is None:
            row = NotificationSetting(
                organization_id=organization_id,
                event_type=event_type,
                email_enabled=email_enabled,
            )
            self.db.add(row)
        else:
            row.email_enabled = email_enabled
        self.db.flush()
        return row
