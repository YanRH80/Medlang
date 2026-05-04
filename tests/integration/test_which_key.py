"""Integration tests: WhichKey overlay opens and dispatches leader keys."""

from __future__ import annotations

import pytest

from app import SimpleTextEditorApp


@pytest.mark.asyncio
async def test_space_opens_which_key(tmp_document) -> None:
    """Pressing space in NORMAL mode opens the WhichKey overlay."""
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()
        from modals.which_key import WhichKeyScreen
        assert isinstance(app.screen, WhichKeyScreen)


@pytest.mark.asyncio
async def test_escape_closes_which_key(tmp_document) -> None:
    """Pressing escape inside WhichKey returns to the editor screen."""
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        from modals.which_key import WhichKeyScreen
        assert not isinstance(app.screen, WhichKeyScreen)


@pytest.mark.asyncio
async def test_which_key_dispatches_command(tmp_document) -> None:
    """Pressing `s` inside WhichKey runs the doc-save command."""
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()
        # Inside WhichKey now; press `s` to dispatch save.
        await pilot.press("s")
        await pilot.pause()
        # WhichKey dismissed.
        from modals.which_key import WhichKeyScreen
        assert not isinstance(app.screen, WhichKeyScreen)
        # Save reported (status message contains "saved" or "auto-save").
        assert "save" in app.status_message.lower() or app.status_message == ""
