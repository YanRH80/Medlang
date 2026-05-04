"""Pane commands (toggle files, focus files/editor).

Scope
-----
Three commands controlling the layout: show/hide the file panel and
move keyboard focus between panels.

Boundaries
----------
- Pane focus mutations go through `app._focused_panel` and
  `app._update_panel_borders` (defined on the App).
- Layout changes go through `app._layout_manager`.
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
from widgets.files_panel import FileTreePanel

if TYPE_CHECKING:
    from app import SimpleTextEditorApp


def _make(commands_cfg: dict, name: str, default_description: str, handler) -> Command:
    return Command(
        name=name,
        description=description_from_config(commands_cfg, name, default_description),
        handler=handler,
        enabled=is_enabled_in_config(commands_cfg, name),
    )


def _cmd_pane_files_toggle(app: Any) -> CommandResult:
    if app._layout_manager is None:
        return CommandResult(False, "layout not ready")
    visible = app._layout_manager.toggle("pane-files")
    return CommandResult(True, f"files panel {'shown' if visible else 'hidden'}")


def _cmd_pane_focus_files(app: Any) -> CommandResult:
    try:
        tree = app.query_one("#pane-files", FileTreePanel)
        tree.focus()
        app._focused_panel = "pane-files"
        app._update_panel_borders()
        return CommandResult(True, "focused files panel")
    except Exception:
        return CommandResult(False, "files panel not available")


def _cmd_pane_focus_editor(app: Any) -> CommandResult:
    app._editor().focus()
    app._focused_panel = "editor"
    app._update_panel_borders()
    return CommandResult(True, "focused editor")


def register(app: "SimpleTextEditorApp", registry: CommandRegistry) -> None:
    cfg = app.config_data.get("commands", {})
    registry.register(_make(cfg, "pane-files-toggle", "Toggle the file panel.", _cmd_pane_files_toggle))
    registry.register(_make(cfg, "pane-focus-files", "Focus the file panel.", _cmd_pane_focus_files))
    registry.register(_make(cfg, "pane-focus-editor", "Focus the editor.", _cmd_pane_focus_editor))
