"""Unit tests for the Have I Been Pwned breach checker."""

import hashlib
import logging
from typing import Self

import httpx
import pytest

from app.domain import pwned as pwned_module
from app.domain.pwned import (
    DisabledPwnedPasswordChecker,
    HibpPwnedPasswordChecker,
    get_pwned_checker,
)

PASSWORD = "correct horse battery"


def _range_body_for(password: str, count: int) -> str:
    """Build an HIBP range response whose suffix line reports ``count`` breaches."""
    suffix = hashlib.sha1(password.encode()).hexdigest().upper()[5:]  # noqa: S324
    # Realistic body: a couple of unrelated suffixes plus the one we care about.
    return f"00000000000000000000000000000000000:7\r\n{suffix}:{count}\r\n"


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        """Succeed: the fake always returns a 200-equivalent body."""


def _patch_client(monkeypatch: pytest.MonkeyPatch, *, body: str) -> None:
    """Make the checker's ``httpx.AsyncClient`` return ``body`` without a network."""

    class _FakeClient:
        def __init__(self, **_kwargs: object) -> None: ...

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_exc: object) -> bool:
            return False

        async def get(self, _url: str) -> _FakeResponse:
            return _FakeResponse(body)

    monkeypatch.setattr(pwned_module.httpx, "AsyncClient", _FakeClient)


async def test_hibp_reports_breach_count(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch, body=_range_body_for(PASSWORD, 4200))
    assert await HibpPwnedPasswordChecker().times_pwned(PASSWORD) == 4200


async def test_hibp_allows_unseen_password(monkeypatch: pytest.MonkeyPatch) -> None:
    # A body that does not contain this password's suffix means "not found".
    _patch_client(monkeypatch, body=_range_body_for("some other password", 9))
    assert await HibpPwnedPasswordChecker().times_pwned(PASSWORD) == 0


async def test_hibp_fails_open_on_malformed_body(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # A non-numeric count must not 500 the sign-up; fail open like an outage does.
    suffix = hashlib.sha1(PASSWORD.encode()).hexdigest().upper()[5:]  # noqa: S324
    _patch_client(monkeypatch, body=f"{suffix}:not-a-number\r\n")
    caplog.set_level(logging.WARNING, logger="papertrail.pwned")
    assert await HibpPwnedPasswordChecker().times_pwned(PASSWORD) == 0
    assert "malformed" in caplog.text.lower()


async def test_hibp_fails_open_on_network_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class _BrokenClient:
        def __init__(self, **_kwargs: object) -> None: ...

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_exc: object) -> bool:
            return False

        async def get(self, _url: str) -> object:
            msg = "boom"
            raise httpx.ConnectError(msg)

    monkeypatch.setattr(pwned_module.httpx, "AsyncClient", _BrokenClient)
    caplog.set_level(logging.WARNING, logger="papertrail.pwned")
    assert await HibpPwnedPasswordChecker().times_pwned(PASSWORD) == 0
    assert "unavailable" in caplog.text


async def test_disabled_checker_never_pwned() -> None:
    assert await DisabledPwnedPasswordChecker().times_pwned(PASSWORD) == 0


def test_get_pwned_checker_defaults_to_hibp() -> None:
    assert isinstance(get_pwned_checker(), HibpPwnedPasswordChecker)


def test_get_pwned_checker_disabled_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pwned_module.get_settings(), "pwned_check_enabled", value=False)
    assert isinstance(get_pwned_checker(), DisabledPwnedPasswordChecker)
