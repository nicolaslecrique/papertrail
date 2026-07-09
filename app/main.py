"""Composition root: build the FastAPI app and wire the layers together.

This module sits at the top of the dependency stack. It assembles the pieces
(static files, routes, database lifecycle) but holds no business logic itself.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db.engine import engine
from app.web.routes import router

_STATIC_DIR = Path(__file__).parent / "web" / "static"


def _configure_logging() -> None:
    """Surface application logs at INFO on the console.

    uvicorn only configures its own loggers, so without this the app's INFO logs
    (notably the dev "console" email backend, which logs the verification and
    password-reset links) would be swallowed by the root logger's WARNING default.
    Records still propagate to the root logger so pytest's caplog keeps working.
    """
    app_logger = logging.getLogger("papertrail")
    app_logger.setLevel(logging.INFO)
    if not any(
        isinstance(handler, logging.StreamHandler) for handler in app_logger.handlers
    ):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
        app_logger.addHandler(handler)


_configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Dispose of the database engine's connection pool on shutdown."""
    yield
    await engine.dispose()


app = FastAPI(title="papertrail", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
app.include_router(router)
