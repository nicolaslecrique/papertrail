"""Composition root: build the FastAPI app and wire the web layer.

This module sits at the top of the dependency stack. It assembles the pieces
(static files, routes) but holds no business logic itself.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.web.routes import router

_STATIC_DIR = Path(__file__).parent / "web" / "static"

app = FastAPI(title="papertrail")
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
app.include_router(router)
