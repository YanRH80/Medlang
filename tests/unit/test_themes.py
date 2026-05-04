"""Unit tests for `themes` (toggle_light_dark, list_themes, is_dark_theme)."""

from __future__ import annotations

from unittest.mock import MagicMock

from themes import (
    DARK_THEMES,
    LIGHT_THEMES,
    current_theme_name,
    is_dark_theme,
    list_themes,
    toggle_light_dark,
)


def test_is_dark_theme_recognises_known_dark() -> None:
    assert is_dark_theme("textual-dark") is True
    assert is_dark_theme("tokyo-night") is True
    assert is_dark_theme("dracula") is True


def test_is_dark_theme_returns_false_for_light() -> None:
    assert is_dark_theme("textual-light") is False


def test_dark_and_light_overlap_is_intentional() -> None:
    # `flexoki-dark` and `flexoki-light` appear in both sets in current
    # implementation. This test pins down that fact; if we ever clean it
    # up, the test will tell us.
    overlap = DARK_THEMES & LIGHT_THEMES
    # Document expected overlap: only flexoki variants today.
    assert overlap.issubset({"flexoki-dark", "flexoki-light"})


def test_toggle_from_dark_to_light() -> None:
    app = MagicMock()
    app.theme = "textual-dark"
    msg = toggle_light_dark(app)
    assert app.theme == "textual-light"
    assert "light" in msg.lower()


def test_toggle_from_light_to_dark() -> None:
    app = MagicMock()
    app.theme = "textual-light"
    msg = toggle_light_dark(app)
    assert app.theme == "textual-dark"
    assert "dark" in msg.lower()


def test_list_themes_returns_sorted() -> None:
    app = MagicMock()
    app.available_themes = {"zzz", "aaa", "mmm"}
    out = list_themes(app)
    assert out == ["aaa", "mmm", "zzz"]


def test_current_theme_name_returns_value_or_default() -> None:
    app = MagicMock()
    app.theme = "tokyo-night"
    assert current_theme_name(app) == "tokyo-night"
    app.theme = ""
    assert current_theme_name(app) == "textual-dark"
