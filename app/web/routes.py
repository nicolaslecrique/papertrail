"""HTTP layer: FastAPI routes rendering htmx/Jinja fragments.

Presentation only — parse the request, delegate to the domain layer, render a
template. No business logic lives here.
"""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import StrictUndefined

from app.domain.greeting import normalize_name

_WEB_DIR = Path(__file__).parent

templates = Jinja2Templates(directory=_WEB_DIR / "templates")
# Fail loudly on a typo'd or missing template variable instead of silently
# rendering a blank; a missing partial still raises TemplateNotFound.
templates.env.undefined = StrictUndefined

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    """Render the full Hello World page."""
    return templates.TemplateResponse(request, "index.html")


@router.post("/greet", response_class=HTMLResponse)
def greet(request: Request, name: Annotated[str, Form()] = "") -> HTMLResponse:
    """Return only the greeting fragment, for htmx to swap into the page."""
    return templates.TemplateResponse(
        request,
        "partials/greeting.html",
        {"name": normalize_name(name)},
    )
