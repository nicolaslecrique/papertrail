"""Unit tests for the disposable-email domain rule."""

import pytest

from app.domain.email_domains import is_disposable_email


@pytest.mark.parametrize(
    "email",
    [
        "throwaway@mailinator.com",
        "USER@MAILINATOR.COM",  # domain match is case-insensitive
        "someone@10minutemail.com",
    ],
)
def test_disposable_domains_are_rejected(email: str) -> None:
    assert is_disposable_email(email) is True


@pytest.mark.parametrize(
    "email",
    [
        "alice@example.com",
        "bob@gmail.com",
        "no-at-sign",  # no domain to match; format is rejected elsewhere
        "trailing@",
    ],
)
def test_legitimate_or_malformed_emails_pass(email: str) -> None:
    assert is_disposable_email(email) is False
