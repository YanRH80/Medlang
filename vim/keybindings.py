"""Vim-like key dispatch.

Scope
-----
Translates keyboard events into editor actions while the app is in any of
the supported Vim modes: insert, normal, visual and visual-line. The
dispatcher mutates app state (mode, prefix, visual anchor) and calls
editor verbs (move cursor, delete, insert, yank/paste through
`app.register`).

Supported verbs
---------------
- Motion: h j k l, 0 $, gg G, w b e, W B E
- Insert entry: i a I A o O
- Delete: x, dd
- Yank/paste: yy, p P
- Visual: v V; in visual: y d, h j k l 0 $, w b e
- Other: u, Ctrl+R (undo/redo), `:` (open command palette)

Boundaries
----------
- Does NOT execute `:` commands. Pressing `:` calls
  `app.open_command_palette`.
- Does NOT manage the system clipboard. Yank/paste go through
  `app.register`.
- Does NOT render UI. Status messages are pushed through
  `app.set_status_message`.
- Uses ONLY public Textual APIs (`TextArea.delete`,
  `textual.widgets.text_area.Selection`).

Freeze criteria
---------------
- All listed verbs work in their respective modes.
- Mode transitions update both `app.vim_mode` and the editor's selection.
- New verbs only require touching this file.
"""

from __future__ import annotations

import re
from typing import Any

from textual.widgets.text_area import Selection

from vim.modes import VimMode


_WORD_RE = re.compile(r"\w+")
_BIG_WORD_RE = re.compile(r"\S+")


# ---------------------------------------------------------------------------
# Word motion helpers (pure functions over `(text_lines, cursor)` -> cursor).
# ---------------------------------------------------------------------------


def _spans(line: str, big: bool) -> list[tuple[int, int]]:
    pattern = _BIG_WORD_RE if big else _WORD_RE
    return [m.span() for m in pattern.finditer(line)]


def next_word_start(lines: list[str], cursor: tuple[int, int], big: bool = False) -> tuple[int, int]:
    """Vim `w` (or `W` if big). Cursor goes to the start of the next word."""

    row, col = cursor
    while row < len(lines):
        for start, _end in _spans(lines[row], big):
            if start > col:
                return (row, start)
        row += 1
        col = -1
    last = max(0, len(lines) - 1)
    return (last, len(lines[last]))


def prev_word_start(lines: list[str], cursor: tuple[int, int], big: bool = False) -> tuple[int, int]:
    """Vim `b` (or `B` if big). Cursor goes to the start of the previous word."""

    row, col = cursor
    while row >= 0:
        spans = _spans(lines[row], big)
        for start, _end in reversed(spans):
            if start < col:
                return (row, start)
        row -= 1
        if row >= 0:
            col = len(lines[row]) + 1
    return (0, 0)


def next_word_end(lines: list[str], cursor: tuple[int, int], big: bool = False) -> tuple[int, int]:
    """Vim `e` (or `E` if big). Cursor goes to the last char of the next word."""

    row, col = cursor
    while row < len(lines):
        for start, end in _spans(lines[row], big):
            last = end - 1
            if last > col:
                return (row, last)
        row += 1
        col = -1
    last_row = max(0, len(lines) - 1)
    return (last_row, max(0, len(lines[last_row]) - 1))


# ---------------------------------------------------------------------------
# Mode-entry helpers (delegated to the app to keep state mutation in one place).
# ---------------------------------------------------------------------------


def _enter_insert_mode(app: Any) -> None:
    app.enter_insert_mode()


def _enter_normal_mode(app: Any, editor: Any) -> None:
    editor.selection = Selection.cursor(editor.cursor_location)
    app.enter_normal_mode()


def _enter_visual_mode(app: Any, editor: Any, linewise: bool = False) -> None:
    app.enter_visual_mode(linewise=linewise)
    if linewise:
        row, _ = editor.cursor_location
        editor.selection = Selection((row, 0), (row, len(editor.document[row])))
    else:
        editor.selection = Selection.cursor(editor.cursor_location)


def _delete_visual_selection(app: Any, editor: Any) -> None:
    """Delete the current selection using the public `TextArea.delete` API."""

    start, end = editor.selection
    if start != end:
        editor.delete(start, end)
    _enter_normal_mode(app, editor)


def _start_of_document(editor: Any) -> None:
    editor.move_cursor((0, 0))


