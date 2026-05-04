"""Theme system: wraps Textual's built-in theme API.

Scope
-----
Lists available themes, toggles dark/light, and provides a helper to
resolve a theme name from a short alias. All actual theming is handled
by Textual's first-class `App.theme` attribute — we just expose the
surface.

Boundaries
----------
- Does NOT implement custom themes. Textual ships 21 built-in themes.
- Does NOT mutate CSS directly. Theme switches go through `app.theme`.
- Does NOT own the theme picker UI. That lives in `modals.theme_picker`.

Freeze criteria
--------------
- `toggle_light_dark` flips between a known dark and known light theme.
- `list_themes` returns every theme Textual has registered on this app.
- `is_dark_theme` correctly categorises the 21 built-in themes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from textual.app import App


DARK_THEMES = frozenset({
    "textual-dark",
    "tokyo-night",
    "nord",
    "dracula",
    "gruvbox-dark",
    "catppuccin-mocha",
    "monokai",
    "flexoki-dark",
    "flexoki-light",
    "github-dark",
    "solarized-dark",
})

LIGHT_THEMES = frozenset({
    "textual-light",
    "solarized-light",
    "catppuccin-latte",
    "github-light",
    "flexoki-light",
    "flexoki-dark",
})


def is_dark_theme(theme: str) -> bool:
    return theme in DARK_THEMES


def toggle_light_dark(app: App) -> str:
    """Switch to the opposite theme family. Returns a status message."""
    current = app.theme or ""
    if is_dark_theme(current):
        app.theme = "textual-light"
        return "light theme"
    app.theme = "textual-dark"
    return "dark theme"


def list_themes(app: App) -> list[str]:
    """Return sorted list of every available theme on this app."""
    return sorted(app.available_themes)


def current_theme_name(app: App) -> str:
    return app.theme or "textual-dark"