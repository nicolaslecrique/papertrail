"""Backend check that a chosen password hasn't appeared in a known breach.

Uses Have I Been Pwned's k-Anonymity range API: only the first five hex chars of
the password's SHA-1 hash ever leave the server — the plaintext (and the full
hash) never do. The domain triggers this from ``UserManager.validate_password``;
the backend is chosen by configuration (``disabled`` skips the network so tests
and offline dev stay deterministic).
"""

import hashlib
import logging
from typing import Protocol

import httpx

from app.config import get_settings

_logger = logging.getLogger("papertrail.pwned")

_HIBP_RANGE_URL = "https://api.pwnedpasswords.com/range/"
_HIBP_TIMEOUT_SECONDS = 5.0


class PwnedPasswordChecker(Protocol):
    """Reports whether a password has shown up in a known data breach."""

    async def times_pwned(self, password: str) -> int:
        """Return how many breaches ``password`` appears in (0 if none/unknown)."""


class HibpPwnedPasswordChecker:
    """Queries Have I Been Pwned's k-Anonymity range API (production)."""

    async def times_pwned(self, password: str) -> int:
        """Return the breach count HIBP reports for ``password``.

        Fails open: if HIBP is unreachable we log and return 0 rather than block
        every sign-up on an outage. The minimum-length rule still applies.
        """
        # SHA-1 is what the HIBP range API is keyed on — not a security choice.
        digest = hashlib.sha1(password.encode()).hexdigest().upper()  # noqa: S324
        prefix, suffix = digest[:5], digest[5:]
        try:
            async with httpx.AsyncClient(timeout=_HIBP_TIMEOUT_SECONDS) as http:
                response = await http.get(f"{_HIBP_RANGE_URL}{prefix}")
                response.raise_for_status()
        except httpx.HTTPError:
            _logger.warning("HIBP breach check unavailable; allowing the password")
            return 0
        try:
            return _count_in_range(response.text, suffix)
        except ValueError:
            # A malformed range body (non-numeric count) must not 500 the sign-up;
            # fail open like an outage does, since the length rule still applies.
            _logger.warning("Malformed HIBP range response; allowing the password")
            return 0


class DisabledPwnedPasswordChecker:
    """No-op checker for offline dev and tests (never touches the network)."""

    async def times_pwned(self, password: str) -> int:  # noqa: ARG002
        """Report every password as not-breached."""
        return 0


def _count_in_range(body: str, suffix: str) -> int:
    """Find ``suffix`` in an HIBP range response body, returning its breach count.

    Each line is ``HASH_SUFFIX:COUNT``; the suffix is absent when count is 0.
    """
    for line in body.splitlines():
        candidate, _, count = line.partition(":")
        if candidate.strip().upper() == suffix:
            return int(count)
    return 0


def get_pwned_checker() -> PwnedPasswordChecker:
    """Return the breach checker selected by ``settings.pwned_check_enabled``."""
    if get_settings().pwned_check_enabled:
        return HibpPwnedPasswordChecker()
    return DisabledPwnedPasswordChecker()
