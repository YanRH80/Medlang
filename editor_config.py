"""Hotkey configuration management.

Scope
-----
Loads hotkey bindings from `config.yaml`, exposes them to the app for
dynamic Binding construction, and saves changes back to disk. The app
reads its BINDINGS from this module at startup rather than hardcoding them.

Boundaries
----------
- Does NOT import from `app.py` (avoids circular dependency).
- Does NOT know about Vim key handling (that lives in `editor_keybindings`).
- All disk I/O goes through `yaml` (no new storage mechanism).

Freeze criteria
--------------
- `load_hotkeys()` reads `config.yaml` and returns a flat list of
  `(action_name, key_combo)` tuples that the app converts to Textual
  `Binding` objects.
- `save_hotkeys()` writes back to `config.yaml` preserving all other keys.
- Unknown key combos are rejected with a clear error.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"

# Textual Binding key syntax: ctrl+xxx, shift+xxx, alt+xxx, super+xxx
# Plus combos: ctrl+shift+x, ctrl+a, etc.
_VALID_MODIFIERS = frozenset({"ctrl", "shift", "alt", "super"})
_VALID_KEY_RE = re.compile(r"^[a-z0-9]$")


@dataclass(frozen=True)
class Hotkey:
    """A single key combination bound to an action."""

    action: str
    keys: tuple[str, ...]  # e.g. ("ctrl+p",) or ("super+h", "super+l")


def _parse_key_combo(raw: str) -> tuple[str, ...]:
    """Parse a key combo string like 'ctrl+p' into a tuple ('ctrl+p',).

    Supports single keys and 2-key combos (e.g. 'ctrl+shift+p').
    Rejects invalid modifiers or non-alphanumeric key names.
    """
    raw = raw.strip().lower()
    parts = raw.split("+")
    if not parts or all(p in _VALID_MODIFIERS for p in parts):
        raise ValueError(f"invalid key combo: {raw!r}")
    key = parts[-1]
    if len(parts) == 1:
        if not _VALID_KEY_RE.match(key):
            raise ValueError(f"invalid key name: {key!r}")
        return (raw,)
    modifiers = frozenset(parts[:-1])
    if not modifiers.issubset(_VALID_MODIFIERS):
        raise ValueError(f"invalid modifiers in: {raw!r}")
    if not _VALID_KEY_RE.match(key):
        raise ValueError(f"invalid key name: {key!r}")
    return (raw,)


def _load_yaml() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return yaml.safe_load(CONFIG_PATH.read_text()) or {}
    except yaml.YAMLError:
        return {}


def _save_yaml(data: dict) -> None:
    CONFIG_PATH.write_text(yaml.safe_dump(data, sort_keys=False))


def load_hotkeys() -> list[Hotkey]:
    """Load hotkey bindings from config.yaml.

    Reads `commands[name].hotkeys[]` entries. Each entry is a string like
    'ctrl+p' or 'super+h'. Returns a flat list of Hotkey objects.
    Skips commands with no hotkeys list or with invalid entries.
    """
    cfg = _load_yaml()
    commands = cfg.get("commands", {})
    if not isinstance(commands, dict):
        return []
    result: list[Hotkey] = []
    for action, meta in commands.items():
        if not isinstance(meta, dict):
            continue
        raw_keys = meta.get("hotkeys", [])
        if not isinstance(raw_keys, list):
            continue
        for raw in raw_keys:
            if not isinstance(raw, str):
                continue
            try:
                combo = _parse_key_combo(raw)
                result.append(Hotkey(action=action, keys=combo))
            except ValueError:
                continue
    return result


def save_hotkeys(hotkeys: list[Hotkey]) -> list[str]:
    """Save hotkey bindings back to config.yaml.

    Merges hotkeys into existing config, preserving all other keys.
    Returns a list of warning strings for duplicate bindings.
    """
    cfg = _load_yaml()
    commands = cfg.setdefault("commands", {})
    action_keys: dict[str, list[str]] = {}
    warnings: list[str] = []
    for hk in hotkeys:
        if hk.action in action_keys:
            warnings.append(f"duplicate hotkey action (kept last): {hk.action}")
        action_keys[hk.action] = list(hk.keys)
    for action, keys in action_keys.items():
        if isinstance(commands.get(action), dict):
            commands[action]["hotkeys"] = keys
        else:
            commands[action] = {"enabled": True, "description": "", "hotkeys": keys}
    _save_yaml(cfg)
    return warnings