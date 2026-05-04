"""Unit tests for `features.leader.LEADER_MAP` and `dispatch`."""

from __future__ import annotations

from unittest.mock import MagicMock

from features.leader import LEADER_MAP, dispatch


def test_leader_map_contains_expected_keys() -> None:
    # j/k are reserved for vertical splits; they currently emit a
    # "not yet implemented" status message but stay registered.
    expected = {"n", "o", "s", "d", "p", "b", "h", "j", "k", "l", "?"}
    assert set(LEADER_MAP.keys()) == expected


def test_leader_map_values_are_callables() -> None:
    for key, handler in LEADER_MAP.items():
        assert callable(handler), f"{key!r} handler is not callable"


def test_dispatch_unknown_key_is_noop() -> None:
    app = MagicMock()
    # Should not raise even for keys not in LEADER_MAP.
    dispatch(app, "z")
    # No command got executed
    app.command_registry.execute.assert_not_called()


def test_dispatch_p_opens_command_palette() -> None:
    app = MagicMock()
    dispatch(app, "p")
    app.open_command_palette.assert_called_once()


def test_dispatch_n_runs_doc_new_command() -> None:
    app = MagicMock()
    app.command_registry.execute.return_value = MagicMock(message="ok")
    dispatch(app, "n")
    args = app.command_registry.execute.call_args[0]
    assert args[1] == "doc-new"


def test_dispatch_j_emits_pending_vertical_message() -> None:
    app = MagicMock()
    dispatch(app, "j")
    app.set_status_message.assert_called_once()
    msg = app.set_status_message.call_args[0][0]
    assert "vertical" in msg.lower() or "not yet" in msg.lower()


def test_dispatch_k_emits_pending_vertical_message() -> None:
    app = MagicMock()
    dispatch(app, "k")
    app.set_status_message.assert_called_once()
