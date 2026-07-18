"""Async SQLAlchemy engine, session factory, and declarative base.

The lowest layer: it owns the Postgres connection and nothing else. No web
framework is imported here (import-linter enforces this).

The engine and session factory are built lazily (on first use) rather than at
import, so importing the app never reads settings or opens a connection pool —
which keeps the composition root and the tests free of import-ordering traps.
"""

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


@lru_cache
def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, built once from settings."""
    return create_async_engine(get_settings().async_database_url)


@lru_cache
def _session_maker() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory bound to :func:`get_engine`."""
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session scoped to a single unit of work."""
    async with _session_maker()() as session:
        yield session


async def dispose_engine() -> None:
    """Dispose of the engine's connection pool (called on app shutdown)."""
    await get_engine().dispose()
