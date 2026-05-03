"""Internal Vim-style register for yank and paste.

Scope
-----
Stores the most recent yanked or deleted text along with its yank mode
(linewise vs charwise) and renders pastes back into a `TextArea`.

Boundaries
----------
- Does NOT integrate with the OS clipboard. Yank and paste live entirely
  in-process. This is intentional so the editor never leaks document
  contents to the system selection.
- Does NOT depend on Vim mode bookkeeping. The register only stores text
  and a boolean. Decisions about *when* to yank or paste belong to the
  keybindings module.

Freeze criteria
---------------
This module can be considered frozen once:
- `yank` stores both linewise and charwise content.
- `paste_after` inserts after the cursor (charwise) or opens a new line
  below (linewise).
- `paste_before` inserts at the cursor column (charwise) or opens a new
  line above (linewise).
- An empty register reports `register empty` and performs no insert.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RegisterContent:
    """Yanked text plus its mode.

    A linewise yank stores whole lines and pastes as new lines above or below
    the cursor. A charwise yank stores arbitrary text and pastes inline.
    """

    text: str
    linewise: bool


class Register:
    """Single unnamed Vim-style register.

    Stores the most recent yanked or deleted text. The editor uses one
    register, which keeps the implementation small while still supporting
    the y/d/x/p/P verbs that the user expects from Vim.
    """

    def __init__(self) -> None:
        self._content: RegisterContent | None = None

    def is_empty(self) -> bool:
        return self._content is None

    def yank(self, text: str, linewise: bool = False) -> None:
        """Store text in the register, marking the yank mode."""

        self._content = RegisterContent(text=text, linewise=linewise)

    def content(self) -> RegisterContent | None:
        return self._content

    def paste_after(self, editor: Any) -> str:
        """Paste register content after the cursor (Vim `p`).

        Linewise content opens a new line below the current one. Charwise
        content is inserted one column after the cursor, matching Vim.
        """

        if self._content is None:
            return "register empty"

        if self._content.linewise:
            row, _ = editor.cursor_location
            line_end = editor.get_cursor_line_end_location()
            text = self._content.text.rstrip("\n")
            editor.insert("\n" + text, line_end)
            editor.move_cursor((row + 1, 0))
            return "pasted line below"

        row, col = editor.cursor_location
        line_len = len(editor.document[row])
        target_col = min(col + 1, line_len)
        editor.insert(self._content.text, (row, target_col))
        return "pasted after"

    def paste_before(self, editor: Any) -> str:
        """Paste register content before the cursor (Vim `P`).

        Linewise content opens a new line above the current one. Charwise
        content is inserted at the cursor column, pushing existing text
        forward.
        """

        if self._content is None:
            return "register empty"

        if self._content.linewise:
            row, _ = editor.cursor_location
            text = self._content.text.rstrip("\n")
            editor.insert(text + "\n", (row, 0))
            editor.move_cursor((row, 0))
            return "pasted line above"

        editor.insert(self._content.text)
        return "pasted before"
