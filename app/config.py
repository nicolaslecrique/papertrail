"""Application configuration, loaded once from the environment.

A shared kernel module that is deliberately *not* part of the web/domain/db
layer stack: any layer may import it. It depends only on pydantic, so it can
never drag a web framework (or SQLAlchemy) into the lower layers. Values come
from environment variables.

``database_url`` has no default — a value must be supplied by whoever boots the
app, instead of one context's value silently standing in for every other. In the
devcontainer that's ``.env.dev`` (loaded via ``.devcontainer/docker-compose.yml``);
tests and e2e set their own via ``os.environ``/the Playwright config. See
docs/coding-guidelines.md.

Access the settings through :func:`get_settings` (cached, so the environment is
read once) rather than a module-level singleton — this lets the web layer inject
it as a FastAPI dependency and lets tests override it.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings, read from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database. No default - genuinely differs per environment (see .env.dev).
    database_url: str

    @property
    def async_database_url(self) -> str:
        """``database_url`` rewritten to use the asyncpg driver.

        Kept as plain string handling (no ``sqlalchemy.make_url``) on purpose: this
        module stays pydantic-only so importing it into the domain never drags
        SQLAlchemy into the pure layers.
        """
        prefix = "postgresql://"
        if self.database_url.startswith(prefix):
            return "postgresql+asyncpg://" + self.database_url[len(prefix) :]
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, read once from the environment."""
    return Settings()
