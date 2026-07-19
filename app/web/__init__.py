"""Web layer: the FastAPI JSON REST API.

Presentation only: it parses requests, delegates to the domain layer, and returns
JSON. It contains no business logic and renders no HTML — the user-facing UI is a
separate React/TanStack Start frontend. It sits at the top of the dependency stack
and may import the domain layer, but never the db layer directly (persistence goes
domain → db); nothing imports it back.
"""
