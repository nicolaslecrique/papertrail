"""Application configuration, loaded once from the environment.

A shared kernel module that is deliberately *not* part of the web/domain/db
layer stack: any layer may import it. It depends only on pydantic, so it can
never drag a web framework into the lower layers. Values come from environment
variables (the devcontainer sets ``DATABASE_URL``); every field has a
development-friendly default so the app also boots with a bare environment.
"""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings, read from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database. The devcontainer exports DATABASE_URL; asyncpg driver is derived.
    database_url: str = "postgresql://papertrail:papertrail@db:5432/papertrail"

    # Token signing secret. MUST be overridden (AUTH_SECRET) in any real
    # deployment; this obvious placeholder keeps secrets out of version control.
    auth_secret: str = "dev-only-not-a-real-secret-change-me"  # noqa: S105
    access_token_lifetime_seconds: int = 60 * 60 * 24  # 1 day

    # Cookie transport. cookie_secure MUST be True in production (HTTPS only).
    cookie_name: str = "papertrailauth"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # Public base URL used to build the verification / reset links in emails.
    base_url: str = "http://localhost:8000"

    # Email delivery. "console" logs the link (dev/test); "smtp" sends for real.
    email_backend: Literal["console", "smtp"] = "console"
    email_from: str = "no-reply@papertrail.local"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_start_tls: bool = False

    @property
    def async_database_url(self) -> str:
        """``database_url`` rewritten to use the asyncpg driver."""
        prefix = "postgresql://"
        if self.database_url.startswith(prefix):
            return "postgresql+asyncpg://" + self.database_url[len(prefix) :]
        return self.database_url


settings = Settings()
