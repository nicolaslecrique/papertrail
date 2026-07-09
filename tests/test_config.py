"""Unit tests for application settings."""

from app.config import Settings


def test_async_database_url_rewrites_to_asyncpg() -> None:
    settings = Settings(database_url="postgresql://u:p@h:5432/db")
    assert settings.async_database_url == "postgresql+asyncpg://u:p@h:5432/db"


def test_async_database_url_passes_through_other_schemes() -> None:
    settings = Settings(database_url="sqlite+aiosqlite:///local.db")
    assert settings.async_database_url == "sqlite+aiosqlite:///local.db"
