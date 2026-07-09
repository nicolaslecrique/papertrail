"""ORM models. The user table schema is provided by fastapi-users."""

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID

from app.db.engine import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    """A registered user (id, email, hashed_password, is_active/superuser/verified)."""
