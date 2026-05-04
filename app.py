"""Top-level Textual application for the editor.

Scope
-----
Composition root: instantiates feature modules, wires them together via
dependency injection, and runs the lifecycle hooks (load on mount, save on
text change, refresh status on selection change).

Boundaries
----------
- Does NOT implement Vim key dispatch (see `vim.keybindings`).
- Does NOT execute commands directly. Each command is a closure over app
  state, registered against the `CommandRegistry` at startup.
- Does NOT touch the JSON file directly. All disk I/O goes through
  `storage`.
- Does NOT format the status bar inline. The `StatusBar` widget owns
  rendering.
- Does NOT manage panels directly. Panel show/hide/toggle is owned by
  `LayoutManager` in `layout`.

Freeze criteria
--------------
- The editor loads/saves the JSON document on every change.
- Mode transitions and theme changes refresh the status bar.
- Commands are registered exactly once in `_register_commands`. New
  commands plug in there without touching any other module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Header, TextArea

import config as _config_module
from commands import CommandRegistry
from layout import LayoutManager
from modals.command_palette import CommandPaletteScreen
from modals.theme_picker import ThemePickerScreen
from register import Register
from status_bar import StatusBar, StatusSnapshot
from storage import LoadedDocument, StorageError, load, save
from themes import list_themes
from vim.keybindings import VimMode, handle_vim_key
from widgets.files_panel import FileTreePanel


BASE_DIR = _config_module.BASE_DIR


def _load_config() -> tuple[dict[str, Any], list[str]]:
    """Thin wrapper around `config.load_config` so tests can monkeypatch
    `app._load_config` (legacy patch target)."""

    return _config_module.load_config()


# ---------------------------------------------------------------------------
# Vim-aware TextArea.
# ---------------------------------------------------------------------------


class VimTextArea(TextArea):
    """TextArea with Vim-like key handling delegated to a dedicated module."""

    async def _on_key(self, event) -> None:
        app = self.app
        if not isinstance(app, SimpleTextEditorApp):
            await super()._on_key(event)
            return

        if handle_vim_key(app, self, event):
            event.stop()
            event.prevent_default()
            return

        if app.vim_mode == VimMode.INSERT:
            await super()._on_key(event)


# ---------------------------------------------------------------------------
# The application.
# ---------------------------------------------------------------------------


class SimpleTextEditorApp(App):
    """Minimal Textual editor with Vim-like modes, JSON autosave, and panels."""

    TITLE = ""
    SUB_TITLE = ""
    CSS_PATH = "styles.tcss"

    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("ctrl+p", "open_command_palette", "Commands"),
        Binding("ctrl+s", "doc_save", "Save"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    vim_mode = reactive(VimMode.NORMAL)
    status_message = reactive("")

    # ----- construction -------------------------------------------------

    def __init__(self) -> None:
        config, config_warnings = _load_config()
        self.config_data = config
        self._config_warnings = config_warnings

        storage_cfg = self.config_data["storage"]
        editor_cfg = self.config_data["editor"]

        vault_path = BASE_DIR / storage_cfg.get("vault_path", "files")
        self.vault_path = vault_path.resolve()
        self.document_path: Path = (BASE_DIR / storage_cfg["document_path"]).resolve()
        self.auto_save = bool(storage_cfg.get("auto_save", True))

        theme_name = str(editor_cfg.get("theme", "textual-dark"))
        self._initial_theme = theme_name

        self._loaded_pairs: list[tuple[str, str]] = []
        self._loading_document = False
        self._modified = False

        self.command_registry = CommandRegistry()
        self.register = Register()
        self.visual_anchor: tuple[int, int] | None = None
        self.vim_prefix = ""
        self._focused_panel: str = "editor"

        self._layout_manager: LayoutManager | None = None

        super().__init__()
        self.title = self.config_data["app"]["title"]
        self.sub_title = self.config_data["app"]["subtitle"]

    # ----- composition -------------------------------------------------

    def compose(self) -> ComposeResult:
        editor_cfg = self.config_data["editor"]
        with Vertical(id="main"):
            yield Header(show_clock=False)
            with Horizontal(id="workspace"):
                yield VimTextArea(
                    "",
                    id="editor",
                    soft_wrap=bool(editor_cfg.get("soft_wrap", False)),
                    show_line_numbers=bool(editor_cfg.get("show_line_numbers", True)),
                    tab_behavior="indent",
                    placeholder=str(editor_cfg.get("placeholder", "")),
                )
            yield StatusBar(id="status-bar")

    # ----- lifecycle -------------------------------------------------

    def on_mount(self) -> None:
        start_mode_raw = self.config_data["editor"].get("vim_start_mode", "normal")
        try:
            self.vim_mode = VimMode(start_mode_raw)
        except ValueError:
            self.vim_mode = VimMode.NORMAL
            self._config_warnings.append(f"invalid vim_start_mode: {start_mode_raw!r}")

        self.theme = self._initial_theme

        self._setup_layout()
        self._register_commands()
        self._load_document()
        self._refresh_header()
        self._editor().focus()
        self._focused_panel = "editor"
        self._update_panel_borders()
        self.refresh_status()

        if self._config_warnings:
            self.set_status_message("config: " + "; ".join(self._config_warnings))

    def on_focus(self, event) -> None:
        widget_id = getattr(event.widget, "id", None)
        if widget_id in ("editor", "pane-files"):
            self._focused_panel = widget_id
            self._update_panel_borders()

    # ----- layout -----------------------------------------------------

    def _setup_layout(self) -> None:
        panels_cfg = self.config_data.get("panels", {})
        files_visible = bool(panels_cfg.get("files", {}).get("visible_on_start", True))

        workspace = self.query_one("#workspace", Horizontal)
        self._layout_manager = LayoutManager(workspace)

        file_tree = FileTreePanel(self.vault_path)
        from layout import Panel
        self._layout_manager.register(Panel(
            id="pane-files",
            widget=file_tree,
            dock="left",
            initial_visible=files_visible,
            width=30,
        ))

    # ----- editor accessor --------------------------------------------

    def _editor(self) -> VimTextArea:
        return self.query_one("#editor", VimTextArea)

    def _status_bar(self) -> StatusBar:
        return self.query_one("#status-bar", StatusBar)

    def _title_with_path(self) -> str:
        try:
            rel = self.document_path.relative_to(self.vault_path)
            return str(rel) if rel.name else self.document_path.name
        except ValueError:
            return self.document_path.name

    def _refresh_header(self) -> None:
        try:
            header = self.query_one("Header", Header)
            header.title = self._title_with_path()
        except Exception:
            pass

    # ----- status bar -------------------------------------------------

    def refresh_status(self) -> None:
        editor = self._editor()
        row, col = editor.cursor_location
        snapshot = StatusSnapshot(
            mode=str(self.vim_mode),
            file_name=self.document_path.name,
            cursor_line=row + 1,
            cursor_column=col + 1,
            modified=self._modified,
            pending=self.vim_prefix,
            message=self.status_message,
        )
        self._status_bar().set_snapshot(snapshot)

    def set_status_message(self, message: str, transient: bool = False) -> None:
        self.status_message = message
        self.refresh_status()
        if transient:
            self.set_timer(3.0, self._clear_status_message)

    def _clear_status_message(self) -> None:
        self.status_message = ""
        self.refresh_status()

    def _update_panel_borders(self) -> None:
        mode_class = f"active-{str(self.vim_mode).lower()}"
        for panel_id in ("editor", "pane-files"):
            try:
                widget = self.query_one(f"#{panel_id}")
                for cls in list(widget.classes):
                    if cls.startswith("active-"):
                        widget.remove_class(cls)
                if panel_id == self._focused_panel:
                    widget.add_class(mode_class)
            except Exception:
                pass

    # ----- mode transitions -------------------------------------------
    # All mode bookkeeping lives in `vim.modes`. These thin wrappers exist
    # so callers (vim.keybindings, command handlers) can keep using
    # `app.enter_*` without knowing about the internals.

    def enter_normal_mode(self) -> None:
        from vim.modes import enter_normal
        enter_normal(self)

    def enter_insert_mode(self) -> None:
        from vim.modes import enter_insert
        enter_insert(self)

    def enter_visual_mode(self, linewise: bool = False) -> None:
        from vim.modes import enter_visual
        enter_visual(self, linewise=linewise)

    # ----- command palette -------------------------------------------

    def action_open_command_palette(self) -> None:
        self.open_command_palette()

    def open_command_palette(self) -> None:
        self.push_screen(CommandPaletteScreen(self.command_registry), self._apply_command_choice)

    def _apply_command_choice(self, command_name: str | None) -> None:
        self._focused_panel = "editor"
        self._update_panel_borders()
        if command_name is None:
            self.set_status_message("command cancelled")
            return
        result = self.command_registry.execute(self, command_name)
        message = result.message or (f"ran {command_name}" if result.ok else f"failed {command_name}")
        self.set_status_message(message)

    # ----- theme picker ---------------------------------------------

    def open_theme_picker(self) -> None:
        themes = list_themes(self)
        self.push_screen(ThemePickerScreen(themes), self._apply_theme_choice)

    def _apply_theme_choice(self, theme_name: str | None) -> None:
        if theme_name is None:
            self.set_status_message("theme selection cancelled")
            return
        self.theme = theme_name
        self.refresh_status()
        self.set_status_message(f"theme: {theme_name}")

    # ----- command registration --------------------------------------

    def _register_commands(self) -> None:
        """Plug in commands from each feature module.

        Each `features/*.py` exports `register(app, registry)`. To add a
        new command domain, drop a module under `features/` and append it
        to the list below — nothing else in `app.py` needs to change.
        """

        from features import document, hotkey, leader, pane, theme

        for module in (theme, document, pane, hotkey, leader):
            module.register(self, self.command_registry)

    # ----- leader key & file tree helpers ----------------------------

    def open_which_key(self) -> None:
        from modals.which_key import WhichKeyScreen
        self.push_screen(WhichKeyScreen(self), self._on_which_key_dismiss)

    def _on_which_key_dismiss(self, key: str | None) -> None:
        self._focused_panel = "editor"
        self._update_panel_borders()
        if key is None:
            return
        self.leader_dispatch(key)

    def leader_dispatch(self, key: str) -> None:
        from features.leader import dispatch
        dispatch(self, key)

    def _refresh_file_tree(self) -> None:
        try:
            tree = self.query_one("#pane-files", FileTreePanel)
            tree.reload()
        except Exception:
            pass

    # ----- document persistence --------------------------------------

    def _load_document(self) -> None:
        self._loading_document = True
        editor = self._editor()
        try:
            doc: LoadedDocument = load(self.document_path)
            editor.text = doc.text
            self._loaded_pairs = list(zip(
                doc.text.split("\n") if doc.text else [],
                doc.line_ids,
                strict=False,
            ))
            self._modified = False
        except Exception as exc:  # pragma: no cover - defensive
            editor.text = ""
            self._loaded_pairs = []
            self._modified = False
            self.set_status_message(f"load failed: {exc}")
        finally:
            self._loading_document = False

    def save_document(self, force: bool = False) -> str:
        if not self.auto_save and not force:
            return "auto-save disabled"
        editor = self._editor()
        try:
            new_ids = save(self.document_path, editor.text, self._loaded_pairs)
        except StorageError as exc:
            return f"save failed: {exc}"
        new_lines = [] if editor.text == "" else editor.text.split("\n")
        self._loaded_pairs = list(zip(new_lines, new_ids, strict=False))
        self._modified = False
        self.refresh_status()
        return "saved"

    def open_document(self, path: Path) -> None:
        if path == self.document_path:
            return
        if self._modified:
            msg = self.save_document(force=True)
            if msg != "saved":
                self.set_status_message(f"save first: {msg}")
                return
        self.document_path = path.resolve()
        self._refresh_header()
        self._load_document()
        self.refresh_status()
        self.set_status_message(f"opened {path.name}")

    # ----- text-area events -----------------------------------------

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if event.text_area.id != "editor" or self._loading_document:
            return
        self._modified = True
        if self.auto_save:
            message = self.save_document()
            if message != "saved":
                self.set_status_message(message)
        self.refresh_status()

    def on_text_area_selection_changed(self, event: TextArea.SelectionChanged) -> None:
        if event.text_area.id == "editor":
            self.refresh_status()

    # ----- file tree panel events -----------------------------------

    def on_file_tree_panel_document_selected(self, event: FileTreePanel.DocumentSelected) -> None:
        self.open_document(event.path)


if __name__ == "__main__":
    SimpleTextEditorApp().run()