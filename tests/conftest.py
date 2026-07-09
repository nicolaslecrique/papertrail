"""Shared pytest fixtures: async test database, HTTP client, and live server.

The app is pointed at a dedicated ``papertrail_test`` database (created on demand)
and a throwaway auth secret. This *must* happen before importing anything that
reads settings, because the engine and ``Settings`` are built at import time.
"""

import asyncio
import os
import socket
import threading
import time
from collections.abc import AsyncIterator, Coroutine, Iterator
from dataclasses import dataclass, field
from typing import cast

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://papertrail:papertrail@db:5432/papertrail_test",
)
os.environ["AUTH_SECRET"] = "test-secret-not-for-production-0123456789"
os.environ["EMAIL_BACKEND"] = "console"

import pytest
import pytest_asyncio
import uvicorn
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.db.engine import Base, get_async_session
from app.domain.email import get_email_sender
from app.domain.schemas import UserCreate
from app.domain.users import User, UserManager, build_user_db
from app.main import app

_STARTUP_TIMEOUT_S = 10.0
_TEST_DB_NAME = "papertrail_test"


def _run[T](coro: Coroutine[object, object, T]) -> T:
    """Run a coroutine to completion in a throwaway thread with its own loop.

    Playwright's synchronous API keeps an event loop running in the main thread,
    so a plain ``asyncio.run`` from an e2e fixture would raise "another loop is
    running". Executing it in a separate thread sidesteps that entirely, and the
    NullPool test engine means no connection is shared across loops.
    """
    box: list[T] = []

    def _runner() -> None:
        box.append(asyncio.run(coro))

    thread = threading.Thread(target=_runner)
    thread.start()
    thread.join()
    return box[0]


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Run Playwright (browser) tests last.

    pytest-playwright's sync API and pytest-asyncio don't coexist within a run:
    once the browser loop is live, pytest-asyncio can no longer drive an async
    test. Ordering all ``page``-using tests after the async ones keeps them apart.
    """
    items.sort(key=lambda item: "page" in getattr(item, "fixturenames", []))


# A NullPool engine never caches connections, so it can be used safely from any
# event loop (per-test loop, the live-server thread's loop, or a throwaway
# asyncio.run loop) without asyncpg's "attached to a different loop" errors.
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


async def create_verified_user(email: str, password: str) -> None:
    """Create an active, already-verified user directly in the test database."""
    async with _test_session_maker() as session:
        manager = UserManager(build_user_db(session), CapturingEmailSender())
        user = cast(
            "User",
            await manager.create(UserCreate(email=email, password=password), safe=True),
        )
        user.is_verified = True
        session.add(user)
        await session.commit()


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


# --------------------------------------------------------------------------- #
# Live server + seeded user (Playwright e2e). Sync fixtures (asyncio.run) so they
# compose cleanly with the synchronous Playwright API.
# --------------------------------------------------------------------------- #
def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def live_server() -> Iterator[str]:
    """Run the FastAPI app on a real port in a thread; yield its base URL.

    uvicorn's ``capture_signals`` already no-ops off the main thread, so the
    server runs safely in this background thread with no extra plumbing.
    """
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + _STARTUP_TIMEOUT_S
        while not server.started:
            if time.monotonic() > deadline:
                msg = "uvicorn server did not start in time"
                raise RuntimeError(msg)
            time.sleep(0.05)
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=_STARTUP_TIMEOUT_S)


@pytest.fixture
def verified_credentials() -> Iterator[tuple[str, str]]:
    """Seed a verified user (committed) for browser login tests; clean up after."""
    email = "e2e-user@example.com"
    password = "e2e-password-123"
    _run(create_verified_user(email, password))
    try:
        yield email, password
    finally:
        _run(_truncate_users())
