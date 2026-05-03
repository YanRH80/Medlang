"""Modeline status bar widget — LazyVim-style single-line modeline.

Scope
-----
Renders the editor's status line:

    [NORMAL]  document.json [+]  Ln 42, Col 7  ⌛ space  yanked line

Boundaries
----------
- Does NOT mutate app state. It only reads the snapshot it is given.
- Does NOT know about Vim semantics beyond a mode string. New modes only
  require an entry in `MODE_STYLES`.

Freeze criteria
---------------
- Mode chip uses theme variables ($primary/$success/$accent).
- Cursor position renders as `Ln N, Col N`.
- Modified marker `[+]` appears only when `modified=True`.
- Pending operator shows as `⌛ key` (d/y/g/space).
- Transient message auto-clears (managed by app timer).
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
    css_class: str


MODE_STYLES: dict[str, ModeStyle] = {
    "normal":     ModeStyle("NORMAL",  "mode-normal"),
    "insert":     ModeStyle("INSERT",  "mode-insert"),
    "visual":     ModeStyle("VISUAL",  "mode-visual"),
    "visual_line": ModeStyle("V-LINE", "mode-visual"),
}

_FALLBACK_STYLE = ModeStyle("MODE", "mode-fallback")


@dataclass(frozen=True)
class StatusSnapshot:
    """All values rendered in a single status update."""

    mode: str
    file_name: str
    cursor_line: int
    cursor_column: int
    modified: bool
    pending: str
    message: str


class StatusBar(Horizontal):
    """Single-line modeline. Update via `set_snapshot`."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        padding: 0;
        background: $panel;
        color: $foreground;
    }

    StatusBar > .status-segment {
        height: 1;
        padding: 0 1;
        background: $panel;
        color: $foreground;
    }

    StatusBar > #mode-chip {
        text-style: bold;
    }

    StatusBar > #mode-chip.mode-normal {
        background: $primary;
        color: $background;
    }

    StatusBar > #mode-chip.mode-insert {
        background: $success;
        color: $background;
    }

    StatusBar > #mode-chip.mode-visual,
    StatusBar > #mode-chip.mode-visual-line {
        background: $accent;
        color: $background;
    }

    StatusBar > #mode-chip.mode-fallback {
        background: $panel;
        color: $foreground;
    }

    StatusBar > #file-segment {
        color: $primary;
        text-style: bold;
    }

    StatusBar > #position-segment {
        color: $foreground;
        text-style: dim;
    }

    StatusBar > #pending-segment {
        color: $foreground;
        text-style: dim;
    }

    StatusBar > #message-segment {
        color: $accent;
        width: 1fr;
        content-align: right middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="mode-chip", classes="status-segment")
        yield Static("", id="file-segment", classes="status-segment")
        yield Static("", id="position-segment", classes="status-segment")
        yield Static("", id="pending-segment", classes="status-segment")
        yield Static("", id="message-segment", classes="status-segment")

    def set_snapshot(self, snapshot: StatusSnapshot) -> None:
        """Update every segment from a fresh snapshot."""

        style = MODE_STYLES.get(snapshot.mode, _FALLBACK_STYLE)

        chip = self.query_one("#mode-chip", Static)
        chip.update(f" {style.label} ")
        for cls in ("mode-normal", "mode-insert", "mode-visual", "mode-fallback"):
            chip.remove_class(cls)
        chip.add_class(style.css_class)

        marker = " [+]" if snapshot.modified else ""
        self.query_one("#file-segment", Static).update(f"{snapshot.file_name}{marker}")

        self.query_one("#position-segment", Static).update(
            f"Ln {snapshot.cursor_line}, Col {snapshot.cursor_column}"
        )

        pending_text = f"⌛ {snapshot.pending}" if snapshot.pending else ""
        self.query_one("#pending-segment", Static).update(pending_text)
        self.query_one("#message-segment", Static).update(snapshot.message)