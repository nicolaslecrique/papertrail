"""FastAPI Hello World service: htmx + Jinja2 + daisyUI, no database."""

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

_BASE_DIR = Path(__file__).parent

app = FastAPI(title="papertrail")
app.mount("/static", StaticFiles(directory=_BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=_BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    """Render the full Hello World page."""
    return templates.TemplateResponse(request, "index.html")


@app.post("/greet", response_class=HTMLResponse)
def greet(request: Request, name: Annotated[str, Form()] = "") -> HTMLResponse:
    """Return only the greeting fragment, for htmx to swap into the page."""
    cleaned = name.strip() or "world"
    return templates.TemplateResponse(
        request,
        "partials/greeting.html",
        {"name": cleaned},
    )
