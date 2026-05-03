"""Visual layer: CSS, color palettes, and status-bar styling.

Scope
-----
Holds the global CSS string applied to the app, the catalog of named color
palettes, and the helpers that apply a palette or toggle dark mode at
runtime.

Boundaries
----------
- Does NOT own UI structure. Widgets are composed in `app.py`.
- Does NOT pick a palette. The picker modal lives in `editor_palettes`.
- Does NOT know about Vim modes beyond a string flag used to toggle the
  status bar's visual state.

Freeze criteria
---------------
This module can be considered frozen once:
- Every palette renders with the editor, header and footer visible and
  readable. The status bar owns its own colors.
- `apply_color_palette` updates the running app without a restart.
- `toggle_light_dark_mode` flips the app theme and reports the new state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from textual.app import App


@dataclass(frozen=True)
class Palette:
    """Color values used by the editor.

    The palette values are applied directly to the current widgets so the UI can
    switch appearance without needing a separate CSS rebuild step.
    """

    name: str
    label: str
    screen_bg: str
    editor_bg: str
    editor_fg: str
    status_bg: str
    status_fg: str
    accent_bg: str
    accent_fg: str


PALETTES: tuple[Palette, ...] = (
    Palette("midnight", "Midnight", "#111827", "#f8fafc", "#111827", "#0b1120", "#cbd5e1", "#312e81", "#f8fafc"),
    Palette("paper", "Paper", "#f8fafc", "#fffdfa", "#111827", "#f1f5f9", "#334155", "#dbeafe", "#0f172a"),
    Palette("forest", "Forest", "#0f172a", "#f8fafc", "#102a17", "#123524", "#dcfce7", "#14532d", "#f8fafc"),
    Palette("sunset", "Sunset", "#1f2937", "#fff7ed", "#1f2937", "#431407", "#ffedd5", "#ea580c", "#fff7ed"),
    Palette("mono", "Mono", "#0f0f10", "#f5f5f5", "#111111", "#1f1f1f", "#e5e5e5", "#525252", "#fafafa"),
)


EDITOR_CSS = """
Screen {
    background: #111827;
    color: #e5e7eb;
}

#editor {
    height: 1fr;
    border: tall #334155;
    background: #f8fafc;
    color: #111827;
}

Header {
    background: #0b1120;
    color: #e5e7eb;
}

Footer {
    background: #0b1120;
    color: #e5e7eb;
}
"""


def get_palette(name: str) -> Palette:
    """Return a palette by name, falling back to the first palette.

    The fallback keeps the editor usable if the config references a palette that
    does not exist yet.
    """

    for palette in PALETTES:
        if palette.name == name:
            return palette
    return PALETTES[0]


def palette_names() -> list[str]:
    """Return the available palette names in display order."""

    return [palette.name for palette in PALETTES]


def apply_color_palette(app: App[Any], palette_name: str) -> Palette:
    """Apply a palette to the editor surface.

    Only the screen background and the editor's text colors are repainted.
    The status bar owns its own palette so the modeline stays readable on
    every theme.
    """

    palette = get_palette(palette_name)
    app.screen.styles.background = palette.screen_bg
    editor = app.query_one("#editor")
    editor.styles.background = palette.editor_bg
    editor.styles.color = palette.editor_fg
    return palette


def toggle_light_dark_mode(app: Any) -> str:
    """Toggle the application between light and dark modes.

    Returns a short status message so the caller can report what changed.
    """

    app.dark = not app.dark
    return "dark mode on" if app.dark else "light mode on"