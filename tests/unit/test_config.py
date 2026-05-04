"""Tests for the configuration module (deep_merge, load_config, validate)."""

from __future__ import annotations

from pathlib import Path

import pytest

import config as config_module


# ---------------------------------------------------------------------------
# _deep_merge
# ---------------------------------------------------------------------------


def test_deep_merge_overrides_top_level() -> None:
    base = {"a": 1, "b": 2}
    out = config_module._deep_merge(base, {"a": 10})
    assert out == {"a": 10, "b": 2}
    # base must not be mutated.
    assert base == {"a": 1, "b": 2}


def test_deep_merge_recurses_into_dicts() -> None:
    base = {"editor": {"placeholder": "x", "wrap": True}}
    override = {"editor": {"placeholder": "y"}}
    out = config_module._deep_merge(base, override)
    assert out == {"editor": {"placeholder": "y", "wrap": True}}


def test_deep_merge_replaces_with_non_dict() -> None:
    base = {"a": {"x": 1}}
    out = config_module._deep_merge(base, {"a": "string"})
    assert out == {"a": "string"}


# ---------------------------------------------------------------------------
# _validate_config
# ---------------------------------------------------------------------------


def test_validate_config_clean_yields_no_warnings() -> None:
    cfg = {
        "app": {"title": "x"},
        "editor": {"theme": "textual-dark"},
        "storage": {"document_path": "x.json"},
        "commands": {},
    }
    assert config_module._validate_config(cfg) == []


def test_validate_config_flags_unknown_top_level() -> None:
    cfg = {"unknown_section": {}}
    warnings = config_module._validate_config(cfg)
    assert any("unknown_section" in w for w in warnings)


def test_validate_config_flags_unknown_editor_key() -> None:
    cfg = {"editor": {"weird_key": True}}
    warnings = config_module._validate_config(cfg)
    assert any("weird_key" in w for w in warnings)


def test_validate_config_flags_unknown_storage_key() -> None:
    cfg = {"storage": {"weird_key": True}}
    warnings = config_module._validate_config(cfg)
    assert any("weird_key" in w for w in warnings)


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


def test_load_config_uses_defaults_when_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "absent.yaml")
    cfg, warnings = config_module.load_config()
    assert cfg == config_module.DEFAULT_CONFIG
    assert warnings == []


def test_load_config_merges_user_yaml(tmp_path: Path, monkeypatch) -> None:
    p = tmp_path / "config.yaml"
    p.write_text("editor:\n  theme: tokyo-night\n")
    monkeypatch.setattr(config_module, "CONFIG_PATH", p)
    cfg, warnings = config_module.load_config()
    assert cfg["editor"]["theme"] == "tokyo-night"
    assert cfg["editor"]["vim_start_mode"] == "normal"
    assert warnings == []


def test_load_config_handles_yaml_error(tmp_path: Path, monkeypatch) -> None:
    p = tmp_path / "broken.yaml"
    p.write_text("editor: : :\n")
    monkeypatch.setattr(config_module, "CONFIG_PATH", p)
    cfg, warnings = config_module.load_config()
    assert cfg == config_module.DEFAULT_CONFIG
    assert any("malformed" in w for w in warnings)


def test_load_config_handles_non_mapping(tmp_path: Path, monkeypatch) -> None:
    p = tmp_path / "list.yaml"
    p.write_text("- 1\n- 2\n")
    monkeypatch.setattr(config_module, "CONFIG_PATH", p)
    cfg, warnings = config_module.load_config()
    assert cfg == config_module.DEFAULT_CONFIG
    assert warnings  # has warning


def test_load_config_emits_warning_on_unknown_key(tmp_path: Path, monkeypatch) -> None:
    p = tmp_path / "config.yaml"
    p.write_text("editor:\n  bogus: 1\n")
    monkeypatch.setattr(config_module, "CONFIG_PATH", p)
    cfg, warnings = config_module.load_config()
    assert any("bogus" in w for w in warnings)
