"""User business logic: the fastapi-users ``UserManager`` and its lifecycle hooks.

Pure domain code: it orchestrates persistence through ``app.db`` and side effects
(sending mail) through the :class:`~app.domain.email.EmailSender` abstraction. It
also re-exports the db session and adapter factories so the web layer can build
its FastAPI dependency graph without importing ``app.db`` directly.
"""

import uuid
from typing import override

from fastapi_users import BaseUserManager, UUIDIDMixin, schemas
from fastapi_users.db import BaseUserDatabase
from fastapi_users.exceptions import InvalidPasswordException

from app.config import settings
from app.db.engine import get_async_session
from app.db.models import User
from app.db.users import build_user_db
from app.di import Request
from app.domain.email import EmailSender

__all__ = ["User", "UserManager", "build_user_db", "get_async_session"]

MIN_PASSWORD_LENGTH = 8

# fastapi-users declares its ``UP`` type variable (bound to ``UserProtocol``) in a
# separate module; pyrefly 1.1.1 fails to substitute that bounded, cross-module
# TypeVar into the inherited method signatures, so it sees the parent params as an
# unresolved ``UP`` and reports spurious "bad-override"/"bad-argument-type"
# errors on the correct overrides below. The overrides are sound (verified at
# runtime by the tests), so these specific checks are suppressed line by line.


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """Coordinates registration, email verification, and password resets."""

    reset_password_token_secret = settings.auth_secret
    verification_token_secret = settings.auth_secret

    def __init__(
        self, user_db: BaseUserDatabase[User, uuid.UUID], email_sender: EmailSender
    ) -> None:
        """Wire the manager to its db adapter and email sender."""
        super().__init__(user_db)  # pyrefly: ignore[bad-argument-type]
        self._email_sender = email_sender

    @override
    # pyrefly: ignore[bad-override]
    async def validate_password(
        self, password: str, user: schemas.BaseUserCreate | User
    ) -> None:
        """Reject weak passwords: enforce a minimum length and forbid the email."""
        if len(password) < MIN_PASSWORD_LENGTH:
            reason = f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
            raise InvalidPasswordException(reason)
        if user.email.casefold() in password.casefold():
            reason = "Password must not contain your email address."
            raise InvalidPasswordException(reason)

    @override
    # pyrefly: ignore[bad-override]
    async def on_after_request_verify(
        self,
        user: User,
        token: str,
        request: Request | None = None,
    ) -> None:
        """Send the email-confirmation link once a verification token is issued."""
        await self._email_sender.send_verification(user.email, token)

    @override
    # pyrefly: ignore[bad-override]
    async def on_after_forgot_password(
        self,
        user: User,
        token: str,
        request: Request | None = None,
    ) -> None:
        """Send the reset link once a password-reset token is issued."""
        await self._email_sender.send_password_reset(user.email, token)
