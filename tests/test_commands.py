"""Tests for the pluggable CommandRegistry."""

from __future__ import annotations

from editor_commands import (
    Command,
    CommandRegistry,
    CommandResult,
    description_from_config,
    is_enabled_in_config,
)


def _ok_handler(message: str = "ran"):
    return lambda app: CommandResult(True, message)


# ---------------------------------------------------------------------------
# Registration.
# ---------------------------------------------------------------------------


def test_registry_starts_empty() -> None:
    r = CommandRegistry()
    assert r.command_names() == []
    assert r.fuzzy_find("") == []


def test_register_then_lookup() -> None:
    r = CommandRegistry()
    r.register(Command("foo", "Do foo", _ok_handler()))
    assert r.command_names() == ["foo"]
    assert r.is_enabled("foo")
    assert r.description("foo") == "Do foo"


def test_register_replaces_same_name() -> None:
    r = CommandRegistry()
    r.register(Command("foo", "first", _ok_handler()))
    r.register(Command("foo", "second", _ok_handler()))
    assert r.description("foo") == "second"


def test_disabled_command_hidden_from_listings() -> None:
    r = CommandRegistry()
    r.register(Command("foo", "x", _ok_handler(), enabled=False))
    r.register(Command("bar", "y", _ok_handler()))
    assert r.command_names() == ["bar"]
    assert "foo" not in r.fuzzy_find("foo")


def test_unregister() -> None:
    r = CommandRegistry()
    r.register(Command("foo", "x", _ok_handler()))
    r.unregister("foo")
    assert r.command_names() == []
    r.unregister("never-existed")  # no-op


# ---------------------------------------------------------------------------
# Fuzzy find.
# ---------------------------------------------------------------------------


def test_fuzzy_find_empty_query_returns_all() -> None:
    r = CommandRegistry()
    r.register(Command("alpha", "a", _ok_handler()))
    r.register(Command("beta", "b", _ok_handler()))
    assert r.fuzzy_find("") == ["alpha", "beta"]


def test_fuzzy_find_prefers_prefix_match() -> None:
    r = CommandRegistry()
    r.register(Command("light-dark-mode", "Switch theme", _ok_handler()))
    r.register(Command("palette", "Color picker", _ok_handler()))
    assert r.fuzzy_find("lig")[0] == "light-dark-mode"


def test_fuzzy_find_matches_substring() -> None:
    r = CommandRegistry()
    r.register(Command("light-dark-mode", "Switch theme", _ok_handler()))
    r.register(Command("palette", "Color picker", _ok_handler()))
    assert r.fuzzy_find("dark")[0] == "light-dark-mode"


def test_fuzzy_find_no_match_returns_empty() -> None:
    r = CommandRegistry()
    r.register(Command("alpha", "a", _ok_handler()))
    assert r.fuzzy_find("zzz") == []


def test_fuzzy_find_respects_limit() -> None:
    r = CommandRegistry()
    for i in range(10):
        r.register(Command(f"cmd{i}", f"desc{i}", _ok_handler()))
    assert len(r.fuzzy_find("cmd", limit=3)) == 3


# ---------------------------------------------------------------------------
# Execute.
# ---------------------------------------------------------------------------


def test_execute_runs_handler() -> None:
    r = CommandRegistry()
    r.register(Command("foo", "x", _ok_handler("done")))
    result = r.execute(None, "foo")
    assert result == CommandResult(True, "done")


def test_execute_unknown_returns_failure() -> None:
    r = CommandRegistry()
    result = r.execute(None, "missing")
    assert not result.ok
    assert "unknown" in result.message


def test_execute_empty_returns_failure() -> None:
    r = CommandRegistry()
    result = r.execute(None, "")
    assert not result.ok
    assert "empty" in result.message


def test_execute_disabled_returns_failure() -> None:
    r = CommandRegistry()
    r.register(Command("foo", "x", _ok_handler(), enabled=False))
    result = r.execute(None, "foo")
    assert not result.ok
    assert "disabled" in result.message


def test_execute_resolves_unique_fuzzy_match() -> None:
    r = CommandRegistry()
    r.register(Command("light-dark-mode", "x", _ok_handler("toggled")))
    r.register(Command("palette", "y", _ok_handler()))
    result = r.execute(None, "lig")
    assert result == CommandResult(True, "toggled")


def test_execute_ambiguous_match_reports_options() -> None:
    r = CommandRegistry()
    r.register(Command("alpha", "x", _ok_handler()))
    r.register(Command("alphabet", "y", _ok_handler()))
    result = r.execute(None, "alp")
    assert not result.ok
    assert "alpha" in result.message


def test_execute_handler_exception_returns_failure() -> None:
    def boom(app):
        raise RuntimeError("kaboom")

    r = CommandRegistry()
    r.register(Command("crash", "x", boom))
    result = r.execute(None, "crash")
    assert not result.ok
    assert "kaboom" in result.message


# ---------------------------------------------------------------------------
# Config helpers.
# ---------------------------------------------------------------------------


def test_is_enabled_defaults_true() -> None:
    assert is_enabled_in_config({}, "missing") is True


def test_is_enabled_reads_explicit_false() -> None:
    cfg = {"foo": {"enabled": False}}
    assert is_enabled_in_config(cfg, "foo") is False


def test_description_from_config_uses_value() -> None:
    cfg = {"foo": {"description": "Hello"}}
    assert description_from_config(cfg, "foo", "fallback") == "Hello"


def test_description_from_config_falls_back() -> None:
    assert description_from_config({}, "foo", "fallback") == "fallback"
    assert description_from_config({"foo": {}}, "foo", "fallback") == "fallback"
