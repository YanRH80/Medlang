"""Modal screen that asks the user for a new filename.

Scope
-----
Tiny modal used by the `:rename` command. Returns the new bare filename,
or `None` if the user cancels.

Boundaries
----------
- Does NOT touch the filesystem. The caller passes the result to
  `storage.rename`.
- Does NOT validate the name beyond accepting any non-empty string. Disk
  validation lives in `storage` so the rules are in one place.

Freeze criteria
---------------
- `Enter` on a non-empty input dismisses with the typed value.
- `Escape` cancels with `None`.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Static

from modals._base import BaseModalScreen


class RenamePromptScreen(BaseModalScreen[str | None]):
    """Modal asking for a new filename."""

    CSS = """
    RenamePromptScreen {
        align: center middle;
        background: $panel 80%;
    }

    #rename-dialog {
        width: 60;
        height: auto;
        padding: 1 2;
        border: round $primary;
        background: $surface;
        color: $foreground;
    }

    #rename-input {
        margin: 1 0;
        border: round $panel;
        background: $surface;
        color: $foreground;
    }

    #rename-input:focus {
        border: round $primary;
    }

    .rename-title {
        text-style: bold;
        color: $accent;
    }

    .rename-hint {
        color: $foreground;
        text-style: dim;
    }
    """

    def __init__(self, current_name: str) -> None:
        super().__init__()
        self._current_name = current_name

    def compose(self) -> ComposeResult:
        with Vertical(id="rename-dialog"):
            yield Static(" Rename document", classes="rename-title")
            yield Input(
                value=self._current_name,
                placeholder="new-name.json",
                id="rename-input",
            )
            yield Static("Enter to confirm   Esc to cancel", classes="rename-hint")

    def on_mount(self) -> None:
        input_widget = self.query_one("#rename-input", Input)
        input_widget.focus()
        # Pre-select the existing text by placing the cursor at the end.
        input_widget.cursor_position = len(input_widget.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "rename-input":
            return
        value = event.value.strip()
        if not value:
            self.dismiss(None)
            return
        self.dismiss(value)
