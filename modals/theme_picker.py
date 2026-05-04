"""Modal screen for picking a Textual theme.

Scope
-----
Owns the modal that lets the user choose one of the themes available on
the running app (`app.available_themes`). Returns the theme name (or
`None` if cancelled). Filtering is fuzzy by theme name.

Boundaries
----------
- Does NOT apply the theme. The caller (`SimpleTextEditorApp`) sets
  `app.theme` once a name is chosen.
- Does NOT define themes. Textual ships 21 built-in; custom themes are
  registered via `app.theme` + `CSS` but we don't handle that here.
- Owns its own CSS so the picker layout stays decoupled from the editor.

Freeze criteria
--------------
- `Enter` picks the top fuzzy match.
- Selecting an option dismisses with that theme name.
- `Escape` cancels with `None`.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from modals._base import BaseModalScreen


@dataclass(frozen=True)
class ThemeOption:
    name: str


def fuzzyfind_themes(query: str, candidates: list[str], limit: int = 12) -> list[ThemeOption]:
    """Return themes ranked by fuzzy similarity on the name."""
    normalized_query = query.strip().lower()
    if not normalized_query:
        return [ThemeOption(n) for n in candidates[:limit]]

    scored: list[tuple[float, str]] = []
    for name in candidates:
        lower = name.lower()
        score = SequenceMatcher(None, normalized_query, lower).ratio()
        if lower.startswith(normalized_query):
            score += 0.35
        if normalized_query in lower:
            score += 0.2
        scored.append((score, name))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [ThemeOption(name) for score, name in scored if score > 0][:limit]


class ThemePickerScreen(BaseModalScreen[str | None]):
    CSS = """
    ThemePickerScreen {
        align: center middle;
        background: $panel 80%;
    }

    #dialog {
        width: 80%;
        height: 80%;
        padding: 1 2;
        border: round $primary;
        background: $surface;
        color: $foreground;
    }

    #theme-query {
        margin: 0 0 1 0;
    }

    #theme-list {
        height: 1fr;
    }

    .title {
        text-style: bold;
        margin-bottom: 1;
        color: $accent;
    }

    .subtitle {
        color: $foreground;
        text-style: dim;
        margin-bottom: 1;
    }
    """

    def __init__(self, themes: list[str]) -> None:
        super().__init__()
        self._themes = themes

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("Choose a theme", classes="title")
            yield Static("Type to filter, then press Enter or select.", classes="subtitle")
            yield Input(placeholder="Filter themes...", id="theme-query")
            yield OptionList(id="theme-list")

    def on_mount(self) -> None:
        self.query_one("#theme-query", Input).focus()
        self._render_options("")

    def _render_options(self, query: str) -> None:
        option_list = self.query_one("#theme-list", OptionList)
        option_list.clear_options()
        option_list.add_options([
            Option(name, id=name)
            for name in (t.name for t in fuzzyfind_themes(query, self._themes))
        ])

    @on(Input.Changed, "#theme-query")
    def on_query_changed(self, event: Input.Changed) -> None:
        self._render_options(event.value)

    @on(Input.Submitted, "#theme-query")
    def on_query_submitted(self, event: Input.Submitted) -> None:
        matches = fuzzyfind_themes(event.value, self._themes)
        if matches:
            self.dismiss(matches[0].name)

    @on(OptionList.OptionSelected, "#theme-list")
    def on_theme_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(str(event.option.id) if event.option.id is not None else None)