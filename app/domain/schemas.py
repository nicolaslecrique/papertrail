"""Pydantic schemas for user input/output, built on the fastapi-users bases."""

import uuid

from fastapi_users import schemas


class UserRead(schemas.BaseUser[uuid.UUID]):
    """User fields safe to expose to clients."""


class UserCreate(schemas.BaseUserCreate):
    """Payload accepted when registering a new user."""


class UserUpdate(schemas.BaseUserUpdate):
    """Payload accepted when updating an existing user."""
