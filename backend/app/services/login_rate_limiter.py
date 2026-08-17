from datetime import datetime, timedelta, timezone
from math import ceil

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import TooManyRequestsError
from app.core.security import hash_invitation_token
from app.models.login_attempt import LoginAttemptWindow


def _key_hash(email: str) -> str:
    return hash_invitation_token(f"login:{email.strip().lower()}")


class LoginRateLimiter:
    """Database-backed failed-login limiter. Independent of tenant context."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _enabled(self) -> bool:
        return bool(settings.auth_login_rate_limit_enabled)

    def _load_for_update(self, key_hash: str) -> LoginAttemptWindow | None:
        return (
            self.db.query(LoginAttemptWindow)
            .filter(LoginAttemptWindow.key_hash == key_hash)
            .with_for_update()
            .one_or_none()
        )

    def _retry_after(self, locked_until: datetime, now: datetime) -> int:
        return max(1, ceil((locked_until - now).total_seconds()))

    def precheck(self, email: str) -> None:
        if not self._enabled():
            return
        now = datetime.now(timezone.utc)
        row = self._load_for_update(_key_hash(email))
        if row is None:
            return
        if row.locked_until is not None and row.locked_until > now:
            raise TooManyRequestsError(self._retry_after(row.locked_until, now))

    def register_failure(self, email: str) -> None:
        if not self._enabled():
            return
        now = datetime.now(timezone.utc)
        window = timedelta(seconds=settings.auth_login_rate_limit_window_seconds)
        key_hash = _key_hash(email)
        row = self._load_for_update(key_hash)
        if row is None:
            row = LoginAttemptWindow(
                key_hash=key_hash,
                failed_count=0,
                window_started_at=now,
                locked_until=None,
            )
            try:
                with self.db.begin_nested():
                    self.db.add(row)
                    self.db.flush()
            except IntegrityError:
                row = self._load_for_update(key_hash)
                if row is None:
                    return
        if row.locked_until is not None and row.locked_until > now:
            self.db.commit()
            raise TooManyRequestsError(self._retry_after(row.locked_until, now))
        if row.locked_until is not None and row.locked_until <= now:
            row.locked_until = None
            row.failed_count = 0
            row.window_started_at = now
        elif row.window_started_at + window <= now:
            row.failed_count = 0
            row.window_started_at = now
            row.locked_until = None
        row.failed_count += 1
        row.updated_at = now
        if row.failed_count >= settings.auth_login_rate_limit_max_attempts:
            row.locked_until = now + window
            retry_after = self._retry_after(row.locked_until, now)
            self.db.commit()
            raise TooManyRequestsError(retry_after)
        self.db.commit()

    def clear(self, email: str) -> None:
        if not self._enabled():
            return
        row = self._load_for_update(_key_hash(email))
        if row is None:
            return
        self.db.delete(row)
        self.db.flush()
