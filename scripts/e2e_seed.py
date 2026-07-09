"""Seed the e2e test database with one active, verified user.

Standalone operational script invoked by the TypeScript Playwright suite's global
setup (see ``e2e/support/global-setup.ts``). It reuses the application's own
``UserManager`` so the seeded password is hashed exactly as the real registration
flow would hash it, then flips ``is_verified`` so the login e2e test can sign in
without going through email confirmation.

The caller sets the environment *before* this module imports ``app`` (settings and
the engine are built at import time):

  DATABASE_URL / AUTH_SECRET / EMAIL_BACKEND   point the app at the test database
  E2E_USER_EMAIL / E2E_USER_PASSWORD           the credentials to seed
"""

import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.db.engine import Base
from app.domain.email import ConsoleEmailSender
from app.domain.schemas import UserCreate
from app.domain.users import UserManager, build_user_db

DEFAULT_EMAIL = "e2e-user@example.com"
DEFAULT_PASSWORD = "e2e-password-123"  # noqa: S105 - a fixed test-only credential


async def _ensure_database() -> None:
    """Create the test database if it does not exist yet."""
    admin_base, _, db_name = settings.async_database_url.rpartition("/")
    admin_engine = create_async_engine(
        f"{admin_base}/papertrail",
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    async with admin_engine.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": db_name},
        )
        if not exists:
            # A database name can't be a bound parameter, so it must be
            # interpolated; db_name comes from our own DATABASE_URL, not input.
            await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    await admin_engine.dispose()


async def _seed(email: str, password: str) -> None:
    """Create the schema, reset the user table, and insert one verified user."""
    engine = create_async_engine(settings.async_database_url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text('TRUNCATE TABLE "user" CASCADE'))
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        manager = UserManager(build_user_db(session), ConsoleEmailSender())
        user = await manager.create(
            UserCreate(email=email, password=password), safe=True
        )
        user.is_verified = True
        session.add(user)
        await session.commit()
    await engine.dispose()


async def main() -> None:
    """Ensure the test database exists, then seed the verified e2e user."""
    email = os.environ.get("E2E_USER_EMAIL", DEFAULT_EMAIL)
    password = os.environ.get("E2E_USER_PASSWORD", DEFAULT_PASSWORD)
    await _ensure_database()
    await _seed(email, password)


if __name__ == "__main__":
    asyncio.run(main())
