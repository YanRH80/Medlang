"""Configuration loading and validation.

Scope
-----
Owns the on-disk YAML config schema, defaults, deep-merge logic and
validation warnings. The app calls `load_config()` at startup and uses
the returned dict; nothing else in the codebase reads `config.yaml`
directly.

Boundaries
----------
- Does NOT depend on Textual or any UI module.
- Does NOT mutate the loaded YAML — returns a new merged dict.
- Does NOT enforce schema beyond key presence + value types.

Freeze criteria
---------------
- `load_config()` returns `(config_dict, warnings)` even when
  `config.yaml` is missing or malformed.
- Unknown keys yield warnings, never crash.
- New top-level sections require an entry in `DEFAULT_CONFIG` plus an
  entry in the corresponding `_KNOWN_*` set.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "app": {
        "title": "Medlang",
        "subtitle": "Vim-like JSON editor",
    },
    "editor": {
        "placeholder": "Modo NORMAL. Pulsa i para escribir, : para comandos.",
        "soft_wrap": False,
        "show_line_numbers": True,
        "vim_start_mode": "normal",
        "theme": "textual-dark",
    },
    "storage": {
        "vault_path": "files",
        "document_path": "files/document.json",
        "auto_save": True,
    },
    "panels": {
        "files": {
            "visible_on_start": True,
        },
    },
    "commands": {
        "theme-toggle": {
            "enabled": True,
            "description": "Toggle between dark and light theme.",
            "hotkeys": [],
        },
        "theme-pick": {
            "enabled": True,
            "description": "Open the theme picker.",
            "hotkeys": [],
        },
        "doc-rename": {
            "enabled": True,
            "description": "Rename the current JSON document.",
            "hotkeys": [],
        },
        "doc-save": {
            "enabled": True,
            "description": "Force-save the document now.",
            "hotkeys": [],
        },
        "pane-files-toggle": {
            "enabled": True,
            "description": "Toggle the file panel visibility.",
            "hotkeys": [],
        },
        "pane-focus-files": {
            "enabled": True,
            "description": "Focus the file panel.",
            "hotkeys": [],
        },
        "pane-focus-editor": {
            "enabled": True,
            "description": "Focus the editor.",
            "hotkeys": [],
        },
        "doc-new": {
            "enabled": True,
            "description": "Create a new JSON document.",
            "hotkeys": [],
        },
        "doc-open": {
            "enabled": True,
            "description": "Open a document from the vault.",
            "hotkeys": [],
        },
    },
}


_KNOWN_TOP_LEVEL_KEYS = set(DEFAULT_CONFIG.keys())
_KNOWN_EDITOR_KEYS = set(DEFAULT_CONFIG["editor"].keys())
_KNOWN_STORAGE_KEYS = set(DEFAULT_CONFIG["storage"].keys())
_KNOWN_PANEL_KEYS = set(DEFAULT_CONFIG["panels"].keys())


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge `override` on top of `base` without mutating either."""

    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _validate_config(cfg: dict[str, Any]) -> list[str]:
    """Return human-readable warnings for unexpected keys or types."""

    warnings: list[str] = []

    for key in cfg:
        if key not in _KNOWN_TOP_LEVEL_KEYS:
            warnings.append(f"unknown config section: {key!r}")

    editor = cfg.get("editor", {})
    if isinstance(editor, dict):
        for key in editor:
            if key not in _KNOWN_EDITOR_KEYS:
                warnings.append(f"unknown editor.{key}")

    storage = cfg.get("storage", {})
    if isinstance(storage, dict):
        for key in storage:
            if key not in _KNOWN_STORAGE_KEYS:
                warnings.append(f"unknown storage.{key}")

    panels = cfg.get("panels", {})
    if isinstance(panels, dict):
        for key in panels:
            if key not in _KNOWN_PANEL_KEYS:
                warnings.append(f"unknown panels.{key}")

    return warnings


def load_config() -> tuple[dict[str, Any], list[str]]:
    """Load config.yaml. Returns (config_dict, warnings)."""

    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG, []

    try:
        loaded = yaml.safe_load(CONFIG_PATH.read_text())
    except yaml.YAMLError as exc:
        return DEFAULT_CONFIG, [f"config.yaml malformed: {exc}"]

    if not isinstance(loaded, dict):
        return DEFAULT_CONFIG, ["config.yaml must be a mapping; using defaults"]

    warnings = _validate_config(loaded)
    return _deep_merge(DEFAULT_CONFIG, loaded), warnings
