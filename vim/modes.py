"""Vim mode finite-state machine.

Scope
-----
Owns the `VimMode` enum and the canonical state-transition functions
that mutate the app's mode + selection. All mode changes funnel through
`enter_normal`, `enter_insert`, `enter_visual` here, so we don't have
duplicated bookkeeping in `app.py` and `vim/keybindings.py`.

Boundaries
----------
- Pure state transitions over `app` and `editor`. No UI rendering.
- No keyboard input. Callers (keybindings, command handlers) decide
  *when* to transition; this module decides *what* to update.

Freeze criteria
---------------
- `enter_normal` resets selection, prefix, anchor.
- `enter_insert` clears prefix and anchor.
- `enter_visual` records the anchor and seeds the selection.
- Each transition refreshes status and panel borders.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from textual.widgets.text_area import Selection


class VimMode(StrEnum):
    """Editor modes exposed to the user."""

    INSERT = "insert"
    NORMAL = "normal"
    VISUAL = "visual"
    VISUAL_LINE = "visual_line"


def enter_normal(app: Any) -> None:
    """Transition to NORMAL mode. Idempotent."""

    editor = app._editor()
    editor.selection = Selection.cursor(editor.cursor_location)
    app.visual_anchor = None
    app.vim_prefix = ""
    app.vim_mode = VimMode.NORMAL
    app.refresh_status()
    app._update_panel_borders()


def enter_insert(app: Any) -> None:
    """Transition to INSERT mode. Idempotent."""

    app.visual_anchor = None
    app.vim_prefix = ""
    app.vim_mode = VimMode.INSERT
    app.refresh_status()
    app._update_panel_borders()


def enter_visual(app: Any, *, linewise: bool = False) -> None:
    """Transition to VISUAL or VISUAL_LINE mode."""

    editor = app._editor()
    app.visual_anchor = editor.cursor_location
    app.vim_prefix = ""
    app.vim_mode = VimMode.VISUAL_LINE if linewise else VimMode.VISUAL
    if linewise:
        row, _ = editor.cursor_location
        editor.selection = Selection((row, 0), (row, len(editor.document[row])))
    else:
        editor.selection = Selection.cursor(editor.cursor_location)
    app.refresh_status()
    app._update_panel_borders()
