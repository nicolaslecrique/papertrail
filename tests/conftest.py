"""Shared pytest fixtures: an async test database and an HTTP client.

The app is pointed at a dedicated ``papertrail_test`` database (created on demand)
and a throwaway auth secret. This *must* happen before importing anything that
reads settings, because the engine and ``Settings`` are built at import time.
"""

import asyncio
import os
import threading
from collections.abc import AsyncIterator, Coroutine
from dataclasses import dataclass, field

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://papertrail:papertrail@db:5432/papertrail_test",
)
os.environ["AUTH_SECRET"] = "test-secret-not-for-production-0123456789"
os.environ["EMAIL_BACKEND"] = "console"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.db.engine import Base, get_async_session
from app.domain.email import get_email_sender
from app.main import app

_TEST_DB_NAME = "papertrail_test"


def _run[T](coro: Coroutine[object, object, T]) -> T:
    """Run a coroutine to completion in a throwaway thread with its own loop.

    Lets a synchronous, session-scoped fixture drive async setup without a
    session-scoped asyncio event loop: the coroutine runs on its own loop in a
    separate thread, and the NullPool test engine means no connection is shared
    across loops.
    """
    box: list[T] = []

    def _runner() -> None:
        box.append(asyncio.run(coro))

    thread = threading.Thread(target=_runner)
    thread.start()
    thread.join()
    return box[0]


# A NullPool engine never caches connections, so it can be used safely from any
# event loop (the per-test loop or a throwaway asyncio.run loop) without
# asyncpg's "attached to a different loop" errors.
_test_engine = create_async_engine(settings.async_database_url, poolclass=NullPool)
_test_session_maker = async_sessionmaker(_test_engine, expire_on_commit=False)


# --------------------------------------------------------------------------- #
# Capturing email sender — records the tokens the auth flows would email out.
# --------------------------------------------------------------------------- #
@dataclass
class SentEmail:
    """One captured outbound email."""

    kind: str
    email: str
    token: str


@dataclass
class CapturingEmailSender:
    """An ``EmailSender`` that records what it would have sent."""

    sent: list[SentEmail] = field(default_factory=list)

    async def send_verification(self, email: str, token: str) -> None:
        """Record a verification email."""
        self.sent.append(SentEmail("verify", email, token))

    async def send_password_reset(self, email: str, token: str) -> None:
        """Record a password-reset email."""
        self.sent.append(SentEmail("reset", email, token))

    def last_token(self, kind: str) -> str:
        """Return the most recent token of the given kind."""
        return next(email.token for email in reversed(self.sent) if email.kind == kind)


# --------------------------------------------------------------------------- #
# Database lifecycle.
# --------------------------------------------------------------------------- #
async def _setup_database() -> None:
    admin_url = settings.async_database_url.rsplit("/", 1)[0] + "/papertrail"
    admin_engine = create_async_engine(
        admin_url,
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    async with admin_engine.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": _TEST_DB_NAME},
        )
        if not exists:
            await conn.execute(text(f'CREATE DATABASE "{_TEST_DB_NAME}"'))
    await admin_engine.dispose()
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(scope="session", autouse=True)
def _prepare_database() -> None:
    """Create the test database and schema once per test session."""
    _run(_setup_database())


async def _truncate_users() -> None:
    async with _test_engine.begin() as conn:
        await conn.execute(text('TRUNCATE TABLE "user" CASCADE'))


# --------------------------------------------------------------------------- #
# HTTP client + dependency overrides (async integration tests).
# --------------------------------------------------------------------------- #
@pytest.fixture
def email_sender() -> CapturingEmailSender:
    """Return a fresh capturing email sender, shared with the app via DI."""
    return CapturingEmailSender()


@pytest_asyncio.fixture
async def client(email_sender: CapturingEmailSender) -> AsyncIterator[AsyncClient]:
    """Yield an httpx client bound to the app, using the test DB + fake email."""

    async def _session_override() -> AsyncIterator[AsyncSession]:
        async with _test_session_maker() as session:
            yield session

    app.dependency_overrides[get_async_session] = _session_override
    app.dependency_overrides[get_email_sender] = lambda: email_sender
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as http:
            yield http
    finally:
        app.dependency_overrides.clear()
        await _truncate_users()
