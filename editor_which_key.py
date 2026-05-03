"""WhichKey popup — LazyVim-style leader key hint overlay.

Scope
-----
Shows available `space+<key>` commands in a grid overlay.
Intercepts the next key press, dispatches via `app.leader_dispatch`,
and closes. Inspired by which-key.nvim (folke).

Boundaries
----------
- Does NOT execute commands directly — calls `app.leader_dispatch(key)`.
- Owns its CSS so layout stays decoupled.

Freeze criteria
---------------
- `space` key opens this screen from NORMAL mode.
- Next key press dispatches via `app.leader_dispatch` and closes.
- `escape` cancels and closes without dispatch.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static


COMMANDS: list[tuple[str, str]] = [
    ("n", "New document"),
    ("o", "Open document"),
    ("s", "Save"),
    ("d", "Delete document"),
    ("p", "Command palette"),
    ("b", "Toggle files"),
    ("h", "Focus files"),
    ("j", "Focus down"),
    ("k", "Focus up"),
    ("l", "Focus editor"),
    ("?", "Show hotkeys"),
]


class WhichKeyScreen(ModalScreen[str | None]):
    """Leader key hint popup. Returns the dispatched key or None on cancel."""

    CSS = """
    WhichKeyScreen {
        align: center middle;
        background: $panel 85%;
    }

    #wk-dialog {
        width: 50%;
        max-width: 60;
        padding: 1 2;
        border: round $primary;
        background: $surface;
        color: $foreground;
    }

    .wk-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .wk-row {
        height: 1;
    }

    .wk-key {
        width: 3;
        color: $primary;
        text-style: bold;
    }

    .wk-desc {
        color: $foreground;
    }

    .wk-hint {
        color: $foreground;
        text-style: dim;
        margin-top: 1;
    }
    """

    BINDINGS = [("escape", "dismiss", "Cancel")]

    def __init__(self, app: Any) -> None:
        super().__init__()
        self._app = app

    def compose(self) -> ComposeResult:
        with Vertical(id="wk-dialog"):
            yield Static(" Space — Commands", classes="wk-title")
            for key, desc in COMMANDS:
                with Horizontal(classes="wk-row"):
                    yield Static(f" {key}", classes="wk-key")
                    yield Static(desc, classes="wk-desc")
            yield Static(" esc cancel", classes="wk-hint")

    def on_key(self, event) -> None:
        key = event.key
        if key == "escape":
            self.dismiss(None)
            return
        for k, _ in COMMANDS:
            if key == k:
                self.dismiss(k)
                return
        self.dismiss(None)