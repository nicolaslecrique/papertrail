"""Shared pytest fixtures: a migrated test database and a session on it.

The app is pointed at a dedicated ``papertrail_test`` database (created on demand).
The env var is set *before* importing the app so the first (cached) settings read
picks it up rather than the devcontainer's dev database.
"""

import asyncio
import os
import threading
from collections.abc import AsyncIterator, Coroutine

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://papertrail:papertrail@db:5432/papertrail_test",
)

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.db.migrate import ensure_database_exists, upgrade_to_head


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
_test_engine = create_async_engine(
    get_settings().async_database_url, poolclass=NullPool
)
_test_session_maker = async_sessionmaker(_test_engine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def _prepare_database() -> None:
    """Create the test database and bring its schema up to head once per session.

    The schema is built by running the real Alembic migrations (not
    ``metadata.create_all``), so every test run exercises them. ``upgrade_to_head``
    is synchronous, so it runs outside the ``_run`` helper's event loop.
    """
    _run(ensure_database_exists(get_settings().async_database_url))
    upgrade_to_head()


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Yield a session on the migrated test database."""
    async with _test_session_maker() as db_session:
        yield db_session
