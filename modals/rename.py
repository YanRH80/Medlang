"""Modal screen that asks the user for a new filename.

Scope
-----
Tiny modal used by the `:rename` command. Returns the new bare filename,
or `None` if the user cancels.

Boundaries
----------
- Does NOT touch the filesystem. The caller passes the result to
  `editor_storage.rename`.
- Does NOT validate the name beyond accepting any non-empty string. Disk
  validation lives in `editor_storage` so the rules are in one place.

Freeze criteria
---------------
- `Enter` on a non-empty input dismisses with the typed value.
- `Escape` cancels with `None`.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static


class RenamePromptScreen(ModalScreen[str | None]):
    """Modal asking for a new filename."""

    CSS = """
    RenamePromptScreen {
        align: center middle;
        background: #0f172a 80%;
    }

    #rename-dialog {
        width: 60;
        height: auto;
        padding: 1 2;
        border: round #6366f1;
        background: #0f172a;
        color: #e2e8f0;
    }

    #rename-input {
        margin: 1 0;
        border: round #334155;
        background: #1e293b;
        color: #f1f5f9;
    }

    #rename-input:focus {
        border: round #6366f1;
    }

    .rename-title {
        text-style: bold;
        color: #fbbf24;
    }

    .rename-hint {
        color: #64748b;
    }
    """

    BINDINGS = [("escape", "dismiss", "Cancel")]

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
