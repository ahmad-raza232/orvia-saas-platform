from collections.abc import Callable
from datetime import datetime, timedelta, timezone
import logging
import time

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.pod_evidence import PodEvidenceStatus
from app.models.shipment import Shipment
from app.repositories.pod_evidence_repository import PodEvidenceRepository
from app.services.audit_service import AuditService

logger = logging.getLogger("orvia.pod_evidence_cleanup")

Clock = Callable[[], datetime]


class PodEvidenceCleanupService:
    """Expires abandoned PENDING POD evidence after the configured TTL.

    Database-only. Does not delete object-storage objects.
    """

    def __init__(
        self,
        db: Session,
        *,
        ttl_seconds: int | None = None,
        batch_size: int | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.db = db
        self.evidence = PodEvidenceRepository(db)
        self.audit = AuditService(db)
        self.ttl_seconds = (
            settings.pod_evidence_pending_ttl_seconds if ttl_seconds is None else ttl_seconds
        )
        self.batch_size = (
            settings.pod_evidence_cleanup_batch_size if batch_size is None else batch_size
        )
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def expire_stale_pending(self) -> dict[str, int]:
        started = time.perf_counter()
        now = self._clock()
        cutoff = now - timedelta(seconds=self.ttl_seconds)
        logger.info(
            "pod_evidence_cleanup.started batch_size=%s ttl_seconds=%s",
            self.batch_size,
            self.ttl_seconds,
        )
        try:
            rows = self.evidence.claim_stale_pending(cutoff=cutoff, limit=self.batch_size)
            scanned = len(rows)
            expired = 0
            skipped = 0
            for row in rows:
                if row.status != PodEvidenceStatus.PENDING.value:
                    skipped += 1
                    continue
                expired_at = now
                row.status = PodEvidenceStatus.EXPIRED.value
                row.expired_at = expired_at
                shipment = self.db.get(Shipment, row.shipment_id)
                tracking_number = shipment.tracking_number if shipment is not None else None
                created_at = row.created_at
                if created_at is not None and created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                self.audit.record(
                    action="POD_EVIDENCE_EXPIRED",
                    resource_type="pod_evidence",
                    resource_id=row.id,
                    organization_id=row.organization_id,
                    actor_user_id=None,
                    details={
                        "evidence_id": str(row.id),
                        "shipment_id": str(row.shipment_id),
                        "tracking_number": tracking_number,
                        "pod_id": str(row.pod_id),
                        "evidence_type": row.evidence_type,
                        "created_at": created_at.isoformat() if created_at else None,
                        "expired_at": expired_at.isoformat(),
                    },
                )
                expired += 1
            self.db.commit()
        except Exception:
            logger.exception("pod_evidence_cleanup.failed")
            self.db.rollback()
            raise
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "pod_evidence_cleanup.completed scanned=%s expired=%s skipped=%s "
            "duration_ms=%s batch_size=%s",
            scanned,
            expired,
            skipped,
            duration_ms,
            self.batch_size,
        )
        return {"scanned": scanned, "expired": expired, "skipped": skipped}


def expire_stale_pending_evidence(
    db: Session,
    *,
    ttl_seconds: int | None = None,
    batch_size: int | None = None,
    now: datetime | None = None,
) -> dict[str, int]:
    clock = (lambda: now) if now is not None else None
    return PodEvidenceCleanupService(
        db,
        ttl_seconds=ttl_seconds,
        batch_size=batch_size,
        clock=clock,
    ).expire_stale_pending()
