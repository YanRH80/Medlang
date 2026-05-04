"""Document commands (new, open, save, rename, delete).

Scope
-----
Registers all `doc-*` commands. Each handler opens a modal (when the
operation needs user input) and on dismiss mutates the app's
`document_path` via `app.open_document` / `app.save_document` /
`storage.rename`.

Boundaries
----------
- Does NOT touch disk directly except through `storage` module.
- Does NOT own modals — they live in `modals/`.
- `app.save_document`, `app.open_document`, `app._refresh_file_tree`
  remain on the App because they manage long-lived editor state.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from commands import (
    Command,
    CommandRegistry,
    CommandResult,
    description_from_config,
    is_enabled_in_config,
)
from storage import StorageError, list_documents, rename, save

if TYPE_CHECKING:
    from app import SimpleTextEditorApp


def _make(commands_cfg: dict, name: str, default_description: str, handler) -> Command:
    return Command(
        name=name,
        description=description_from_config(commands_cfg, name, default_description),
        handler=handler,
        enabled=is_enabled_in_config(commands_cfg, name),
    )


def _cmd_save(app: Any) -> CommandResult:
    return CommandResult(True, app.save_document(force=True))


def _cmd_doc_new(app: Any) -> CommandResult:
    from modals.new_doc import NewDocScreen

    def _on_dismiss(name: str | None) -> None:
        if not name:
            app.set_status_message("new document cancelled")
            return
        if not name.endswith(".json"):
            name += ".json"
        new_path = app.vault_path / name
        if new_path.exists():
            app.set_status_message(f"file already exists: {name}")
            return
        try:
            save(new_path, "", [])
        except StorageError as exc:
            app.set_status_message(f"create failed: {exc}")
            return
        app.open_document(new_path)
        app._refresh_file_tree()
        app._focused_panel = "editor"
        app._update_panel_borders()

    app.push_screen(NewDocScreen(), _on_dismiss)
    return CommandResult(True, "new document opened")


def _cmd_doc_open(app: Any) -> CommandResult:
    from modals.doc_picker import DocPickerScreen

    docs = list_documents(app.vault_path)

    def _on_dismiss(path_str: str | None) -> None:
        if not path_str:
            app.set_status_message("open cancelled")
            return
        app.open_document(Path(path_str))
        app._refresh_file_tree()
        app._focused_panel = "editor"
        app._update_panel_borders()

    app.push_screen(DocPickerScreen(docs), _on_dismiss)
    return CommandResult(True, "doc picker opened")


def _cmd_doc_rename(app: Any) -> CommandResult:
    from modals.rename import RenamePromptScreen

    def _on_dismiss(new_name: str | None) -> None:
        if not new_name:
            app.set_status_message("rename cancelled")
            return
        try:
            new_path = rename(app.document_path, new_name)
        except StorageError as exc:
            app.set_status_message(f"rename failed: {exc}")
            return
        app.document_path = new_path
        app.set_status_message(f"renamed to {new_path.name}")

    app.push_screen(RenamePromptScreen(app.document_path.name), _on_dismiss)
    return CommandResult(True, "rename prompt opened")


def _cmd_doc_delete(app: Any) -> CommandResult:
    from modals.doc_picker import DocPickerScreen

    docs = [p for p in list_documents(app.vault_path) if p != app.document_path]
    if not docs:
        return CommandResult(False, "cannot delete: no other documents")

    def _on_dismiss(path_str: str | None) -> None:
        if not path_str:
            app.set_status_message("delete cancelled")
            return
        if app.document_path.exists():
            app.document_path.unlink()
        app.open_document(Path(path_str))
        app._refresh_file_tree()
        app._focused_panel = "editor"
        app._update_panel_borders()

    app.push_screen(DocPickerScreen(docs), _on_dismiss)
    return CommandResult(True, "delete: select replacement doc")


def register(app: "SimpleTextEditorApp", registry: CommandRegistry) -> None:
    cfg = app.config_data.get("commands", {})
    registry.register(_make(cfg, "doc-save", "Force-save the document now.", _cmd_save))
    registry.register(_make(cfg, "doc-new", "Create a new JSON document.", _cmd_doc_new))
    registry.register(_make(cfg, "doc-open", "Open a document from the vault.", _cmd_doc_open))
    registry.register(_make(cfg, "doc-rename", "Rename the current JSON document.", _cmd_doc_rename))
    registry.register(_make(cfg, "doc-delete", "Delete the current document.", _cmd_doc_delete))
