"""Modal screen for creating a new JSON document.

Scope
-----
Owns the modal UI that asks the user for a filename, then creates
an empty JSON document in the vault. The caller receives the chosen
name (or None on cancel).

Boundaries
----------
- Does NOT write to disk. The caller (`SimpleTextEditorApp._cmd_doc_new`)
  handles the actual file creation via `storage.save`.
- Does NOT know about the vault path. That is passed in via config.

Freeze criteria
--------------
- Enter submits the filename.
- Escape cancels with None.
- Empty filename is rejected (must enter a name).
"""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Static

from modals._base import BaseModalScreen


class NewDocScreen(BaseModalScreen[str | None]):
    CSS = """
    NewDocScreen {
        align: center middle;
        background: $panel 80%;
    }

    #dialog {
        width: 60%;
        max-width: 60;
        padding: 1 2;
        border: round $primary;
        background: $surface;
        color: $foreground;
    }

    .title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .hint {
        color: $foreground;
        text-style: dim;
        margin-bottom: 1;
    }

    #new-doc-input {
        margin-bottom: 1;
    }

    .error {
        color: $error;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("New document", classes="title")
            yield Static("Enter filename (e.g. notes.json):", classes="hint")
            yield Input(placeholder="filename.json", id="new-doc-input")
            yield Static("", id="new-doc-error", classes="error")

    def on_mount(self) -> None:
        self.query_one("#new-doc-input", Input).focus()

    @on(Input.Submitted, "#new-doc-input")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        name = event.value.strip()
        if not name:
            self.query_one("#new-doc-error", Static).update("filename required")
            return
        if "/" in name or "\\" in name or name in {".", ".."}:
            self.query_one("#new-doc-error", Static).update("invalid filename")
            return
        if not name.endswith(".json"):
            name = name + ".json"
        self.dismiss(name)

    @on(Input.Changed, "#new-doc-input")
    def on_input_changed(self, event: Input.Changed) -> None:
        self.query_one("#new-doc-error", Static).update("")