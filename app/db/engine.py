"""Async SQLAlchemy engine, session factory, and declarative base.

The lowest layer: it owns the Postgres connection and nothing else. No web
framework is imported here (import-linter enforces this).
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.async_database_url)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session scoped to a single unit of work."""
    async with async_session_maker() as session:
        yield session
