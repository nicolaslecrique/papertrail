"""Prepare the database: create it if missing and run the Alembic migrations.

Used by the test fixtures and the e2e seeder so their schema is built by the real
migrations (exercising them on every run) rather than by ``metadata.create_all`` -
which keeps the migrations honest and the test/dev schema identical to production.

The connection URL is resolved inside ``migrations/env.py`` from application
settings (i.e. ``DATABASE_URL``); ``upgrade_to_head`` only locates ``alembic.ini``.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

# The maintenance database that always exists on the server, used to create the
# target database (a database can't be created from a connection to itself).
_MAINTENANCE_DATABASE = "papertrail"

_ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


async def ensure_database_exists(async_database_url: str) -> None:
    """Create the database named in ``async_database_url`` if it doesn't exist.

    Connects to the server's ``papertrail`` maintenance database with AUTOCOMMIT
    (``CREATE DATABASE`` cannot run inside a transaction). Shared by the pytest
    fixtures and the e2e seeder, which each point at a ``papertrail_test`` database.
    """
    admin_base, _, db_name = async_database_url.rpartition("/")
    admin_engine = create_async_engine(
        f"{admin_base}/{_MAINTENANCE_DATABASE}",
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    try:
        async with admin_engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            )
            if not exists:
                # A database name can't be a bound parameter, so it must be
                # interpolated; db_name comes from our own settings, not user input.
                await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        await admin_engine.dispose()


def upgrade_to_head() -> None:
    """Apply all pending migrations (equivalent to ``alembic upgrade head``).

    Must be called from a synchronous context with no running event loop: the
    async ``env.py`` drives the migration with its own ``asyncio.run``.
    """
    config = Config(str(_ALEMBIC_INI))
    # Stop env.py's fileConfig() from reconfiguring (and, by default, disabling)
    # the app's already-registered loggers when we migrate in-process. The CLI
    # (`alembic upgrade head`) leaves this unset, so it still configures logging.
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")
