"""Unit tests for `vim.modes` (VimMode, transitions)."""

from __future__ import annotations

from unittest.mock import MagicMock

from vim.modes import VimMode, enter_insert, enter_normal, enter_visual


def _fake_app(cursor=(0, 0), line_text: str = "abc"):
    """Construct an app double whose `_editor()` returns a controllable editor."""

    editor = MagicMock()
    editor.cursor_location = cursor
    # `editor.document[row]` returns the line text for any row index.
    document = MagicMock()
    document.__getitem__ = MagicMock(return_value=line_text)
    editor.document = document

    app = MagicMock()
    app._editor.return_value = editor
    return app, editor


def test_vim_mode_values() -> None:
    assert VimMode.NORMAL.value == "normal"
    assert VimMode.INSERT.value == "insert"
    assert VimMode.VISUAL.value == "visual"
    assert VimMode.VISUAL_LINE.value == "visual_line"


def test_enter_normal_clears_anchor_and_prefix() -> None:
    app, editor = _fake_app()
    app.visual_anchor = (1, 2)
    app.vim_prefix = "g"

    enter_normal(app)

    assert app.visual_anchor is None
    assert app.vim_prefix == ""
    assert app.vim_mode == VimMode.NORMAL
    app.refresh_status.assert_called_once()
    app._update_panel_borders.assert_called_once()


def test_enter_insert_clears_state_and_sets_mode() -> None:
    app, editor = _fake_app()
    app.visual_anchor = (3, 4)
    app.vim_prefix = "d"

    enter_insert(app)

    assert app.visual_anchor is None
    assert app.vim_prefix == ""
    assert app.vim_mode == VimMode.INSERT


def test_enter_visual_records_anchor() -> None:
    app, editor = _fake_app(cursor=(2, 5))
    app.visual_anchor = None

    enter_visual(app, linewise=False)

    assert app.visual_anchor == (2, 5)
    assert app.vim_mode == VimMode.VISUAL


def test_enter_visual_linewise_sets_visual_line_mode() -> None:
    app, editor = _fake_app(cursor=(2, 5))

    enter_visual(app, linewise=True)

    assert app.vim_mode == VimMode.VISUAL_LINE
