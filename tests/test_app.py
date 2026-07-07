"""Unit tests for the FastAPI routes using Starlette's TestClient."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_index_serves_hello_page() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Hello World" in response.text
    assert "/static/app.css" in response.text
    assert "/static/htmx.min.js" in response.text


def test_greet_returns_greeting_fragment() -> None:
    response = client.post("/greet", data={"name": "Ada"})
    assert response.status_code == 200
    assert "Hello, Ada!" in response.text
    # A fragment for htmx to swap in, not a full document.
    assert "<html" not in response.text.lower()


def test_greet_defaults_to_world_when_blank() -> None:
    response = client.post("/greet", data={"name": "   "})
    assert response.status_code == 200
    assert "Hello, world!" in response.text
