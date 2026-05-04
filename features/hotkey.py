"""Hotkey commands (display, set).

Scope
-----
- `hotkeys` — display all current bindings (built-in + config).
- `hotkey-set` — open the modal, parse `<action> <key-combo>`, persist
  to `config.yaml` via `hotkey_config.save_hotkeys`.

Boundaries
----------
- Does NOT change runtime BINDINGS. Textual's `BINDINGS` is processed
  at App `__init__`, not editable later. Saved hotkeys take effect on
  next launch.
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
from hotkey_config import Hotkey, load_hotkeys, save_hotkeys

if TYPE_CHECKING:
    from app import SimpleTextEditorApp


def _make(commands_cfg: dict, name: str, default_description: str, handler) -> Command:
    return Command(
        name=name,
        description=description_from_config(commands_cfg, name, default_description),
        handler=handler,
        enabled=is_enabled_in_config(commands_cfg, name),
    )


def _cmd_hotkeys(app: Any) -> CommandResult:
    rows = ["Hotkeys:", "---------"]
    for b in app.BINDINGS:
        display = getattr(b, "display", "") or ""
        if display:
            rows.append(f"  {b.key} → {display}")
        else:
            rows.append(f"  {b.key}")
    for hk in load_hotkeys():
        for key in hk.keys:
            rows.append(f"  {key} → {hk.action}  (config)")
    return CommandResult(True, "\n".join(rows[:15]))


def _cmd_hotkey_set(app: Any) -> CommandResult:
    from modals.hotkey_set import HotkeySetScreen

    def _on_dismiss(result: tuple[str, str] | None) -> None:
        if not result:
            app.set_status_message("hotkey set cancelled")
            return
        action_name, key_combo = result
        try:
            hotkeys = load_hotkeys()
            new_hk = Hotkey(action=action_name, keys=(key_combo,))
            hotkeys = [h for h in hotkeys if h.action != action_name]
            hotkeys.append(new_hk)
            save_hotkeys(hotkeys)
            app.set_status_message(f"hotkey set: {key_combo} → {action_name}")
        except Exception as exc:
            app.set_status_message(f"hotkey set failed: {exc}")

    app.push_screen(HotkeySetScreen(), _on_dismiss)
    return CommandResult(True, "hotkey set opened")


def register(app: "SimpleTextEditorApp", registry: CommandRegistry) -> None:
    cfg = app.config_data.get("commands", {})
    registry.register(_make(cfg, "hotkeys", "Show all current hotkey bindings.", _cmd_hotkeys))
    registry.register(_make(cfg, "hotkey-set", "Set a hotkey: hotkey-set <action> <key-combo>.", _cmd_hotkey_set))
