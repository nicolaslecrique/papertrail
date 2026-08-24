"""Integration test for the database plumbing.

The app has no tables yet, so there is nothing domain-specific to assert. This
keeps the whole chain honest end to end anyway — settings → async engine →
session, plus the migration runner that the ``_prepare_database`` fixture calls —
so the plumbing is known-good on the day the first model lands.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def test_session_reaches_the_migrated_database(session: AsyncSession) -> None:
    assert await session.scalar(text("SELECT 1")) == 1
