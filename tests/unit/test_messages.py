"""Unit tests for centralised Textual messages."""

from __future__ import annotations

from pathlib import Path

from messages import DocumentSelected
from widgets.files_panel import FileTreePanel


def test_document_selected_carries_path() -> None:
    p = Path("/tmp/example.json")
    msg = DocumentSelected(p)
    assert msg.path == p


def test_files_panel_reexports_message() -> None:
    # Backwards-compat alias: `FileTreePanel.DocumentSelected` is the same
    # class as `messages.DocumentSelected`.
    assert FileTreePanel.DocumentSelected is DocumentSelected
