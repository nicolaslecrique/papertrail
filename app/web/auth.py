"""Authentication wiring: the JWT cookie backend and fastapi-users dependencies.

This is the single place where the FastAPI dependency graph for auth is
assembled, which keeps the pure lower layers free of the web framework. It
reaches the db session and adapter through the domain layer's re-exports, so
the web layer never imports ``app.db`` directly (import-linter enforces this).
"""

import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)
from fastapi_users.db import BaseUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.domain.email import EmailSender, get_email_sender
from app.domain.pwned import PwnedPasswordChecker, get_pwned_checker
from app.domain.users import User, UserManager, build_user_db, get_async_session

_settings = get_settings()
cookie_transport = CookieTransport(
    cookie_name=_settings.cookie_name,
    cookie_max_age=_settings.access_token_lifetime_seconds,
    cookie_secure=_settings.cookie_secure,
    cookie_httponly=True,
    cookie_samesite=_settings.cookie_samesite,
)


def get_jwt_strategy() -> JWTStrategy[User, uuid.UUID]:
    """Build the stateless JWT strategy from the configured secret + lifetime."""
    settings = get_settings()
    return JWTStrategy(
        secret=settings.auth_secret,
        lifetime_seconds=settings.access_token_lifetime_seconds,
    )


auth_backend = AuthenticationBackend(
    name="jwt-cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)


async def get_user_db(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AsyncGenerator[BaseUserDatabase[User, uuid.UUID], None]:
    """Yield the fastapi-users db adapter bound to the request's session."""
    yield build_user_db(session)


async def get_user_manager(
    user_db: Annotated[BaseUserDatabase[User, uuid.UUID], Depends(get_user_db)],
    email_sender: Annotated[EmailSender, Depends(get_email_sender)],
    pwned_checker: Annotated[PwnedPasswordChecker, Depends(get_pwned_checker)],
) -> AsyncGenerator[UserManager, None]:
    """Yield a ``UserManager`` wired to the db adapter, email, and breach checker."""
    yield UserManager(user_db, email_sender, pwned_checker)


# pyrefly 1.1.1 cannot substitute fastapi-users' bounded, cross-module ``UP``
# TypeVar, so it misreads the (correct) manager/backend generics here. The wiring
# is exercised end to end by the tests; suppress the spurious argument-type error.
# pyrefly: ignore[bad-argument-type]
fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])
