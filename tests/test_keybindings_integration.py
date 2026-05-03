"""Regression shield: exercise every verb key, verify no crash + state intact."""

from __future__ import annotations

from pathlib import Path

import pytest

import app as app_module
from app import SimpleTextEditorApp
from editor_keybindings import VimMode


@pytest.fixture
def tmp_document(tmp_path: Path, monkeypatch):
    doc_path = tmp_path / "doc.json"
    cfg = {
        "app": {"title": "T", "subtitle": "S"},
        "editor": {
            "placeholder": "",
            "soft_wrap": False,
            "show_line_numbers": True,
            "vim_start_mode": "normal",
            "palette": "midnight",
        },
        "storage": {
            "document_path": str(doc_path),
            "auto_save": True,
        },
        "commands": {},
    }
    monkeypatch.setattr(app_module, "_load_config", lambda: (cfg, []))
    return doc_path


@pytest.mark.asyncio
async def test_all_motion_verbs_dont_crash(tmp_document) -> None:
    """h j k l 0 $ gg G w b e W B E — none raise NameError."""
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("i")
        await pilot.press("a", "b", "c", "space", "d", "e", "f")
        await pilot.press("escape")
        await pilot.pause()
        for key in ("h", "j", "k", "l", "0", "$", "g", "g"):
            await pilot.press(key)
            await pilot.pause()
        for key in ("w", "b", "e", "W", "B", "E"):
            await pilot.press(key)
            await pilot.pause()
        assert app.vim_mode == VimMode.NORMAL


@pytest.mark.asyncio
async def test_insert_entry_exit_dont_crash(tmp_document) -> None:
    """i a I A o O escape — none crash."""
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        for key in ("i", "a", "I", "A", "o", "O", "escape"):
            await pilot.press(key)
            await pilot.pause()
        assert app.vim_mode == VimMode.NORMAL


@pytest.mark.asyncio
async def test_delete_x_doesnt_crash(tmp_document) -> None:
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("i")
        await pilot.press("a", "b", "c")
        await pilot.press("escape")
        await pilot.pause()
        await pilot.press("x")
        await pilot.pause()
        assert app.vim_mode == VimMode.NORMAL


@pytest.mark.asyncio
async def test_delete_dd_doesnt_crash(tmp_document) -> None:
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("i")
        await pilot.press("a", "enter", "b")
        await pilot.press("escape")
        await pilot.press("g", "g")
        await pilot.press("d", "d")
        await pilot.pause()
        assert app.vim_mode == VimMode.NORMAL


@pytest.mark.asyncio
async def test_yy_paste_dont_crash(tmp_document) -> None:
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("i")
        await pilot.press("a", "b", "c")
        await pilot.press("escape")
        await pilot.pause()
        await pilot.press("y", "y")
        await pilot.press("p")
        await pilot.pause()
        assert app.vim_mode == VimMode.NORMAL


@pytest.mark.asyncio
async def test_join_J_doesnt_crash_or_bulk_edit(tmp_document) -> None:
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("i")
        await pilot.press("a", "enter", "b")
        await pilot.press("escape")
        await pilot.press("g", "g")  # go to line 0 before joining
        await pilot.press("J")
        await pilot.pause()
        editor = app.query_one("#editor")
        assert "a b" in editor.text or "ab" in editor.text
        assert app.vim_mode == VimMode.NORMAL


@pytest.mark.asyncio
async def test_visual_v_doesnt_crash(tmp_document) -> None:
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("i")
        await pilot.press("a", "b", "c")
        await pilot.press("escape")
        await pilot.press("v")
        await pilot.pause()
        assert app.vim_mode == VimMode.VISUAL


@pytest.mark.asyncio
async def test_undo_u_doesnt_crash(tmp_document) -> None:
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("i")
        await pilot.press("a", "b", "c")
        await pilot.press("escape")
        await pilot.press("u")
        await pilot.pause()
        editor = app.query_one("#editor")
        assert editor.text == ""
        assert app.vim_mode == VimMode.NORMAL


@pytest.mark.asyncio
async def test_redo_ctrl_r_doesnt_crash(tmp_document) -> None:
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("i")
        await pilot.press("a", "b", "c")
        await pilot.press("escape")
        await pilot.press("u")
        await pilot.pause()
        await pilot.press("ctrl+r")
        await pilot.pause()
        editor = app.query_one("#editor")
        assert editor.text == "abc"
        assert app.vim_mode == VimMode.NORMAL


@pytest.mark.asyncio
async def test_modifier_keys_dont_crash(tmp_document) -> None:
    """ctrl+/alt+ keys propagate to app BINDINGS, no crash. super is gone."""
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        for key in (
            "ctrl+h",
            "ctrl+l",
            "ctrl+k",
            "ctrl+j",
            "ctrl+p",
            "ctrl+s",
            "ctrl+b",
        ):
            await pilot.press(key)
            await pilot.pause()
        assert app.vim_mode == VimMode.NORMAL


@pytest.mark.asyncio
async def test_space_leader_new_doc(tmp_document) -> None:
    """space opens WhichKey, then n opens new doc modal."""
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()
        from editor_which_key import WhichKeyScreen
        assert isinstance(app.screen, WhichKeyScreen)
        await pilot.press("n")
        await pilot.pause()
        from editor_new_doc import NewDocScreen
        assert isinstance(app.screen, NewDocScreen)


@pytest.mark.asyncio
async def test_space_leader_open_doc(tmp_document) -> None:
    """space opens WhichKey, then o opens doc picker modal."""
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()
        from editor_which_key import WhichKeyScreen
        assert isinstance(app.screen, WhichKeyScreen)
        await pilot.press("o")
        await pilot.pause()
        from editor_doc_picker import DocPickerScreen
        assert isinstance(app.screen, DocPickerScreen)