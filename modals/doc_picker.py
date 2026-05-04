"""Modal screen for picking a document from the vault.

Scope
-----
Owns the modal UI that lists all .json files in the vault, filters
them fuzzy-style as the user types, and returns the chosen file path
(or None on cancel). Uses the same fuzzy algorithm as the command palette.

Boundaries
----------
- Does NOT load or save documents. The caller handles that.
- Does NOT know about the editor state. Pure UI only.

Freeze criteria
--------------
- Enter picks the top fuzzy match.
- Selecting an option dismisses with that path.
- Escape cancels with None.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from modals._base import BaseModalScreen


@dataclass(frozen=True)
class DocOption:
    path: Path


def fuzzyfind_docs(query: str, candidates: list[Path], limit: int = 20) -> list[DocOption]:
    """Return doc paths ranked by fuzzy similarity on the filename."""
    normalized_query = query.strip().lower()
    if not normalized_query:
        return [DocOption(p) for p in candidates[:limit]]
    scored: list[tuple[float, Path]] = []
    for path in candidates:
        name = path.name.lower()
        score = SequenceMatcher(None, normalized_query, name).ratio()
        if name.startswith(normalized_query):
            score += 0.35
        if normalized_query in name:
            score += 0.2
        scored.append((score, path))
    scored.sort(key=lambda item: (-item[0], item[1].name))
    return [DocOption(p) for score, p in scored if score > 0][:limit]


class DocPickerScreen(BaseModalScreen[str | None]):
    CSS = """
    DocPickerScreen {
        align: center middle;
        background: $panel 80%;
    }

    #dialog {
        width: 70%;
        max-width: 80;
        height: 70%;
        max-height: 25;
        padding: 1 2;
        border: round $primary;
        background: $surface;
        color: $foreground;
    }

    #doc-query {
        margin: 0 0 1 0;
    }

    #doc-list {
        height: 1fr;
    }

    .title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .subtitle {
        color: $foreground;
        text-style: dim;
        margin-bottom: 1;
    }
    """

    def __init__(self, docs: list[Path]) -> None:
        super().__init__()
        self._docs = docs

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("Open document", classes="title")
            yield Static("Type to filter, then press Enter or select.", classes="subtitle")
            yield Input(placeholder="Filter files...", id="doc-query")
            yield OptionList(id="doc-list")

    def on_mount(self) -> None:
        self.query_one("#doc-query", Input).focus()
        self._render_options("")

    def _render_options(self, query: str) -> None:
        option_list = self.query_one("#doc-list", OptionList)
        option_list.clear_options()
        options = fuzzyfind_docs(query, self._docs)
        if not options:
            option_list.add_option(Option("(no files)", id=None, disabled=True))
            return
        for opt in options:
            option_list.add_option(Option(opt.path.name, id=str(opt.path)))

    @on(Input.Changed, "#doc-query")
    def on_query_changed(self, event: Input.Changed) -> None:
        self._render_options(event.value)

    @on(Input.Submitted, "#doc-query")
    def on_query_submitted(self, event: Input.Submitted) -> None:
        matches = fuzzyfind_docs(event.value, self._docs)
        if matches:
            self.dismiss(str(matches[0].path))

    @on(OptionList.OptionSelected, "#doc-list")
    def on_doc_selected(self, event: OptionList.OptionSelected) -> None:
        opt_id = event.option.id
        if opt_id is None:
            return
        self.dismiss(opt_id)