def _end_of_document(editor: Any) -> None:
    last_row = max(0, editor.document.line_count - 1)
    editor.move_cursor((last_row, len(editor.document[last_row])))


def _open_line(editor: Any, below: bool) -> None:
    row, _ = editor.cursor_location
    line_start = (row, 0)
    line_end = editor.get_cursor_line_end_location()

    if below:
        editor.insert("\n", line_end)
        editor.move_cursor((row + 1, 0))
    else:
        editor.insert("\n", line_start)
        editor.move_cursor((row, 0))


def _doc_lines(editor: Any) -> list[str]:
    """Return a snapshot of every line as a Python list."""

    return [editor.document[row] for row in range(editor.document.line_count)]


def _join_lines(app: Any, editor: Any) -> None:
    """Join current line with the line below. Cursor moves to end of joined line."""
    row, _ = editor.cursor_location
    total = editor.document.line_count
    if row >= total - 1:
        return
    cur_end = editor.get_cursor_line_end_location()
    next_start = cur_end
    next_end = (row + 1, 0)
    editor.replace(" ", next_start, next_end)
    new_pos = editor.get_cursor_line_end_location()
    editor.move_cursor(new_pos)
    app.set_status_message("joined")


def _move_word(editor: Any, kind: str) -> None:
    """Apply a word-motion verb. `kind` is one of w b e W B E."""

    cursor = editor.cursor_location
    lines = _doc_lines(editor)
    if kind == "w":
        target = next_word_start(lines, cursor, big=False)
    elif kind == "W":
        target = next_word_start(lines, cursor, big=True)
    elif kind == "b":
        target = prev_word_start(lines, cursor, big=False)
    elif kind == "B":
        target = prev_word_start(lines, cursor, big=True)
    elif kind == "e":
        target = next_word_end(lines, cursor, big=False)
    elif kind == "E":
        target = next_word_end(lines, cursor, big=True)
    else:
        return
    editor.move_cursor(target)


def _update_visual_selection(app: Any, editor: Any, target: Any, linewise: bool = False) -> None:
    anchor = app.visual_anchor or editor.cursor_location
    if linewise:
        anchor_row = anchor[0]
        target_row = target[0]
        start = (anchor_row, 0)
        end = (target_row, len(editor.document[target_row]))
        editor.selection = Selection(start, end)
    else:
        editor.selection = Selection(anchor, target)


def _move_with_mode(app: Any, editor: Any, move: Any, *, linewise: bool = False) -> None:
    move()
    if app.vim_mode == VimMode.VISUAL:
        _update_visual_selection(app, editor, editor.cursor_location, linewise=False)
    elif app.vim_mode == VimMode.VISUAL_LINE:
        _update_visual_selection(app, editor, editor.cursor_location, linewise=True)


# ---------------------------------------------------------------------------
# Main dispatcher.
# ---------------------------------------------------------------------------


