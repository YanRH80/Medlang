"""Modal screen for setting a hotkey binding.

Scope
-----
Owns the modal UI for assigning a key combo to an existing action.
User types "<action> <key-combo>" (e.g. "pane-files-toggle ctrl+b").
Validates action exists and key combo is well-formed before returning.

Boundaries
----------
- Does NOT write to config. Caller (`SimpleTextEditorApp._cmd_hotkey_set`)
  receives the parsed (action, key_combo) and handles saving.
- Does NOT know about the app's binding list. Validation is by checking
  the parsed action name is non-empty and key combo matches the format.

Freeze criteria
--------------
- Enter submits the parsed (action, key_combo) if valid.
- Escape cancels with None.
- Invalid input shows inline error, does not dismiss.
"""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from editor_commands import CommandRegistry


class HotkeySetScreen(ModalScreen[tuple[str, str] | None]):
    CSS = """
    HotkeySetScreen {
        align: center middle;
        background: $panel 80%;
    }

    #dialog {
        width: 70%;
        max-width: 70;
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

    #hk-input {
        margin-bottom: 1;
    }

    .error {
        color: $error;
    }
    """

    BINDINGS = [("escape", "dismiss", "Dismiss")]

    def __init__(self, registry: CommandRegistry | None = None) -> None:
        super().__init__()
        self._registry = registry

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("Set hotkey", classes="title")
            yield Static(
                "Format: <action> <key-combo>\n"
                "Example: pane-files-toggle ctrl+b  |  super+h",
                classes="hint",
            )
            yield Input(placeholder="action key-combo", id="hk-input")
            yield Static("", id="hk-error", classes="error")

    def on_mount(self) -> None:
        self.query_one("#hk-input", Input).focus()

    def _parse(self, raw: str) -> tuple[str, str] | str:
        parts = raw.strip().split()
        if len(parts) < 2:
            return "format: <action> <key-combo>"
        action = parts[0]
        key_combo = parts[1]
        if not action:
            return "action cannot be empty"
        # Basic key combo validation
        import re
        key_pattern = re.compile(r"^(ctrl|shift|alt|super)\+[a-z0-9]$|^(ctrl\+){1,2}(shift|alt)\+[a-z0-9]$|^[a-z0-9]$")
        if not re.match(r"^(ctrl|shift|alt|super)?(\+[a-z0-9])+$", key_combo):
            return f"invalid key combo: {key_combo!r}"
        return (action, key_combo)

    @on(Input.Submitted, "#hk-input")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        error = self.query_one("#hk-error", Static)
        parsed = self._parse(event.value)
        if isinstance(parsed, str):
            error.update(parsed)
            return
        self.dismiss(parsed)

    @on(Input.Changed, "#hk-input")
    def on_input_changed(self, event: Input.Changed) -> None:
        self.query_one("#hk-error", Static).update("")