"""HTTP layer: the JSON REST API.

Presentation only — this module translates HTTP requests into calls on the domain
layer and returns JSON. No business logic lives here; the rules live in
``app.domain``.
"""

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.domain.greeting import normalize_name


class MessageResponse(BaseModel):
    """A simple ``{"message": ...}`` envelope for endpoints without a resource body."""

    message: str


router = APIRouter(prefix="/api")


@router.get("/greeting", tags=["greeting"])
async def greeting(name: Annotated[str, Query()] = "") -> MessageResponse:
    """Return a greeting for ``name``, falling back to a default when blank."""
    return MessageResponse(message=f"Hello, {normalize_name(name)}!")
