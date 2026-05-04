"""Pilot-driven integration tests for the command palette modal."""

from __future__ import annotations

import pytest
from textual.widgets import Input, OptionList

from modals.command_palette import CommandPaletteScreen
from commands import Command, CommandRegistry, CommandResult


def _build_registry() -> CommandRegistry:
    r = CommandRegistry()
    r.register(Command("light-dark-mode", "Toggle theme", lambda app: CommandResult(True, "x")))
    r.register(Command("palette", "Open palettes", lambda app: CommandResult(True, "x")))
    r.register(Command("rename", "Rename file", lambda app: CommandResult(True, "x")))
    r.register(Command("save", "Force save", lambda app: CommandResult(True, "x")))
    return r


class _PaletteHostApp:
    """Tiny App that pushes the CommandPaletteScreen on mount."""

    @staticmethod
    def make():
        from textual.app import App

        registry = _build_registry()

        class HostApp(App):
            def __init__(self) -> None:
                super().__init__()
                self.result: object | None = "<unset>"

            async def on_mount(self) -> None:
                self.push_screen(
                    CommandPaletteScreen(registry),
                    callback=self._capture,
                )

            def _capture(self, value):
                self.result = value

        return HostApp()


@pytest.mark.asyncio
async def test_modal_opens_with_full_command_list() -> None:
    app = _PaletteHostApp.make()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, CommandPaletteScreen)
        option_list = screen.query_one("#command-list", OptionList)
        assert option_list.option_count == 4


@pytest.mark.asyncio
async def test_typing_filters_options() -> None:
    app = _PaletteHostApp.make()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, CommandPaletteScreen)

        await pilot.press("l", "i", "g")
        await pilot.pause()

        option_list = screen.query_one("#command-list", OptionList)
        # Only "light-dark-mode" should remain (prefix match).
        assert option_list.option_count == 1
        first = option_list.get_option_at_index(0)
        assert first.id == "light-dark-mode"


@pytest.mark.asyncio
async def test_enter_dismisses_with_top_match() -> None:
    app = _PaletteHostApp.make()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("p", "a", "l")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.result == "palette"


@pytest.mark.asyncio
async def test_escape_dismisses_with_none() -> None:
    app = _PaletteHostApp.make()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert app.result is None


@pytest.mark.asyncio
async def test_down_arrow_focuses_option_list() -> None:
    app = _PaletteHostApp.make()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, CommandPaletteScreen)

        input_widget = screen.query_one("#command-query", Input)
        option_list = screen.query_one("#command-list", OptionList)
        assert screen.focused is input_widget

        await pilot.press("down")
        await pilot.pause()

        assert screen.focused is option_list
        assert option_list.highlighted == 0


@pytest.mark.asyncio
async def test_up_arrow_returns_focus_to_input() -> None:
    app = _PaletteHostApp.make()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, CommandPaletteScreen)

        await pilot.press("down")
        await pilot.pause()
        await pilot.press("up")
        await pilot.pause()

        input_widget = screen.query_one("#command-query", Input)
        assert screen.focused is input_widget


@pytest.mark.asyncio
async def test_enter_on_option_list_dismisses_with_that_option() -> None:
    app = _PaletteHostApp.make()
    async with app.run_test() as pilot:
        await pilot.pause()

        # Bridge into the list.
        await pilot.press("down")
        await pilot.pause()

        # Move highlight down once (to the second option = "palette").
        await pilot.press("down")
        await pilot.pause()

        await pilot.press("enter")
        await pilot.pause()

        assert app.result == "palette"
