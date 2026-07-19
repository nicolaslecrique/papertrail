"""Reject sign-ups that use a disposable / throwaway email provider.

A throwaway address (mailinator, 10minutemail, …) lets someone pass email
verification without a real, durable inbox — handy for spamming the account base
or evading a per-person limit. We refuse the known disposable domains at
registration. The block list ships with the ``disposable-email-domains`` package
as a plain in-memory set, so this is a pure local lookup: no network, fully
deterministic in tests. The domain layer owns the rule; the web layer catches
:class:`DisposableEmailError` and returns the message as a JSON error.
"""

from disposable_email_domains import blocklist
from fastapi_users.exceptions import FastAPIUsersException


class DisposableEmailError(FastAPIUsersException):
    """Raised when a registration email uses a known disposable domain."""


def is_disposable_email(email: str) -> bool:
    """Return whether ``email``'s domain is a known disposable/throwaway provider.

    The block list is stored lower-cased, so the domain is folded before lookup.
    An address with no ``@`` has no domain to match and is treated as not
    disposable (its format is rejected elsewhere).
    """
    _, at, domain = email.rpartition("@")
    if not at:
        return False
    return domain.casefold() in blocklist
