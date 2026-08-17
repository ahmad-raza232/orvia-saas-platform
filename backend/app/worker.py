"""Background worker that drains the notification outbox and expires stale POD evidence.

Run as a separate process:

    python -m app.worker

Does not send email inside shipment API transactions.
"""

from __future__ import annotations

from collections.abc import Callable
import logging
import signal
import threading
import time

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.services.email_provider import EmailProvider, get_email_provider
from app.services.outbox_processor import process_pending_outbox_events
from app.services.pod_evidence_cleanup import expire_stale_pending_evidence

logger = logging.getLogger("orvia.worker")

SessionFactory = Callable[[], Session]


class OutboxWorker:
    """Single-process poll loop. Does not spawn additional processors."""

    def __init__(
        self,
        session_factory: SessionFactory | None = None,
        email_provider: EmailProvider | None = None,
        *,
        poll_interval_seconds: float | None = None,
        batch_size: int | None = None,
    ) -> None:
        self._session_factory = session_factory or SessionLocal
        self._email_provider = email_provider
        self._poll_interval_seconds = (
            settings.outbox_poll_interval_seconds
            if poll_interval_seconds is None
            else poll_interval_seconds
        )
        self._batch_size = settings.outbox_batch_size if batch_size is None else batch_size
        self._stop = threading.Event()
        self._running = False
        self._last_cleanup_monotonic: float | None = None

    def stop(self) -> None:
        self._stop.set()

    def run_once(self) -> int:
        db = self._session_factory()
        try:
            provider = self._email_provider if self._email_provider is not None else get_email_provider()
            return process_pending_outbox_events(db, limit=self._batch_size, email_provider=provider)
        finally:
            db.close()

    def run_cleanup_once(self) -> dict[str, int]:
        db = self._session_factory()
        try:
            return expire_stale_pending_evidence(db)
        finally:
            db.close()

    def maybe_run_cleanup(self) -> dict[str, int] | None:
        if not settings.pod_evidence_cleanup_enabled:
            return None
        now = time.monotonic()
        interval = settings.pod_evidence_cleanup_interval_seconds
        if (
            self._last_cleanup_monotonic is not None
            and (now - self._last_cleanup_monotonic) < interval
        ):
            return None
        result = self.run_cleanup_once()
        self._last_cleanup_monotonic = now
        return result

    def run_cycle(self) -> None:
        if settings.outbox_worker_enabled:
            try:
                processed = self.run_once()
                if processed:
                    logger.info("worker.cycle processed=%s", processed)
            except Exception:
                logger.exception("worker.cycle_error")
        try:
            self.maybe_run_cleanup()
        except Exception:
            logger.exception("pod_evidence_cleanup.failed")

    def run_forever(self) -> None:
        if self._running:
            logger.warning("worker.already_running")
            return
        self._running = True
        logger.info(
            "worker.started poll_interval_seconds=%s batch_size=%s email_provider=%s "
            "pod_cleanup_enabled=%s pod_cleanup_interval_seconds=%s",
            self._poll_interval_seconds,
            self._batch_size,
            settings.email_provider,
            settings.pod_evidence_cleanup_enabled,
            settings.pod_evidence_cleanup_interval_seconds,
        )
        try:
            while not self._stop.is_set():
                self.run_cycle()
                self._stop.wait(self._poll_interval_seconds)
        finally:
            self._running = False
            logger.info("worker.stopped")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if not settings.outbox_worker_enabled:
        logger.info("worker.disabled")
        return
    worker = OutboxWorker()

    def handle(signum: int, _frame: object) -> None:
        logger.info("worker.stop_requested")
        worker.stop()

    signal.signal(signal.SIGINT, handle)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle)
    worker.run_forever()


if __name__ == "__main__":
    main()
