"""Unit tests for the pure-Python domain layer."""

from app.domain.greeting import DEFAULT_NAME, normalize_name


def test_normalize_name_trims_surrounding_whitespace() -> None:
    assert normalize_name("  Ada  ") == "Ada"


def test_normalize_name_keeps_a_regular_name() -> None:
    assert normalize_name("Ada") == "Ada"


def test_normalize_name_defaults_when_blank() -> None:
    assert normalize_name("   ") == DEFAULT_NAME


def test_normalize_name_defaults_when_empty() -> None:
    assert normalize_name("") == DEFAULT_NAME
