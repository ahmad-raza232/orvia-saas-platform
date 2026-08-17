from abc import ABC, abstractmethod
from email.utils import formataddr
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("orvia.email")


class EmailDeliveryError(Exception):
    """Raised when an email provider cannot deliver a message."""


class EmailProvider(ABC):
    """Delivery adapter. Domain services must not call SMTP directly."""

    @abstractmethod
    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        metadata: dict | None = None,
    ) -> None:
        raise NotImplementedError


class LoggingEmailProvider(EmailProvider):
    """Development provider: records the message instead of sending it."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        metadata: dict | None = None,
    ) -> None:
        record = {
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "metadata": metadata or {},
        }
        self.sent.append(record)
        meta = metadata or {}
        logger.info(
            "email.recorded subject=%s notification_id=%s recipient=%s",
            subject,
            meta.get("notification_id"),
            recipient,
        )
        # Intentionally do not log message bodies (may contain invitation tokens).


class SmtpEmailProvider(EmailProvider):
    def _from_header(self) -> str:
        from_email = settings.smtp_from_address
        if not settings.smtp_host:
            raise EmailDeliveryError("SMTP is not configured: SMTP_HOST is required.")
        if not from_email:
            raise EmailDeliveryError("SMTP is not configured: SMTP_FROM_EMAIL is required.")
        if settings.smtp_from_name:
            return formataddr((settings.smtp_from_name, from_email))
        return from_email

    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        metadata: dict | None = None,
    ) -> None:
        from_header = self._from_header()
        message = EmailMessage()
        message["From"] = from_header
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        notification_id = (metadata or {}).get("notification_id")
        if notification_id:
            message["Message-ID"] = f"<{notification_id}@orvia.invalid>"
        timeout = max(1, int(settings.smtp_timeout_seconds))
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=timeout) as smtp:
                smtp.ehlo()
                if settings.smtp_use_tls:
                    smtp.starttls()
                    smtp.ehlo()
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password or "")
                smtp.send_message(message)
        except EmailDeliveryError:
            raise
        except smtplib.SMTPAuthenticationError:
            logger.warning("email.smtp_auth_failed notification_id=%s", notification_id)
            raise EmailDeliveryError("Email delivery failed.") from None
        except Exception:
            logger.warning("email.smtp_failed notification_id=%s", notification_id)
            raise EmailDeliveryError("Email delivery failed.") from None


def get_email_provider() -> EmailProvider:
    if settings.email_provider.lower().strip() == "smtp":
        return SmtpEmailProvider()
    return LoggingEmailProvider()
