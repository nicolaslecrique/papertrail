"""Application configuration, loaded once from the environment.

A shared kernel module that is deliberately *not* part of the web/domain/db
layer stack: any layer may import it. It depends only on pydantic, so it can
never drag a web framework (or SQLAlchemy) into the lower layers. Values come
from environment variables (the devcontainer sets ``DATABASE_URL``); every field
has a development-friendly default so the app also boots with a bare environment.

Access the settings through :func:`get_settings` (cached, so the environment is
read once) rather than a module-level singleton — this lets the web layer inject
it as a FastAPI dependency and lets tests override it.
"""

from functools import lru_cache
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The obvious placeholder for the JWT signing secret. Kept as a named constant so
# the production guard below can refuse it. It must never sign real tokens.
PLACEHOLDER_AUTH_SECRET = "dev-only-not-a-real-secret-change-me"  # noqa: S105


class Settings(BaseSettings):
    """Typed application settings, read from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # "dev" (the default) relaxes the production guard below so the devcontainer,
    # tests, and local runs boot with the placeholder secret. Set ENVIRONMENT=prod
    # in any real deployment to turn the guard on.
    environment: Literal["dev", "prod"] = "dev"

    # Database. The devcontainer exports DATABASE_URL; asyncpg driver is derived.
    database_url: str = "postgresql://papertrail:papertrail@db:5432/papertrail"

    # Token signing secret. MUST be overridden (AUTH_SECRET) in any real
    # deployment; the production guard refuses the placeholder so a misconfigured
    # prod fails fast instead of signing forgeable JWTs with a public secret.
    auth_secret: str = PLACEHOLDER_AUTH_SECRET
    access_token_lifetime_seconds: int = 60 * 60 * 24  # 1 day

    # Cookie transport. cookie_secure MUST be True in production (HTTPS only); the
    # production guard enforces it, and SameSite=None always requires Secure.
    cookie_name: str = "papertrailauth"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # Public base URL used to build the verification / reset links in emails. These
    # links are opened in the browser, so this points at the *frontend* origin (the
    # TanStack Start server), whose /verify and /reset-password routes call the API.
    base_url: str = "http://localhost:3000"

    # Breach check at sign-up. When True, the chosen password is checked against
    # Have I Been Pwned's k-Anonymity range API and rejected if it appears in a
    # known breach. Disable (PWNED_CHECK_ENABLED=false) for offline dev / tests.
    pwned_check_enabled: bool = True

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
        """``database_url`` rewritten to use the asyncpg driver.

        Kept as plain string handling (no ``sqlalchemy.make_url``) on purpose: this
        module stays pydantic-only so importing it into the domain never drags
        SQLAlchemy into the pure layers.
        """
        prefix = "postgresql://"
        if self.database_url.startswith(prefix):
            return "postgresql+asyncpg://" + self.database_url[len(prefix) :]
        return self.database_url

    @model_validator(mode="after")
    def _check_secure_configuration(self) -> Self:
        """Reject browser-invalid and unsafe-for-production configurations.

        ``SameSite=None`` is invalid without ``Secure`` in every modern browser, so
        it is refused regardless of environment. In ``prod`` the placeholder auth
        secret and a non-secure cookie are refused too, so a deployment that forgot
        to set ``AUTH_SECRET`` / ``COOKIE_SECURE`` fails to boot instead of running
        with forgeable sessions.
        """
        if self.cookie_samesite == "none" and not self.cookie_secure:
            msg = "cookie_samesite='none' requires cookie_secure=True."
            raise ValueError(msg)
        if self.environment == "prod":
            if self.auth_secret == PLACEHOLDER_AUTH_SECRET:
                msg = "AUTH_SECRET must be overridden in production."
                raise ValueError(msg)
            if not self.cookie_secure:
                msg = "COOKIE_SECURE must be True in production."
                raise ValueError(msg)
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, read once from the environment."""
    return Settings()
