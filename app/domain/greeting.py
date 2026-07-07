"""Greeting business rules — pure functions, no I/O or framework types."""

DEFAULT_NAME = "world"


def normalize_name(name: str) -> str:
    """Trim a submitted name, falling back to the default when it is blank."""
    return name.strip() or DEFAULT_NAME
