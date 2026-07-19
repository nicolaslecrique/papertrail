"""Domain layer: pure Python business logic.

Sits between the web and db layers: the web layer calls the domain, and the
domain calls the db layer for persistence. It must not import a web framework
(FastAPI/Starlette) nor touch SQLAlchemy directly — persistence goes
through ``app.db``. These rules are enforced by the import-linter contracts in
``pyproject.toml``, which keep the logic trivial to unit-test in isolation.
"""
