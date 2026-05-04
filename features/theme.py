"""Theme commands (toggle, pick).

Scope
-----
Registers `theme-toggle` and `theme-pick`. The actual theme switching
goes through Textual's native `app.theme` setter; we only expose the
commands.

Boundaries
----------
- Does NOT define themes (Textual ships 21).
- Does NOT own the theme picker UI (lives in `modals.theme_picker`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from commands import (
    Command,
    CommandRegistry,
    CommandResult,
    description_from_config,
    is_enabled_in_config,
)
from themes import toggle_light_dark

if TYPE_CHECKING:
    from app import SimpleTextEditorApp


def _make(commands_cfg: dict, name: str, default_description: str, handler) -> Command:
    return Command(
        name=name,
        description=description_from_config(commands_cfg, name, default_description),
        handler=handler,
        enabled=is_enabled_in_config(commands_cfg, name),
    )


def _cmd_theme_toggle(app: Any) -> CommandResult:
    return CommandResult(True, toggle_light_dark(app))


def _cmd_theme_pick(app: Any) -> CommandResult:
    app.open_theme_picker()
    return CommandResult(True, "theme picker opened")


def register(app: "SimpleTextEditorApp", registry: CommandRegistry) -> None:
    cfg = app.config_data.get("commands", {})
    registry.register(_make(cfg, "theme-toggle", "Toggle between dark and light theme.", _cmd_theme_toggle))
    registry.register(_make(cfg, "theme-pick", "Open the theme picker.", _cmd_theme_pick))
