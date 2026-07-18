"""Composition root: build the FastAPI app and wire the layers together.

This module sits at the top of the dependency stack. It assembles the pieces (the
JSON API routes and the database lifecycle) but holds no business logic itself. The
app is a pure REST API — the user-facing UI is a separate React/TanStack Start
frontend that consumes these ``/api`` endpoints (see docs/frontend.md).
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.db.engine import engine
from app.web.api import router


def _operation_id(route: APIRoute) -> str:
    """Use each route's name as its OpenAPI ``operationId``.

    FastAPI's default appends the HTTP method and full path, which produces
    unwieldy generated client names (``registerApiAuthRegisterPost``). The route
    names are already unique here, so the bare name yields clean SDK symbols
    (``register``, ``usersCurrentUser``, ...) for @hey-api/openapi-ts.
    """
    return route.name


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


app = FastAPI(
    title="papertrail",
    lifespan=lifespan,
    generate_unique_id_function=_operation_id,
)
app.include_router(router)
