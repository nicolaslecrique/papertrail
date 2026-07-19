"""Database layer: the only place that talks to Postgres.

Isolates persistence — the async SQLAlchemy engine/session (``engine``), the ORM
models (``models``), the fastapi-users adapter (``users``), and the migration/
provisioning helpers (``migrate``) — from the rest of the app. It is the lowest
layer: the domain calls into it, but it must not import the domain or web layers,
nor any web framework — enforced by the import-linter contracts in ``pyproject.toml``.
"""
