from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import UUID
import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.events import CHANNEL_EMAIL, TEMPLATE_KEYS
from app.models.notification import Notification
from app.models.outbox import OutboxEvent
from app.models.shipment import Shipment
from app.repositories.notification_repository import NotificationRepository
from app.repositories.outbox_repository import OutboxRepository
from app.services.email_provider import EmailDeliveryError, EmailProvider, get_email_provider
from app.services.notification_service import NotificationSettingsService
from app.services.notification_templates import render_email, template_variables
from app.services.recipient_resolver import RecipientResolver

logger = logging.getLogger("orvia.outbox")

Clock = Callable[[], datetime]


class OutboxProcessor:
    """Claims pending outbox events and attempts notification delivery.

    Safe to call from cron, a worker, or tests. Does not belong in HTTP request
    handlers that mutate shipments.
    """

    def __init__(
        self,
        db: Session,
        email_provider: EmailProvider | None = None,
        *,
        max_attempts: int | None = None,
        retry_base_seconds: int | None = None,
        processing_timeout_seconds: int | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.db = db
        self.outbox = OutboxRepository(db)
        self.notifications = NotificationRepository(db)
        self.settings = NotificationSettingsService(db)
        self.resolver = RecipientResolver()
        self.email = email_provider or get_email_provider()
        self.max_attempts = max_attempts if max_attempts is not None else settings.outbox_max_attempts
        self.retry_base_seconds = (
            retry_base_seconds if retry_base_seconds is not None else settings.outbox_retry_base_seconds
        )
        self.processing_timeout_seconds = (
            processing_timeout_seconds
            if processing_timeout_seconds is not None
            else settings.outbox_processing_timeout_seconds
        )
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _now(self) -> datetime:
        return self._clock()

    def process_pending(self, limit: int | None = None) -> int:
        batch_size = settings.outbox_batch_size if limit is None else limit
        recovered = self.outbox.recover_stuck(
            now=self._now(), timeout_seconds=self.processing_timeout_seconds
        )
        if recovered:
            logger.info("outbox.recovered count=%s", len(recovered))
            self.db.commit()

        claimed = self.outbox.claim_pending(now=self._now(), limit=batch_size)
        claimed_ids = [event.id for event in claimed]
        if claimed_ids:
            logger.info("outbox.claimed count=%s", len(claimed_ids))
            self.db.commit()

        processed = 0
        for event_id in claimed_ids:
            event = self.outbox.get_by_id(event_id)
            if event is None:
                continue
            try:
                self._process_event(event, now=self._now())
                self.db.commit()
            except Exception:
                logger.exception("outbox.event_error event_id=%s", event_id)
                self.db.rollback()
                self._release_claim(event_id)
            processed += 1
        return processed

    def _release_claim(self, event_id: UUID) -> None:
        event = self.outbox.get_by_id(event_id)
        if event is None or event.status != "PROCESSING":
            return
        now = self._now()
        event.attempts += 1
        event.processing_started_at = None
        event.updated_at = now
        event.last_error = "PROCESSOR_ERROR"
        if event.attempts >= self.max_attempts:
            event.status = "FAILED"
            event.processed_at = now
            logger.warning(
                "outbox.final_failure event_id=%s event_type=%s reason=PROCESSOR_ERROR attempts=%s",
                event.id,
                event.event_type,
                event.attempts,
            )
        else:
            delay = self.retry_base_seconds * (2 ** (event.attempts - 1))
            event.status = "PENDING"
            event.available_at = now + timedelta(seconds=delay)
            event.processed_at = None
            logger.info(
                "outbox.retry_scheduled event_id=%s attempts=%s delay_seconds=%s reason=PROCESSOR_ERROR",
                event.id,
                event.attempts,
                delay,
            )
        self.db.commit()

    def _process_event(self, event: OutboxEvent, *, now: datetime) -> None:
        notification = self._get_or_create_notification(event)
        if notification.status in {"SENT", "SKIPPED"}:
            event.status = "PROCESSED"
            event.processed_at = now
            event.processing_started_at = None
            event.updated_at = now
            logger.info(
                "outbox.event_processed event_id=%s event_type=%s status=PROCESSED",
                event.id,
                event.event_type,
            )
            return

        if not self.settings.is_email_enabled(event.organization_id, event.event_type):
            self._skip(event, notification, "EVENT_DISABLED", now)
            return

        shipment = self._load_shipment(event)
        if shipment is None or shipment.organization_id != event.organization_id:
            self._fail_terminal(event, notification, "SHIPMENT_NOT_FOUND", now)
            return

        resolved = self.resolver.resolve_email(shipment)
        notification.customer_id = resolved.customer_id
        notification.tracking_number = shipment.tracking_number
        notification.shipment_id = shipment.id
        if resolved.skipped:
            self._skip(event, notification, resolved.skipped_reason or "SKIPPED", now)
            return

        notification.recipient = resolved.email
        notification.status = "SENDING"
        notification.updated_at = now
        self.db.flush()

        variables = template_variables(
            tracking_number=shipment.tracking_number,
            customer_name=resolved.customer_name,
            shipment_status=shipment.status,
            delivered_at=shipment.delivered_at,
        )
        subject, body = render_email(event.event_type, variables)
        try:
            self.email.send(
                resolved.email or "",
                subject,
                body,
                metadata={
                    "notification_id": str(notification.id),
                    "organization_id": str(event.organization_id),
                    "event_type": event.event_type,
                    "tracking_number": shipment.tracking_number,
                },
            )
        except Exception as exc:
            message = "Email delivery failed."
            if isinstance(exc, EmailDeliveryError):
                message = str(exc)[:500]
            self._retry_or_fail(event, notification, message, now)
            return

        notification.status = "SENT"
        notification.attempts += 1
        notification.sent_at = now
        notification.last_error = None
        notification.updated_at = now
        event.status = "PROCESSED"
        event.attempts += 1
        event.processed_at = now
        event.processing_started_at = None
        event.last_error = None
        event.updated_at = now
        logger.info(
            "outbox.notification_sent event_id=%s notification_id=%s event_type=%s tracking_number=%s",
            event.id,
            notification.id,
            event.event_type,
            shipment.tracking_number,
        )
        logger.info(
            "outbox.event_processed event_id=%s event_type=%s status=PROCESSED",
            event.id,
            event.event_type,
        )

    def _get_or_create_notification(self, event: OutboxEvent) -> Notification:
        existing = self.notifications.get_by_outbox_channel(event.id, CHANNEL_EMAIL)
        if existing is not None:
            return existing
        shipment_id = event.payload.get("shipment_id") if isinstance(event.payload, dict) else None
        tracking_number = event.payload.get("tracking_number") if isinstance(event.payload, dict) else None
        customer_id = event.payload.get("customer_id") if isinstance(event.payload, dict) else None
        notification = Notification(
            organization_id=event.organization_id,
            outbox_event_id=event.id,
            shipment_id=UUID(shipment_id) if shipment_id else None,
            customer_id=UUID(customer_id) if customer_id else None,
            channel=CHANNEL_EMAIL,
            template_key=TEMPLATE_KEYS[event.event_type],
            event_type=event.event_type,
            tracking_number=tracking_number,
            status="PENDING",
            attempts=0,
        )
        try:
            with self.db.begin_nested():
                return self.notifications.create(notification)
        except IntegrityError:
            existing = self.notifications.get_by_outbox_channel(event.id, CHANNEL_EMAIL)
            if existing is None:
                raise
            return existing

    def _load_shipment(self, event: OutboxEvent) -> Shipment | None:
        shipment_id = None
        if isinstance(event.payload, dict) and event.payload.get("shipment_id"):
            shipment_id = UUID(str(event.payload["shipment_id"]))
        elif event.aggregate_type == "shipment":
            shipment_id = event.aggregate_id
        if shipment_id is None:
            return None
        return (
            self.db.query(Shipment)
            .options(selectinload(Shipment.customer))
            .filter(Shipment.id == shipment_id)
            .one_or_none()
        )

    def _skip(self, event: OutboxEvent, notification: Notification, reason: str, now: datetime) -> None:
        notification.status = "SKIPPED"
        notification.last_error = reason
        notification.updated_at = now
        event.status = "PROCESSED"
        event.processed_at = now
        event.processing_started_at = None
        event.last_error = reason
        event.updated_at = now
        logger.info(
            "outbox.notification_skipped event_id=%s event_type=%s reason=%s",
            event.id,
            event.event_type,
            reason,
        )
        logger.info(
            "outbox.event_processed event_id=%s event_type=%s status=PROCESSED",
            event.id,
            event.event_type,
        )

    def _fail_terminal(
        self, event: OutboxEvent, notification: Notification, reason: str, now: datetime
    ) -> None:
        notification.status = "FAILED"
        notification.last_error = reason
        notification.updated_at = now
        event.status = "FAILED"
        event.last_error = reason
        event.processed_at = now
        event.processing_started_at = None
        event.updated_at = now
        logger.warning(
            "outbox.final_failure event_id=%s event_type=%s reason=%s",
            event.id,
            event.event_type,
            reason,
        )

    def _retry_or_fail(
        self, event: OutboxEvent, notification: Notification, message: str, now: datetime
    ) -> None:
        notification.attempts += 1
        notification.status = "FAILED"
        notification.last_error = message
        notification.updated_at = now
        event.attempts += 1
        event.last_error = message
        event.processing_started_at = None
        event.updated_at = now
        logger.warning(
            "outbox.notification_failed event_id=%s event_type=%s attempts=%s",
            event.id,
            event.event_type,
            event.attempts,
        )
        if event.attempts >= self.max_attempts:
            event.status = "FAILED"
            event.processed_at = now
            logger.warning(
                "outbox.final_failure event_id=%s event_type=%s attempts=%s",
                event.id,
                event.event_type,
                event.attempts,
            )
        else:
            delay = self.retry_base_seconds * (2 ** (event.attempts - 1))
            event.status = "PENDING"
            event.available_at = now + timedelta(seconds=delay)
            event.processed_at = None
            logger.info(
                "outbox.retry_scheduled event_id=%s attempts=%s delay_seconds=%s",
                event.id,
                event.attempts,
                delay,
            )


def process_pending_outbox_events(
    db: Session,
    limit: int | None = None,
    email_provider: EmailProvider | None = None,
) -> int:
    return OutboxProcessor(db, email_provider).process_pending(limit=limit)
