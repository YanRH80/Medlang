"""Modal command palette with fuzzy filter, ghost-text autocomplete, arrow-key bridge.

Scope
-----
Owns the modal UI used by `:` and `Ctrl+P`. Lists every registered command,
filters as the user types, suggests inline ghost-text completion, lets the
user bridge from the input into the option list with arrow keys, and
returns the chosen command name (or `None` on cancel).

Boundaries
----------
- Does NOT execute commands. The caller runs the chosen name through
  `CommandRegistry.execute`.
- Does NOT know about specific commands or their side effects.
- Owns its CSS so the picker layout stays decoupled from the rest of the
  app.

Freeze criteria
---------------
- Typing in the input filters the option list in real time.
- Ghost-text completion appears for prefix matches; `→` accepts it.
- `↓` from the input focuses the option list; `↑` from the first option
  goes back to the input.
- `Enter` from the input dismisses with the top fuzzy match.
- `Enter` on an option in the list dismisses with that option.
- `Esc` cancels with `None`.
"""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.suggester import SuggestFromList
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from editor_commands import CommandRegistry


class CommandPaletteScreen(ModalScreen[str | None]):
    """Modal command picker. Returns the chosen command name or None."""

    CSS = """
    CommandPaletteScreen {
        align: center middle;
        background: $panel 80%;
    }

    #dialog {
        width: 70%;
        max-width: 90;
        height: 70%;
        max-height: 25;
        padding: 1 2;
        border: round $primary;
        background: $surface;
        color: $foreground;
    }

    #command-query {
        margin: 0 0 1 0;
        border: round $primary;
        background: $surface;
        color: $foreground;
    }

    #command-query:focus {
        border: round $primary;
    }

    #command-list {
        height: 1fr;
        background: $surface;
        border: none;
        padding: 0;
    }

    #command-list > .option-list--option-highlighted {
        background: $accent;
        color: $foreground;
        text-style: bold;
    }

    .palette-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .palette-hint {
        color: $foreground;
        text-style: dim;
        margin-top: 1;
    }
    """

    BINDINGS = [("escape", "dismiss", "Cancel")]

    def __init__(self, registry: CommandRegistry) -> None:
        super().__init__()
        self._registry = registry
        names = registry.command_names()
        self._suggester = SuggestFromList(names, case_sensitive=False)

    # ----- compose ---------------------------------------------------------

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(" Command palette", classes="palette-title")
            yield Input(
                placeholder="Type a command...",
                id="command-query",
                suggester=self._suggester,
            )
            yield OptionList(id="command-list")
            yield Static(
                "↓↑ navigate   → accept ghost   Enter run   Esc cancel",
                classes="palette-hint",
            )

    def on_mount(self) -> None:
        self.query_one("#command-query", Input).focus()
        self._render_options("")

    # ----- rendering -------------------------------------------------------

    def _render_options(self, query: str) -> None:
        option_list = self.query_one("#command-list", OptionList)
        option_list.clear_options()
        names = self._registry.fuzzy_find(query, limit=20)
        if not names:
            option_list.add_option(Option("(no matches)", id=None, disabled=True))
            return
        for name in names:
            description = self._registry.description(name)
            option_list.add_option(Option(f"{name}  -  {description}", id=name))
        option_list.highlighted = 0

    # ----- input events (conventional handlers, not @on selectors) --------

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "command-query":
            return
        self._render_options(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "command-query":
            return
        matches = self._registry.fuzzy_find(event.value, limit=1)
        if matches:
            self.dismiss(matches[0])
        else:
            self.dismiss(None)

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        if event.option_list.id != "command-list":
            return
        option_id = event.option.id
        if option_id is None:
            return
        self.dismiss(str(option_id))

    # ----- arrow-key bridge between input and list ------------------------

    async def on_key(self, event: events.Key) -> None:
        list_widget = self.query_one("#command-list", OptionList)
        input_widget = self.query_one("#command-query", Input)
        focused = self.focused

        if event.key == "down" and focused is input_widget:
            if list_widget.option_count > 0:
                list_widget.focus()
                if list_widget.highlighted is None:
                    list_widget.highlighted = 0
                event.stop()
                event.prevent_default()
            return

        if event.key == "up" and focused is list_widget:
            if list_widget.highlighted in (None, 0):
                input_widget.focus()
                event.stop()
                event.prevent_default()
            return
