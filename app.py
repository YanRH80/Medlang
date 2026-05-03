"""Top-level Textual application for the editor.

Scope
-----
Composition root: instantiates feature modules, wires them together via
dependency injection, and runs the lifecycle hooks (load on mount, save on
text change, refresh status on selection change).

Boundaries
----------
- Does NOT implement Vim key dispatch (see `editor_keybindings`).
- Does NOT execute commands directly. Each command is a closure over app
  state, registered against the `CommandRegistry` at startup.
- Does NOT touch the JSON file directly. All disk I/O goes through
  `editor_storage`.
- Does NOT format the status bar inline. The `StatusBar` widget owns
  rendering.
- Does NOT manage panels directly. Panel show/hide/toggle is owned by
  `LayoutManager` in `editor_layout`.

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

import yaml
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, TextArea
from textual.widgets.text_area import Selection

from editor_command_palette import CommandPaletteScreen
from editor_commands import (
    Command,
    CommandRegistry,
    CommandResult,
    description_from_config,
    is_enabled_in_config,
)
from editor_keybindings import VimMode, handle_vim_key
from editor_layout import LayoutManager
from editor_panel_files import FileTreePanel
from editor_register import Register
from editor_status import StatusBar, StatusSnapshot
from editor_storage import LoadedDocument, StorageError, load, save, list_documents, rename
from editor_styles import EDITOR_CSS
from editor_theme_picker import ThemePickerScreen
from editor_themes import list_themes, toggle_light_dark, current_theme_name
from editor_config import load_hotkeys, save_hotkeys, Hotkey


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "app": {
        "title": "Editor simple",
        "subtitle": "Vim-like + JSON",
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
        "pane-files-show": {
            "enabled": True,
            "description": "Show the file panel.",
            "hotkeys": [],
        },
        "pane-files-hide": {
            "enabled": True,
            "description": "Hide the file panel.",
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
        "pane-focus-up": {
            "enabled": True,
            "description": "Focus the panel above.",
            "hotkeys": [],
        },
        "pane-focus-down": {
            "enabled": True,
            "description": "Focus the panel below.",
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


# ---------------------------------------------------------------------------
# Configuration loading and validation.
# ---------------------------------------------------------------------------


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge `override` on top of `base` without mutating either."""

    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_config() -> tuple[dict[str, Any], list[str]]:
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
    CSS = EDITOR_CSS

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
        from editor_layout import Panel
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

    def enter_normal_mode(self) -> None:
        editor = self._editor()
        editor.selection = Selection.cursor(editor.cursor_location)
        self.visual_anchor = None
        self.vim_prefix = ""
        self.vim_mode = VimMode.NORMAL
        self.refresh_status()
        self._update_panel_borders()

    def enter_insert_mode(self) -> None:
        self.visual_anchor = None
        self.vim_prefix = ""
        self.vim_mode = VimMode.INSERT
        self.refresh_status()
        self._update_panel_borders()

    def enter_visual_mode(self, linewise: bool = False) -> None:
        editor = self._editor()
        self.visual_anchor = editor.cursor_location
        self.vim_prefix = ""
        self.vim_mode = VimMode.VISUAL_LINE if linewise else VimMode.VISUAL
        if linewise:
            row, _ = editor.cursor_location
            editor.selection = Selection((row, 0), (row, len(editor.document[row])))
        else:
            editor.selection = Selection.cursor(editor.cursor_location)
        self.refresh_status()
        self._update_panel_borders()

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

    def _cmd_doc_delete(self, app: Any) -> CommandResult:
        from editor_doc_picker import DocPickerScreen

        docs = [p for p in list_documents(self.vault_path) if p != self.document_path]
        if not docs:
            return CommandResult(False, "cannot delete: no other documents")

        def _on_dismiss(path_str: str | None) -> None:
            if not path_str:
                self.set_status_message("delete cancelled")
                return
            if self.document_path.exists():
                self.document_path.unlink()
            self.open_document(Path(path_str))
            self._refresh_file_tree()
            self._focused_panel = "editor"
            self._update_panel_borders()

        self.push_screen(DocPickerScreen(docs), _on_dismiss)
        return CommandResult(True, "delete: select replacement doc")

    # ----- command registration --------------------------------------

    def _register_commands(self) -> None:
        commands_cfg = self.config_data.get("commands", {})

        def make(name: str, default_description: str, handler) -> Command:
            return Command(
                name=name,
                description=description_from_config(commands_cfg, name, default_description),
                handler=handler,
                enabled=is_enabled_in_config(commands_cfg, name),
            )

        self.command_registry.register(make(
            "theme-toggle",
            "Toggle between dark and light theme.",
            lambda app: CommandResult(True, toggle_light_dark(app)),
        ))
        self.command_registry.register(make(
            "theme-pick",
            "Open the theme picker.",
            self._cmd_theme_pick,
        ))
        self.command_registry.register(make(
            "doc-rename",
            "Rename the current JSON document.",
            self._cmd_rename,
        ))
        self.command_registry.register(make(
            "doc-save",
            "Force-save the document now.",
            self._cmd_save,
        ))
        self.command_registry.register(make(
            "pane-files-toggle",
            "Toggle the file panel.",
            self._cmd_pane_files_toggle,
        ))
        self.command_registry.register(make(
            "pane-focus-files",
            "Focus the file panel.",
            self._cmd_pane_focus_files,
        ))
        self.command_registry.register(make(
            "pane-focus-editor",
            "Focus the editor.",
            self._cmd_pane_focus_editor,
        ))
        self.command_registry.register(make(
            "hotkeys",
            "Show all current hotkey bindings.",
            self._cmd_hotkeys,
        ))
        self.command_registry.register(make(
            "hotkey-set",
            "Set a hotkey: hotkey-set <action> <key-combo>.",
            self._cmd_hotkey_set,
        ))
        self.command_registry.register(make(
            "doc-new",
            "Create a new JSON document.",
            self._cmd_doc_new,
        ))
        self.command_registry.register(make(
            "doc-open",
            "Open a document from the vault.",
            self._cmd_doc_open,
        ))
        self.command_registry.register(make(
            "command-palette",
            "Open the command palette.",
            lambda app: (self.open_command_palette(), CommandResult(True, "palette"))[1],
        ))
        self.command_registry.register(make(
            "doc-delete",
            "Delete the current document.",
            self._cmd_doc_delete,
        ))

    # ----- command handlers -----------------------------------------

    def _cmd_theme_pick(self, app: Any) -> CommandResult:
        self.open_theme_picker()
        return CommandResult(True, "theme picker opened")

    def _cmd_save(self, app: Any) -> CommandResult:
        return CommandResult(True, self.save_document(force=True))

    def _cmd_pane_files_toggle(self, app: Any) -> CommandResult:
        if self._layout_manager is None:
            return CommandResult(False, "layout not ready")
        lm = self._layout_manager
        visible = lm.toggle("pane-files")
        return CommandResult(True, f"files panel {'shown' if visible else 'hidden'}")

    def _cmd_pane_focus_files(self, app: Any) -> CommandResult:
        try:
            tree = self.query_one("#pane-files", FileTreePanel)
            tree.focus()
            self._focused_panel = "pane-files"
            self._update_panel_borders()
            return CommandResult(True, "focused files panel")
        except Exception:
            return CommandResult(False, "files panel not available")

    def _cmd_pane_focus_editor(self, app: Any) -> CommandResult:
        self._editor().focus()
        self._focused_panel = "editor"
        self._update_panel_borders()
        return CommandResult(True, "focused editor")

    def _cmd_pane_focus_up(self, app: Any) -> CommandResult:
        self._editor().focus()
        self._focused_panel = "editor"
        self._update_panel_borders()
        return CommandResult(True, "focused editor")

    def _cmd_pane_focus_down(self, app: Any) -> CommandResult:
        self._editor().focus()
        self._focused_panel = "editor"
        self._update_panel_borders()
        return CommandResult(True, "focused editor")

    def _cmd_hotkeys(self, app: Any) -> CommandResult:
        rows = ["Hotkeys:", "---------"]
        for b in self.BINDINGS:
            display = getattr(b, "display", "") or ""
            if display:
                rows.append(f"  {b.key} → {display}")
            else:
                rows.append(f"  {b.key}")
        for hk in load_hotkeys():
            for key in hk.keys:
                rows.append(f"  {key} → {hk.action}  (config)")
        return CommandResult(True, "\n".join(rows[:15]))

    def _cmd_hotkey_set(self, app: Any) -> CommandResult:
        from editor_hotkey_set import HotkeySetScreen

        def _on_dismiss(result: tuple[str, str] | None) -> None:
            if not result:
                self.set_status_message("hotkey set cancelled")
                return
            action_name, key_combo = result
            try:
                hotkeys = load_hotkeys()
                new_hk = Hotkey(action=action_name, keys=(key_combo,))
                existing = [h for h in hotkeys if h.action == action_name]
                if existing:
                    hotkeys = [h for h in hotkeys if h.action != action_name]
                hotkeys.append(new_hk)
                save_hotkeys(hotkeys)
                self.set_status_message(f"hotkey set: {key_combo} → {action_name}")
            except Exception as exc:
                self.set_status_message(f"hotkey set failed: {exc}")

        self.push_screen(HotkeySetScreen(), _on_dismiss)
        return CommandResult(True, "hotkey set opened")

    def open_which_key(self) -> None:
        from editor_which_key import WhichKeyScreen
        self.push_screen(WhichKeyScreen(self), self._on_which_key_dismiss)

    def _on_which_key_dismiss(self, key: str | None) -> None:
        self._focused_panel = "editor"
        self._update_panel_borders()
        if key is None:
            return
        self.leader_dispatch(key)

    def leader_dispatch(self, key: str) -> None:
        if key == "n":
            self._cmd_doc_new(self)
        elif key == "o":
            self._cmd_doc_open(self)
        elif key == "s":
            self._cmd_save(self)
        elif key == "p":
            self.open_command_palette()
        elif key == "b":
            self._cmd_pane_files_toggle(self)
        elif key == "h":
            self._cmd_pane_focus_files(self)
        elif key == "l":
            self._cmd_pane_focus_editor(self)
        elif key == "j":
            self._cmd_pane_focus_down(self)
        elif key == "k":
            self._cmd_pane_focus_up(self)
        elif key == "?":
            result = self._cmd_hotkeys(self)
            self.set_status_message(result.message or "")
        elif key == "d":
            self._cmd_doc_delete(self)

    def _cmd_doc_new(self, app: Any) -> CommandResult:
        from editor_new_doc import NewDocScreen

        def _on_dismiss(name: str | None) -> None:
            if not name:
                self.set_status_message("new document cancelled")
                return
            if not name.endswith(".json"):
                name += ".json"
            new_path = self.vault_path / name
            if new_path.exists():
                self.set_status_message(f"file already exists: {name}")
                return
            try:
                save(new_path, "", [])
            except StorageError as exc:
                self.set_status_message(f"create failed: {exc}")
                return
            self.open_document(new_path)
            self._refresh_file_tree()
            self._focused_panel = "editor"
            self._update_panel_borders()

        self.push_screen(NewDocScreen(), _on_dismiss)
        return CommandResult(True, "new document opened")

    def _cmd_doc_open(self, app: Any) -> CommandResult:
        from editor_doc_picker import DocPickerScreen

        docs = list_documents(self.vault_path)

        def _on_dismiss(path_str: str | None) -> None:
            if not path_str:
                self.set_status_message("open cancelled")
                return
            self.open_document(Path(path_str))
            self._refresh_file_tree()
            self._focused_panel = "editor"
            self._update_panel_borders()

        self.push_screen(DocPickerScreen(docs), _on_dismiss)
        return CommandResult(True, "doc picker opened")

    def action_doc_new(self) -> None:
        self._cmd_doc_new(self)

    def action_doc_open(self) -> None:
        self._cmd_doc_open(self)

    def _refresh_file_tree(self) -> None:
        try:
            tree = self.query_one("#pane-files", FileTreePanel)
            tree.reload()
        except Exception:
            pass

    def action_pane_focus_left(self) -> None:
        self._cmd_pane_focus_files(self)

    def action_pane_focus_right(self) -> None:
        self.action_pane_focus_up()

    def action_pane_focus_up(self) -> None:
        self._editor().focus()

    def action_pane_focus_down(self) -> None:
        self._editor().focus()

    def _cmd_rename(self, app: Any) -> CommandResult:
        from editor_rename import RenamePromptScreen

        def _on_dismiss(new_name: str | None) -> None:
            if not new_name:
                self.set_status_message("rename cancelled")
                return
            try:
                new_path = rename(self.document_path, new_name)
            except StorageError as exc:
                self.set_status_message(f"rename failed: {exc}")
                return
            self.document_path = new_path
            self.set_status_message(f"renamed to {new_path.name}")

        self.push_screen(RenamePromptScreen(self.document_path.name), _on_dismiss)
        return CommandResult(True, "rename prompt opened")

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


# Alias for the old command name — maintains backwards compatibility for tests
SimpleTextEditorApp.action_force_save = SimpleTextEditorApp.save_document


if __name__ == "__main__":
    SimpleTextEditorApp().run()