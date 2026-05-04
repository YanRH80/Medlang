"""Unit tests for `layout.LayoutManager`."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from layout import LayoutManager, Panel


@pytest.fixture
def host_and_panel():
    """Provide a fake host container and a fake widget for panel tests."""

    host = MagicMock()
    widget = MagicMock()
    widget.id = None
    widget.styles = MagicMock()
    panel = Panel(id="files", widget=widget, dock="left", initial_visible=True, width=30)
    return host, panel


def test_register_mounts_widget_with_visibility(host_and_panel) -> None:
    host, panel = host_and_panel
    lm = LayoutManager(host)
    lm.register(panel)
    host.mount.assert_called_once_with(panel.widget)
    assert lm.is_visible("files") is True


def test_show_hide_toggle_round_trip(host_and_panel) -> None:
    host, panel = host_and_panel
    lm = LayoutManager(host)
    lm.register(panel)

    panel.widget.styles.display = "block"
    assert lm.is_visible("files") is True

    lm.hide("files")
    panel.widget.styles.display = "none"
    assert lm.is_visible("files") is False

    lm.show("files")
    panel.widget.styles.display = "block"
    assert lm.is_visible("files") is True


def test_toggle_returns_new_visibility(host_and_panel) -> None:
    host, panel = host_and_panel
    lm = LayoutManager(host)
    lm.register(panel)

    panel.widget.styles.display = "block"
    new_visible = lm.toggle("files")
    panel.widget.styles.display = "none" if not new_visible else "block"
    assert new_visible is False


def test_unknown_panel_ops_are_noop() -> None:
    host = MagicMock()
    lm = LayoutManager(host)
    # Should not raise.
    lm.show("absent")
    lm.hide("absent")
    assert lm.toggle("absent") is False
    assert lm.is_visible("absent") is False


def test_initial_visible_false_renders_hidden() -> None:
    host = MagicMock()
    widget = MagicMock()
    widget.styles = MagicMock()
    panel = Panel(id="x", widget=widget, dock="left", initial_visible=False, width=20)
    lm = LayoutManager(host)
    lm.register(panel)
    # Display set on register
    assert widget.styles.display == "none"
