"""Modeline status bar widget.

Scope
-----
Renders the editor's status line in a LazyVim-like layout:

    [NORMAL]  document.json [+]  42:7  23 lines  midnight   yanked line

Each segment is an independently styled `Static`, so colors, margins, and
emphasis can be tuned without touching state logic. The widget is
read-only: callers push a `StatusSnapshot` and the widget renders it.

Boundaries
----------
- Does NOT mutate app state. It only reads the snapshot it is given.
- Does NOT know about Vim semantics beyond a mode string. New modes only
  require an entry in `MODE_STYLES`.
- Does NOT manage timers. Transient messages can be cleared by sending an
  empty message in the next snapshot.

Freeze criteria
---------------
This module can be considered frozen once:
- Mode chip color matches the active mode (NORMAL, INSERT, VISUAL,
  VISUAL_LINE).
- Cursor position renders as `line:col` 1-indexed.
- Modified marker `[+]` appears only when `modified=True`.
- Transient message renders to the right; empty string hides the segment.
"""

from __future__ import annotations

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static


@dataclass(frozen=True)
class ModeStyle:
    """Visual style associated with a Vim mode."""

    label: str
    background: str
    foreground: str


# Industry-standard color palette inspired by LazyVim.
MODE_STYLES: dict[str, ModeStyle] = {
    "normal": ModeStyle("NORMAL", "#3b82f6", "#0b1120"),
    "insert": ModeStyle("INSERT", "#22c55e", "#0b1120"),
    "visual": ModeStyle("VISUAL", "#a855f7", "#0b1120"),
    "visual_line": ModeStyle("V-LINE", "#a855f7", "#0b1120"),
}

_FALLBACK_STYLE = ModeStyle("MODE", "#64748b", "#0b1120")


@dataclass(frozen=True)
class StatusSnapshot:
    """All values rendered in a single status update."""

    mode: str
    file_name: str
    cursor_line: int
    cursor_column: int
    line_count: int
    palette_name: str
    modified: bool
    pending: str
    message: str


class StatusBar(Horizontal):
    """Composite modeline. Update via `set_snapshot` or `update_message`."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        padding: 0;
        background: #0b1120;
        color: #cbd5e1;
    }

    StatusBar > .status-segment {
        height: 1;
        padding: 0 1;
        background: #0b1120;
        color: #cbd5e1;
    }

    StatusBar > #mode-chip {
        text-style: bold;
    }

    StatusBar > #file-segment {
        color: #f1f5f9;
        text-style: bold;
    }

    StatusBar > #message-segment {
        color: #fbbf24;
        width: 1fr;
        content-align: right middle;
    }

    StatusBar > #cursor-segment, StatusBar > #lines-segment, StatusBar > #palette-segment, StatusBar > #pending-segment {
        color: #94a3b8;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="mode-chip", classes="status-segment")
        yield Static("", id="file-segment", classes="status-segment")
        yield Static("", id="cursor-segment", classes="status-segment")
        yield Static("", id="lines-segment", classes="status-segment")
        yield Static("", id="palette-segment", classes="status-segment")
        yield Static("", id="pending-segment", classes="status-segment")
        yield Static("", id="message-segment", classes="status-segment")

    def set_snapshot(self, snapshot: StatusSnapshot) -> None:
        """Update every segment from a fresh snapshot."""

        style = MODE_STYLES.get(snapshot.mode, _FALLBACK_STYLE)

        chip = self.query_one("#mode-chip", Static)
        chip.update(f" {style.label} ")
        chip.styles.background = style.background
        chip.styles.color = style.foreground

        marker = " [+]" if snapshot.modified else ""
        self.query_one("#file-segment", Static).update(f"{snapshot.file_name}{marker}")
        self.query_one("#cursor-segment", Static).update(
            f"{snapshot.cursor_line}:{snapshot.cursor_column}"
        )
        self.query_one("#lines-segment", Static).update(f"{snapshot.line_count} lines")
        self.query_one("#palette-segment", Static).update(snapshot.palette_name)

        pending_text = f"⌛ {snapshot.pending}" if snapshot.pending else ""
        self.query_one("#pending-segment", Static).update(pending_text)
        self.query_one("#message-segment", Static).update(snapshot.message)