def handle_vim_key(app: Any, editor: Any, event: Any) -> bool:
    """Handle Vim-like keyboard input. Returns True when the key was consumed."""

    key = event.key
    character = event.character or ""
    mode = app.vim_mode

    if mode == VimMode.INSERT:
        if key == "escape":
            _enter_normal_mode(app, editor)
            app.set_status_message("normal mode")
            return True
        return False

    if key == "escape":
        _enter_normal_mode(app, editor)
        app.set_status_message("normal mode")
        return True

    if character == ":" or key == ":":
        app.open_command_palette()
        return True

    if mode == VimMode.NORMAL and key == "v":
        _enter_visual_mode(app, editor, linewise=False)
        app.set_status_message("visual mode")
        return True

    if mode == VimMode.NORMAL and key == "V":
        _enter_visual_mode(app, editor, linewise=True)
        app.set_status_message("visual-line mode")
        return True

    if mode in {VimMode.VISUAL, VimMode.VISUAL_LINE}:
        if key == "v" and mode == VimMode.VISUAL:
            _enter_normal_mode(app, editor)
            app.set_status_message("normal mode")
            return True
        if key == "V" and mode == VimMode.VISUAL_LINE:
            _enter_normal_mode(app, editor)
            app.set_status_message("normal mode")
            return True
        if key == "d":
            app.register.yank(editor.selected_text, linewise=mode == VimMode.VISUAL_LINE)
            _delete_visual_selection(app, editor)
            app.set_status_message("deleted selection")
            return True
        if key == "y":
            app.register.yank(editor.selected_text, linewise=mode == VimMode.VISUAL_LINE)
            _enter_normal_mode(app, editor)
            app.set_status_message("yanked selection")
            return True
        if key in {"h", "j", "k", "l", "0", "$"}:
            move_map = {
                "h": editor.action_cursor_left,
                "j": editor.action_cursor_down,
                "k": editor.action_cursor_up,
                "l": editor.action_cursor_right,
                "0": editor.action_cursor_line_start,
                "$": editor.action_cursor_line_end,
            }
            _move_with_mode(app, editor, move_map[key], linewise=mode == VimMode.VISUAL_LINE)
            return True
        if key in {"w", "b", "e", "W", "B", "E"}:
            _move_word(editor, key)
            if mode == VimMode.VISUAL:
                _update_visual_selection(app, editor, editor.cursor_location, linewise=False)
            elif mode == VimMode.VISUAL_LINE:
                _update_visual_selection(app, editor, editor.cursor_location, linewise=True)
            return True

    if mode == VimMode.NORMAL:
        pending = app.vim_prefix

        if pending == "d":
            app.vim_prefix = ""
            if key == "d":
                row, _ = editor.cursor_location
                line_text = editor.document[row]
                app.register.yank(line_text, linewise=True)
                editor.action_delete_line()
                app.set_status_message("deleted line")
            return True

        if pending == "y":
            app.vim_prefix = ""
            if key == "y":
                row, _ = editor.cursor_location
                line_text = editor.document[row]
                app.register.yank(line_text, linewise=True)
                app.set_status_message("yanked line")
            return True

        if pending == "g":
            app.vim_prefix = ""
            if key == "g":
                _start_of_document(editor)
                app.set_status_message("top of document")
            return True

        if key == "d":
            app.vim_prefix = "d"
            app.set_status_message("d…")
            return True

        if key == "y":
            app.vim_prefix = "y"
            app.set_status_message("y…")
            return True

        if key == "g":
            app.vim_prefix = "g"
            app.set_status_message("g…")
            return True

        if key == "space":
            if hasattr(app, "open_which_key"):
                app.open_which_key()
            return True

        if key == "i":
            _enter_insert_mode(app)
            app.set_status_message("insert mode")
            return True

        if key == "a":
            editor.action_cursor_right()
            _enter_insert_mode(app)
            app.set_status_message("append mode")
            return True

        if key == "A":
            editor.action_cursor_line_end()
            _enter_insert_mode(app)
            app.set_status_message("append end of line")
            return True

        if key == "I":
            editor.action_cursor_line_start()
            _enter_insert_mode(app)
            app.set_status_message("insert at line start")
            return True

        if key == "x":
            row, col = editor.cursor_location
            line_text = editor.document[row]
            if col < len(line_text):
                app.register.yank(line_text[col], linewise=False)
            editor.action_delete_right()
            app.set_status_message("deleted char")
            return True

        if key == "p":
            message = app.register.paste_after(editor)
            app.set_status_message(message)
            return True

        if key == "P":
            message = app.register.paste_before(editor)
            app.set_status_message(message)
            return True

        if key == "o":
            _open_line(editor, below=True)
            _enter_insert_mode(app)
            app.set_status_message("open line below")
            return True

        if key == "O":
            _open_line(editor, below=False)
            _enter_insert_mode(app)
            app.set_status_message("open line above")
            return True

        if key == "J":
            _join_lines(app, editor)
            return True

        if key in {"h", "j", "k", "l", "0", "$"}:
            move_map = {
                "h": editor.action_cursor_left,
                "j": editor.action_cursor_down,
                "k": editor.action_cursor_up,
                "l": editor.action_cursor_right,
                "0": editor.action_cursor_line_start,
                "$": editor.action_cursor_line_end,
            }
            move_map[key]()
            return True

        if key in {"w", "b", "e", "W", "B", "E"}:
            _move_word(editor, key)
            return True

        if key == "G":
            _end_of_document(editor)
            app.set_status_message("end of document")
            return True

        if key == "u":
            editor.action_undo()
            app.set_status_message("undo")
            return True

        if key == "ctrl+r":
            editor.action_redo()
            app.set_status_message("redo")
            return True

    # Let modified keys (ctrl/alt/super/shift combos) propagate to app-level
    # bindings so ctrl+p, super+h/j/k/l etc. reach the app's BINDINGS.
    if "+" in key:
        return False

    # Swallow unhandled keys in non-insert modes to prevent accidental edits.
    event.stop()
    event.prevent_default()
    return True
