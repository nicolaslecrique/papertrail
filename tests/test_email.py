"""Unit tests for the email sender abstraction."""

import logging
from email.message import EmailMessage

import aiosmtplib
import pytest

from app.domain import email as email_module
from app.domain.email import ConsoleEmailSender, SmtpEmailSender, get_email_sender


async def test_console_sender_logs_verification_link(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="papertrail.email")
    await ConsoleEmailSender().send_verification("a@b.com", "vtok")
    assert "/verify?token=vtok" in caplog.text


async def test_console_sender_logs_reset_link(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="papertrail.email")
    await ConsoleEmailSender().send_password_reset("a@b.com", "rtok")
    assert "/reset-password?token=rtok" in caplog.text


def test_get_email_sender_defaults_to_console() -> None:
    assert isinstance(get_email_sender(), ConsoleEmailSender)


def test_get_email_sender_returns_smtp_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(email_module.get_settings(), "email_backend", "smtp")
    assert isinstance(get_email_sender(), SmtpEmailSender)


async def test_smtp_sender_builds_and_sends_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, EmailMessage] = {}

    async def fake_send(
        message: object, **_kwargs: object
    ) -> tuple[dict[str, object], str]:
        assert isinstance(message, EmailMessage)
        captured["message"] = message
        return {}, "ok"

    monkeypatch.setattr(aiosmtplib, "send", fake_send)
    await SmtpEmailSender().send_password_reset("a@b.com", "rtok")
    message = captured["message"]
    assert message["To"] == "a@b.com"
    assert "/reset-password?token=rtok" in message.get_content()


async def test_smtp_sender_builds_verification_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, EmailMessage] = {}

    async def fake_send(
        message: object, **_kwargs: object
    ) -> tuple[dict[str, object], str]:
        assert isinstance(message, EmailMessage)
        captured["message"] = message
        return {}, "ok"

    monkeypatch.setattr(aiosmtplib, "send", fake_send)
    await SmtpEmailSender().send_verification("a@b.com", "vtok")
    message = captured["message"]
    assert message["To"] == "a@b.com"
    assert "/verify?token=vtok" in message.get_content()
