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

Freeze criteria
---------------
- The editor loads/saves the JSON document on every change.
- Mode transitions and palette changes refresh the status bar.
- Commands are registered exactly once in `_register_commands`. New
  commands plug in there without touching any other module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from textual.app import App, ComposeResult
from textual.binding import Binding
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
from editor_palettes import PalettePickerScreen
from editor_register import Register
from editor_status import StatusBar, StatusSnapshot
from editor_storage import LoadedDocument, StorageError, load, rename, save
from editor_styles import EDITOR_CSS, apply_color_palette, palette_names, toggle_light_dark_mode


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
        "palette": "midnight",
    },
    "storage": {
        "document_path": "document.json",
        "auto_save": True,
    },
    "commands": {
        "light-dark-mode": {
            "enabled": True,
            "description": "Toggle light / dark mode.",
        },
        "palette": {
            "enabled": True,
            "description": "Open the color palette picker.",
        },
        "rename": {
            "enabled": True,
            "description": "Rename the current JSON document.",
        },
        "save": {
            "enabled": True,
            "description": "Force-save the document now.",
        },
    },
}


_KNOWN_TOP_LEVEL_KEYS = set(DEFAULT_CONFIG.keys())
_KNOWN_EDITOR_KEYS = set(DEFAULT_CONFIG["editor"].keys())
_KNOWN_STORAGE_KEYS = set(DEFAULT_CONFIG["storage"].keys())


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
    """Minimal Textual editor with Vim-like modes and JSON autosave."""

    TITLE = ""
    SUB_TITLE = ""
    CSS = EDITOR_CSS

    # Disable Textual's built-in command palette; we own `:` and Ctrl+P.
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("ctrl+p", "open_command_palette", "Commands"),
        Binding("ctrl+s", "force_save", "Save"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    vim_mode = reactive(VimMode.NORMAL)
    status_message = reactive("")

    # ----- construction ---------------------------------------------------

    def __init__(self) -> None:
        config, config_warnings = _load_config()
        self.config_data = config
        self._config_warnings = config_warnings

        storage_cfg = self.config_data["storage"]
        editor_cfg = self.config_data["editor"]

        self.document_path: Path = (BASE_DIR / storage_cfg["document_path"]).resolve()
        self.auto_save = bool(storage_cfg.get("auto_save", True))
        self.palette_name = str(editor_cfg.get("palette", "midnight"))

        self._loaded_pairs: list[tuple[str, str]] = []
        self._loading_document = False
        self._modified = False

        self.command_registry = CommandRegistry()
        self.register = Register()
        self.visual_anchor: tuple[int, int] | None = None
        self.vim_prefix = ""

        super().__init__()
        self.title = self.config_data["app"]["title"]
        self.sub_title = self.config_data["app"]["subtitle"]

    # ----- composition -----------------------------------------------------

    def compose(self) -> ComposeResult:
        editor_cfg = self.config_data["editor"]
        yield Header(show_clock=True)
        yield VimTextArea(
            "",
            id="editor",
            soft_wrap=bool(editor_cfg.get("soft_wrap", False)),
            show_line_numbers=bool(editor_cfg.get("show_line_numbers", True)),
            tab_behavior="indent",
            placeholder=str(editor_cfg.get("placeholder", "")),
        )
        yield StatusBar(id="status-bar")
        yield Footer()

    # ----- lifecycle -------------------------------------------------------

    def on_mount(self) -> None:
        """Initialise document, palette, status bar, and registered commands."""

        start_mode_raw = self.config_data["editor"].get("vim_start_mode", "normal")
        try:
            self.vim_mode = VimMode(start_mode_raw)
        except ValueError:
            self.vim_mode = VimMode.NORMAL
            self._config_warnings.append(f"invalid vim_start_mode: {start_mode_raw!r}")

        self._register_commands()
        self._load_document()
        self.apply_palette(self.palette_name)
        self._editor().focus()
        self.refresh_status()

        if self._config_warnings:
            self.set_status_message("config: " + "; ".join(self._config_warnings))

    # ----- editor accessor -------------------------------------------------

    def _editor(self) -> VimTextArea:
        return self.query_one("#editor", VimTextArea)

    def _status_bar(self) -> StatusBar:
        return self.query_one("#status-bar", StatusBar)

    # ----- status bar ------------------------------------------------------

    def refresh_status(self) -> None:
        """Push a fresh snapshot to the status bar."""

        editor = self._editor()
        row, col = editor.cursor_location
        snapshot = StatusSnapshot(
            mode=str(self.vim_mode),
            file_name=self.document_path.name,
            cursor_line=row + 1,
            cursor_column=col + 1,
            line_count=editor.document.line_count,
            palette_name=self.palette_name,
            modified=self._modified,
            pending=self.vim_prefix,
            message=self.status_message,
        )
        self._status_bar().set_snapshot(snapshot)

    def set_status_message(self, message: str) -> None:
        self.status_message = message
        self.refresh_status()

    # ----- mode transitions ------------------------------------------------

    def enter_normal_mode(self) -> None:
        editor = self._editor()
        editor.selection = Selection.cursor(editor.cursor_location)
        self.visual_anchor = None
        self.vim_prefix = ""
        self.vim_mode = VimMode.NORMAL
        self.refresh_status()

    def enter_insert_mode(self) -> None:
        self.visual_anchor = None
        self.vim_prefix = ""
        self.vim_mode = VimMode.INSERT
        self.refresh_status()

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

    # ----- command palette -------------------------------------------------

    def action_open_command_palette(self) -> None:
        """Footer-bound action to open the command palette."""

        self.open_command_palette()

    def action_force_save(self) -> None:
        """Footer-bound action to force-save."""

        message = self.save_document(force=True)
        self.set_status_message(message)

    def open_command_palette(self) -> None:
        """Push the modal command palette and dispatch the chosen command."""

        self.push_screen(CommandPaletteScreen(self.command_registry), self._apply_command_choice)

    def _apply_command_choice(self, command_name: str | None) -> None:
        if command_name is None:
            self.set_status_message("command cancelled")
            return
        result = self.command_registry.execute(self, command_name)
        message = result.message or (f"ran {command_name}" if result.ok else f"failed {command_name}")
        self.set_status_message(message)

    # ----- palette picker --------------------------------------------------

    def open_palette_picker(self) -> None:
        self.push_screen(PalettePickerScreen(), self._apply_palette_choice)

    def _apply_palette_choice(self, palette_name: str | None) -> None:
        if palette_name is None:
            self.set_status_message("palette selection cancelled")
            return
        self.apply_palette(palette_name)
        self.set_status_message(f"palette set to {palette_name}")

    def apply_palette(self, palette_name: str) -> None:
        if palette_name not in set(palette_names()):
            palette_name = "midnight"
        self.palette_name = palette_name
        apply_color_palette(self, palette_name)
        self.refresh_status()

    # ----- command registration -------------------------------------------

    def _register_commands(self) -> None:
        """Wire feature actions into the command registry.

        Adding a new command means adding one block here. The registry
        itself never has to change.
        """

        commands_cfg = self.config_data.get("commands", {})

        def make(name: str, default_description: str, handler) -> Command:
            return Command(
                name=name,
                description=description_from_config(commands_cfg, name, default_description),
                handler=handler,
                enabled=is_enabled_in_config(commands_cfg, name),
            )

        self.command_registry.register(
            make(
                "light-dark-mode",
                "Toggle light / dark mode.",
                lambda app: CommandResult(True, toggle_light_dark_mode(app)),
            )
        )
        self.command_registry.register(
            make(
                "palette",
                "Open the color palette picker.",
                self._command_palette,
            )
        )
        self.command_registry.register(
            make(
                "rename",
                "Rename the current JSON document.",
                self._command_rename,
            )
        )
        self.command_registry.register(
            make(
                "save",
                "Force-save the document now.",
                self._command_save,
            )
        )

    # ----- command handlers (closures over app state) ---------------------

    def _command_palette(self, app: Any) -> CommandResult:
        self.open_palette_picker()
        return CommandResult(True, "palette picker opened")

    def _command_save(self, app: Any) -> CommandResult:
        return CommandResult(True, self.save_document(force=True))

    def _command_rename(self, app: Any) -> CommandResult:
        """Push a tiny modal to ask for the new filename, then rename on disk."""

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

    # ----- document persistence -------------------------------------------

    def _load_document(self) -> None:
        self._loading_document = True
        editor = self._editor()
        try:
            doc: LoadedDocument = load(self.document_path)
            editor.text = doc.text
            self._loaded_pairs = list(zip(doc.text.split("\n") if doc.text else [], doc.line_ids, strict=False))
            self._modified = False
        except Exception as exc:  # pragma: no cover - defensive
            editor.text = ""
            self._loaded_pairs = []
            self._modified = False
            self.set_status_message(f"load failed: {exc}")
        finally:
            self._loading_document = False

    def save_document(self, force: bool = False) -> str:
        """Persist to disk. Returns a status message."""

        if not self.auto_save and not force:
            return "auto-save disabled"
        editor = self._editor()
        try:
            new_ids = save(self.document_path, editor.text, self._loaded_pairs)
        except StorageError as exc:
            return f"save failed: {exc}"
        # Update the snapshot of (text, id) pairs for the next save.
        new_lines = [] if editor.text == "" else editor.text.split("\n")
        self._loaded_pairs = list(zip(new_lines, new_ids, strict=False))
        self._modified = False
        self.refresh_status()
        return "saved"

    # ----- text-area events -----------------------------------------------

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


if __name__ == "__main__":
    SimpleTextEditorApp().run()
