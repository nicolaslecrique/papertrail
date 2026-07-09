"""Bridge the ORM user model to the fastapi-users persistence adapter.

Exposes a plain factory (no FastAPI ``Depends``) so that the dependency-
injection wiring can live in the web layer while the SQLAlchemy details stay
here in the db layer.
"""

import uuid

from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


def build_user_db(session: AsyncSession) -> SQLAlchemyUserDatabase[User, uuid.UUID]:
    """Wrap an async session in the fastapi-users SQLAlchemy adapter."""
    return SQLAlchemyUserDatabase(session, User)
