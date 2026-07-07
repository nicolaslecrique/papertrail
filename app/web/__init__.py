"""Web layer: FastAPI routes, htmx endpoints, and Jinja templates.

This layer is presentation only: it parses requests, delegates to the domain
layer, and renders templates. It must contain no business logic. It sits at the
top of the dependency stack and may import the domain layer, but never the db
layer directly (persistence goes domain → db); nothing imports it back.
"""
