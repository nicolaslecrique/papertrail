"""Run the Alembic migrations programmatically against the configured database.

Used by the test fixtures and the e2e seeder so their schema is built by the real
migrations (exercising them on every run) rather than by ``metadata.create_all`` -
which keeps the migrations honest and the test/dev schema identical to production.

The connection URL is resolved inside ``migrations/env.py`` from application
settings (i.e. ``DATABASE_URL``); this helper only locates ``alembic.ini``.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config

_ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


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
