"""Integration test: every feature module registers expected commands."""

from __future__ import annotations

import pytest

from app import SimpleTextEditorApp


EXPECTED_COMMANDS = {
    "theme-toggle",
    "theme-pick",
    "doc-save",
    "doc-new",
    "doc-open",
    "doc-rename",
    "doc-delete",
    "pane-files-toggle",
    "pane-focus-files",
    "pane-focus-editor",
    "hotkeys",
    "hotkey-set",
    "command-palette",
}


@pytest.mark.asyncio
async def test_all_feature_commands_registered(tmp_document) -> None:
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        registered = set(app.command_registry.command_names())
        missing = EXPECTED_COMMANDS - registered
        assert not missing, f"missing commands: {missing}"


@pytest.mark.asyncio
async def test_no_unexpected_commands(tmp_document) -> None:
    """Catch typos / leftover registrations."""
    app = SimpleTextEditorApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        registered = set(app.command_registry.command_names())
        unexpected = registered - EXPECTED_COMMANDS
        assert not unexpected, f"unexpected commands: {unexpected}"
