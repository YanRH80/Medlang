"""WhichKey + leader-key dispatch.

Scope
-----
Owns the LazyVim-style leader experience:

- `space` (handled in `vim/keybindings.py`) calls `app.open_which_key()`.
- WhichKey shows the available `space+<key>` commands and dismisses with
  the chosen key.
- `app.leader_dispatch(key)` looks the key up in `LEADER_MAP` and runs
  the registered handler.

The `command-palette` command also lives here because it is logically a
leader command (`space p`) and avoids cluttering `app.py`.

Boundaries
----------
- Does NOT execute Vim verbs. Verbs live in `vim/keybindings.py`.
- Does NOT own the WhichKey UI (lives in `modals/which_key.py`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from commands import (
    Command,
    CommandRegistry,
    CommandResult,
    description_from_config,
    is_enabled_in_config,
)

if TYPE_CHECKING:
    from app import SimpleTextEditorApp


# ---------------------------------------------------------------------------
# Leader map: key → (action, label_for_status)
# ---------------------------------------------------------------------------
# `action(app)` runs the corresponding command. Order matches WhichKey's
# COMMANDS list so adding a key here is the only change required.

def _dispatch_command(app: Any, name: str) -> None:
    """Run a registered command by name and surface its message."""

    result = app.command_registry.execute(app, name)
    if result.message:
        app.set_status_message(result.message)


def _action_command_palette(app: Any) -> None:
    app.open_command_palette()


def _action_show_hotkeys(app: Any) -> None:
    _dispatch_command(app, "hotkeys")


def _action_pending_vertical(app: Any) -> None:
    """Placeholder for j/k leader keys until vertical splits exist.

    The keys are surfaced in WhichKey so users see them as part of the
    roadmap; until the feature lands they emit a status message rather
    than silently no-op.
    """

    app.set_status_message("vertical split: not yet implemented")


LEADER_MAP: dict[str, Callable[[Any], None]] = {
    "n": lambda app: _dispatch_command(app, "doc-new"),
    "o": lambda app: _dispatch_command(app, "doc-open"),
    "s": lambda app: _dispatch_command(app, "doc-save"),
    "d": lambda app: _dispatch_command(app, "doc-delete"),
    "p": _action_command_palette,
    "b": lambda app: _dispatch_command(app, "pane-files-toggle"),
    "h": lambda app: _dispatch_command(app, "pane-focus-files"),
    "j": _action_pending_vertical,
    "k": _action_pending_vertical,
    "l": lambda app: _dispatch_command(app, "pane-focus-editor"),
    "?": _action_show_hotkeys,
}


def dispatch(app: Any, key: str) -> None:
    """Run the leader key handler for `key`. No-op if unknown."""

    handler = LEADER_MAP.get(key)
    if handler is not None:
        handler(app)


# ---------------------------------------------------------------------------
# Command registration
# ---------------------------------------------------------------------------


def _make(commands_cfg: dict, name: str, default_description: str, handler) -> Command:
    return Command(
        name=name,
        description=description_from_config(commands_cfg, name, default_description),
        handler=handler,
        enabled=is_enabled_in_config(commands_cfg, name),
    )


def _cmd_command_palette(app: Any) -> CommandResult:
    app.open_command_palette()
    return CommandResult(True, "palette")


def register(app: "SimpleTextEditorApp", registry: CommandRegistry) -> None:
    cfg = app.config_data.get("commands", {})
    registry.register(_make(cfg, "command-palette", "Open the command palette.", _cmd_command_palette))
