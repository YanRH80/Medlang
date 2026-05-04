"""End-to-end Pilot tests: launch the app, drive it, assert behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from app import SimpleTextEditorApp
from vim.keybindings import VimMode


@pytest.mark.asyncio
async def test_app_starts_in_normal_mode(tmp_document) -> None:
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.vim_mode == VimMode.NORMAL


@pytest.mark.asyncio
async def test_pressing_i_enters_insert_mode(tmp_document) -> None:
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("i")
        await pilot.pause()
        assert app.vim_mode == VimMode.INSERT


@pytest.mark.asyncio
async def test_typing_in_insert_writes_text(tmp_document) -> None:
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("i")
        await pilot.press("h", "i")
        await pilot.pause()
        editor = app.query_one("#editor")
        assert editor.text == "hi"


@pytest.mark.asyncio
async def test_escape_returns_to_normal(tmp_document) -> None:
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("i")
        await pilot.press("escape")
        await pilot.pause()
        assert app.vim_mode == VimMode.NORMAL


@pytest.mark.asyncio
async def test_colon_in_normal_opens_command_palette(tmp_document) -> None:
    from modals.command_palette import CommandPaletteScreen

    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("colon")
        await pilot.pause()
        assert isinstance(app.screen, CommandPaletteScreen)


@pytest.mark.asyncio
async def test_yy_then_p_duplicates_line(tmp_document) -> None:
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        # Insert a line.
        await pilot.press("i")
        await pilot.press("h", "e", "l", "l", "o")
        await pilot.press("escape")
        await pilot.pause()
        # Yank line, paste below.
        await pilot.press("y", "y")
        await pilot.press("p")
        await pilot.pause()

        editor = app.query_one("#editor")
        assert editor.text == "hello\nhello"


@pytest.mark.asyncio
async def test_dd_deletes_line(tmp_document) -> None:
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("i")
        await pilot.press("a", "enter", "b", "enter", "c")
        await pilot.press("escape")
        await pilot.press("g", "g")  # top of doc
        await pilot.press("d", "d")
        await pilot.pause()
        editor = app.query_one("#editor")
        assert editor.text == "b\nc"


@pytest.mark.asyncio
async def test_save_persists_to_disk(tmp_document: Path) -> None:
    import json

    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("i")
        await pilot.press("a", "b", "c")
        await pilot.press("escape")
        await pilot.pause()

        assert tmp_document.exists()
        raw = json.loads(tmp_document.read_text())
        assert [line["text"] for line in raw["lines"]] == ["abc"]
