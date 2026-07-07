"""Database layer: the only place that talks to Postgres.

Isolates persistence (SQLAlchemy engine/session, models, repositories) from the
rest of the app. It is the lowest layer: the domain calls into it, but it must
not import the domain or web layers, nor any web framework — enforced by the
import-linter contracts in ``pyproject.toml``. Empty for now: the Hello World
slice has no database yet.
"""
