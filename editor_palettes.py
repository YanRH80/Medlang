"""Modal screen for picking a color palette.

Scope
-----
Owns the modal that lets the user choose one of the predefined color
palettes shipped in `editor_styles.PALETTES`. Returns the palette name (or
`None` if cancelled). Filtering is fuzzy by both palette `name` and human
`label`.

Boundaries
----------
- Does NOT apply the palette. The caller (`SimpleTextEditorApp`) calls
  `apply_palette` once a name is chosen.
- Does NOT define palettes. New palettes are added in `editor_styles`.
- Owns its own CSS so the picker layout stays decoupled from the rest of
  the app.

Freeze criteria
---------------
This module can be considered frozen once:
- `Enter` picks the top fuzzy match.
- Selecting an option in the list dismisses with that name.
- `Escape` cancels with `None`.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from editor_styles import PALETTES

@dataclass(frozen=True)
class PaletteOption:
    """Palette option shown inside the picker modal."""

    name: str
    label: str

def _palette_options() -> list[PaletteOption]:
    return [PaletteOption(palette.name, palette.label) for palette in PALETTES]

def fuzzyfind_palettes(query: str, limit: int = 8) -> list[PaletteOption]:
    """Return palette options ranked by fuzzy similarity."""

    normalized_query = query.strip().lower()
    options = _palette_options()
    if not normalized_query:
        return options[:limit]

    scored: list[tuple[float, PaletteOption]] = []
    for option in options:
        normalized_name = option.name.lower()
        normalized_label = option.label.lower()
        score = SequenceMatcher(None, normalized_query, normalized_name).ratio()
        score += SequenceMatcher(None, normalized_query, normalized_label).ratio() * 0.25
        if normalized_name.startswith(normalized_query) or normalized_label.startswith(normalized_query):
            score += 0.35
        if normalized_query in normalized_name or normalized_query in normalized_label:
            score += 0.2
        scored.append((score, option))
    scored.sort(key=lambda item: (-item[0], item[1].label))
    return [option for score, option in scored if score > 0][:limit]

class PalettePickerScreen(ModalScreen[str | None]):
    """Modal color-palette selector with fuzzy filtering.

    This is intentionally standard Textual UI: a modal, an input for filtering,
    and an option list for keyboard selection.
    """

    CSS = """
    PalettePickerScreen {
        align: center middle;
        background: #0f172a 80%;
    }

    #dialog {
        width: 80%;
        height: 80%;
        padding: 1 2;
        border: round #64748b;
        background: #0f172a;
        color: #e2e8f0;
    }

    #palette-query {
        margin: 0 0 1 0;
    }

    #palette-list {
        height: 1fr;
    }

    .title {
        text-style: bold;
        margin-bottom: 1;
        color: #fbbf24;
    }

    .subtitle {
        color: #94a3b8;
        margin-bottom: 1;
    }
    """

    BINDINGS = [("escape", "dismiss", "Dismiss")]

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("Choose a color palette", classes="title")
            yield Static("Type to filter, then press Enter or select an option.", classes="subtitle")
            yield Input(placeholder="Filter palettes...", id="palette-query")
            yield OptionList(id="palette-list")

    def on_mount(self) -> None:
        self.query_one("#palette-query", Input).focus()
        self._render_options("")

    def _render_options(self, query: str) -> None:
        option_list = self.query_one("#palette-list", OptionList)
        option_list.clear_options()
        option_list.add_options([Option(f"{option.label}  [{option.name}]", id=option.name) for option in fuzzyfind_palettes(query)])

    @on(Input.Changed, "#palette-query")
    def on_query_changed(self, event: Input.Changed) -> None:
        self._render_options(event.value)

    @on(Input.Submitted, "#palette-query")
    def on_query_submitted(self, event: Input.Submitted) -> None:
        matches = fuzzyfind_palettes(event.value)
        if matches:
            self.dismiss(matches[0].name)

    @on(OptionList.OptionSelected, "#palette-list")
    def on_palette_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(str(event.option.id) if event.option.id is not None else None)