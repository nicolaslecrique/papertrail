"""Unit tests for the JSON API's simple, database-free endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_greeting_returns_message() -> None:
    response = client.get("/api/greeting", params={"name": "Ada"})
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, Ada!"}


def test_greeting_defaults_to_world_when_blank() -> None:
    response = client.get("/api/greeting", params={"name": "   "})
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, world!"}


def test_openapi_schema_exposes_the_api() -> None:
    # The frontend's typed client is generated from this schema, so keep it
    # reachable and shaped the way the generator (and check.sh's drift guard)
    # expect: every /api route present under conventional paths.
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in ("/api/auth/login", "/api/auth/register", "/api/users/me"):
        assert path in paths
