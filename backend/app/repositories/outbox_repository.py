from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.outbox import OutboxEvent


class OutboxRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def enqueue(
        self,
        *,
        organization_id: UUID,
        event_type: str,
        aggregate_type: str,
        aggregate_id: UUID,
        payload: dict,
        available_at: datetime,
    ) -> None:
        """Insert an outbox row. Duplicate lifecycle events are ignored."""
        stmt = (
            insert(OutboxEvent)
            .values(
                id=uuid4(),
                organization_id=organization_id,
                event_type=event_type,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                payload=payload,
                status="PENDING",
                attempts=0,
                available_at=available_at,
            )
            .on_conflict_do_nothing(constraint="uq_outbox_org_event_aggregate")
        )
        self.db.execute(stmt)

    def claim_pending(self, *, now: datetime, limit: int) -> list[OutboxEvent]:
        events = (
            self.db.query(OutboxEvent)
            .filter(
                OutboxEvent.status == "PENDING",
                OutboxEvent.available_at <= now,
            )
            .order_by(OutboxEvent.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
            .all()
        )
        for event in events:
            event.status = "PROCESSING"
            event.processing_started_at = now
            event.updated_at = now
        if events:
            self.db.flush()
        return events

    def recover_stuck(self, *, now: datetime, timeout_seconds: int) -> list[OutboxEvent]:
        cutoff = now - timedelta(seconds=timeout_seconds)
        events = (
            self.db.query(OutboxEvent)
            .filter(
                OutboxEvent.status == "PROCESSING",
                or_(
                    and_(
                        OutboxEvent.processing_started_at.isnot(None),
                        OutboxEvent.processing_started_at <= cutoff,
                    ),
                    and_(
                        OutboxEvent.processing_started_at.is_(None),
                        OutboxEvent.updated_at <= cutoff,
                    ),
                ),
            )
            .with_for_update(skip_locked=True)
            .all()
        )
        for event in events:
            event.status = "PENDING"
            event.available_at = now
            event.processing_started_at = None
            event.updated_at = now
            event.last_error = "STALE_PROCESSING_RECOVERED"
        if events:
            self.db.flush()
        return events

    def get_by_id(self, event_id: UUID) -> OutboxEvent | None:
        return self.db.get(OutboxEvent, event_id)

    def list_for_organization(
        self,
        organization_id: UUID,
        *,
        event_type: str | None = None,
        aggregate_id: UUID | None = None,
    ) -> list[OutboxEvent]:
        stmt: Select[tuple[OutboxEvent]] = select(OutboxEvent).where(
            OutboxEvent.organization_id == organization_id
        )
        if event_type:
            stmt = stmt.where(OutboxEvent.event_type == event_type)
        if aggregate_id:
            stmt = stmt.where(OutboxEvent.aggregate_id == aggregate_id)
        return list(self.db.execute(stmt.order_by(OutboxEvent.created_at.asc())).scalars().all())

    def count_for_organization(self, organization_id: UUID, event_type: str | None = None) -> int:
        stmt = select(func.count()).select_from(OutboxEvent).where(
            OutboxEvent.organization_id == organization_id
        )
        if event_type:
            stmt = stmt.where(OutboxEvent.event_type == event_type)
        return int(self.db.execute(stmt).scalar_one())
