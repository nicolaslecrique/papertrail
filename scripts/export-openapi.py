"""Export the FastAPI OpenAPI schema to ``openapi.json`` at the repo root.

The frontend's typed API client is generated from this committed file, offline and
deterministically (``frontend/openapi-ts.config.ts`` reads it). ``check.sh``
regenerates this file and the client and fails if either drifts from the backend,
so the committed schema always matches the routes and Pydantic models.
"""

import json
from pathlib import Path

from app.main import app

_OUTPUT = Path(__file__).resolve().parent.parent / "openapi.json"


def main() -> None:
    """Write the app's OpenAPI schema to ``openapi.json`` (pretty, trailing newline)."""
    schema = app.openapi()
    _OUTPUT.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
