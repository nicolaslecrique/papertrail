"""Outbound transactional email for the auth flows (verify + password reset).

The domain triggers these from the ``UserManager`` hooks. The backend is chosen
by configuration: ``console`` just logs the link (handy in dev and trivial to
assert against in tests); ``smtp`` sends a real message via aiosmtplib.
"""

import logging
from email.message import EmailMessage
from typing import Protocol

import aiosmtplib

from app.config import settings

_logger = logging.getLogger("papertrail.email")


class EmailSender(Protocol):
    """Sends the transactional emails the auth flows depend on."""

    async def send_verification(self, email: str, token: str) -> None:
        """Deliver an email-confirmation link to ``email``."""

    async def send_password_reset(self, email: str, token: str) -> None:
        """Deliver a password-reset link to ``email``."""


def _verify_url(token: str) -> str:
    return f"{settings.base_url}/verify?token={token}"


def _reset_url(token: str) -> str:
    return f"{settings.base_url}/reset-password?token={token}"


class ConsoleEmailSender:
    """Logs the auth links instead of sending mail (development / tests)."""

    async def send_verification(self, email: str, token: str) -> None:
        """Log the confirmation link for ``email``."""
        _logger.info("Confirm %s by visiting %s", email, _verify_url(token))

    async def send_password_reset(self, email: str, token: str) -> None:
        """Log the password-reset link for ``email``."""
        _logger.info(
            "Reset the password for %s by visiting %s", email, _reset_url(token)
        )


class SmtpEmailSender:
    """Sends the auth emails through a configured SMTP server (production)."""

    async def send_verification(self, email: str, token: str) -> None:
        """Email the confirmation link to ``email``."""
        await self._send(
            email,
            "Confirm your papertrail account",
            f"Confirm your account: {_verify_url(token)}",
        )

    async def send_password_reset(self, email: str, token: str) -> None:
        """Email the password-reset link to ``email``."""
        await self._send(
            email,
            "Reset your papertrail password",
            f"Reset your password: {_reset_url(token)}",
        )

    async def _send(self, recipient: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = settings.email_from
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_start_tls,
        )


def get_email_sender() -> EmailSender:
    """Return the email sender selected by ``settings.email_backend``."""
    if settings.email_backend == "smtp":
        return SmtpEmailSender()
    return ConsoleEmailSender()
