"""Unit tests for application settings."""

import pytest
from pydantic import ValidationError

from app.config import PLACEHOLDER_AUTH_SECRET, Settings

REAL_SECRET = "a-real-production-secret-value-0123456789"


def test_async_database_url_rewrites_to_asyncpg() -> None:
    settings = Settings(database_url="postgresql://u:p@h:5432/db")
    assert settings.async_database_url == "postgresql+asyncpg://u:p@h:5432/db"


def test_async_database_url_passes_through_other_schemes() -> None:
    settings = Settings(database_url="sqlite+aiosqlite:///local.db")
    assert settings.async_database_url == "sqlite+aiosqlite:///local.db"


def test_samesite_none_requires_secure() -> None:
    # SameSite=None without Secure is rejected by every modern browser, so refuse
    # it regardless of environment.
    with pytest.raises(ValidationError, match="cookie_secure"):
        Settings(cookie_samesite="none", cookie_secure=False)


def test_samesite_none_allowed_with_secure() -> None:
    settings = Settings(cookie_samesite="none", cookie_secure=True)
    assert settings.cookie_samesite == "none"


def test_prod_refuses_placeholder_secret() -> None:
    with pytest.raises(ValidationError, match="AUTH_SECRET"):
        Settings(
            environment="prod",
            auth_secret=PLACEHOLDER_AUTH_SECRET,
            cookie_secure=True,
        )


def test_prod_refuses_insecure_cookie() -> None:
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        Settings(environment="prod", auth_secret=REAL_SECRET, cookie_secure=False)


def test_prod_accepts_a_secure_configuration() -> None:
    settings = Settings(environment="prod", auth_secret=REAL_SECRET, cookie_secure=True)
    assert settings.environment == "prod"


def test_dev_allows_the_placeholder_secret() -> None:
    # The devcontainer, tests, and local runs boot with the placeholder in dev.
    settings = Settings(auth_secret=PLACEHOLDER_AUTH_SECRET)
    assert settings.environment == "dev"
