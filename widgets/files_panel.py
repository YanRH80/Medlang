"""Left panel: directory tree of the JSON document vault.

Scope
-----
Subclasses DirectoryTree to show only .json files inside the vault
directory. When the user selects a file, posts a `DocumentSelected`
message. The caller (the app) decides whether to save first and what
to do with the loaded text.

Boundaries
----------
- Does NOT load the document itself.
- Does NOT mutate disk (read-only tree).
- Does NOT track unsaved-changes state.
- Does NOT handle nested directories; vault is flat (one level, .json only).

Freeze criteria
--------------
- Tree loads vault_path on mount and shows only .json files.
- `DocumentSelected` fires exactly once per user click on a .json file.
- Clicking the same file that's already open is a no-op (handled by caller).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from textual.events import Key
from textual.widgets import DirectoryTree

from messages import DocumentSelected


class FileTreePanel(DirectoryTree, can_focus=True):
    BORDER_TITLE = "Files"

    # Re-export so existing `FileTreePanel.DocumentSelected` references keep
    # working through the migration. The canonical message lives in
    # `messages.py`.
    DocumentSelected = DocumentSelected

    def __init__(self, vault_path: Path, *, name: str | None = None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(str(vault_path), name=name, id=id, classes=classes)

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        for path in paths:
            if path.is_dir():
                yield path
            elif path.is_file() and path.suffix == ".json":
                yield path

    def on_key(self, event: Key) -> None:
        key = event.key
        if key == "space":
            event.stop()
            app = self.app
            if hasattr(app, "open_which_key"):
                app.open_which_key()
            return
        if key in ("j", "k"):
            event.stop()
            node = self.cursor_node
            if not node:
                return
            if key == "j":
                if node == self.root and node.children:
                    self.select_node(node.children[0])
                elif node.parent and node.parent.children:
                    idx = node.parent.children.index(node)
                    if idx < len(node.parent.children) - 1:
                        self.select_node(node.parent.children[idx + 1])
            elif key == "k":
                if node.parent and node.parent != self.root:
                    self.select_node(node.parent)
                elif node.parent == self.root and self.root.children:
                    idx = self.root.children.index(node) if node in self.root.children else -1
                    if idx > 0:
                        self.select_node(self.root.children[idx - 1])

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        event.stop()
        self.post_message(self.DocumentSelected(event.path))