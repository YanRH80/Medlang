# AGENTS.md — Medlang Editor

## Project summary

Terminal text editor built with Textual 8.x. Vim-like modes (normal/insert/visual/visual-line),
fuzzy command palette (`:`, `Ctrl+P`), JSON vault persistence with stable line IDs, and
integrated file panel. All documents live in `files/` directory.

## Behavioral principles (Karpathy)

Four lines. Every decision traces back to these.

1. **Think Before Coding** — Don't assume. Don't hide confusion. Surface tradeoffs.
   Before writing code: read the relevant files, check existing patterns, ask if
   the request is ambiguous. Pausing to ask costs less than rewriting.

2. **Simplicity First** — Minimum code that solves the problem. Nothing speculative.
   A function beats a class. A class beats a pattern. A pattern beats an
   architecture. Add nothing that doesn't directly solve the stated problem.

3. **Surgical Changes** — Touch only what you must. Clean up only your own mess.
   Diff reviewability is the goal. If your change makes a diff 5x larger than
   necessary, simplify. Pre-existing code debt: don't touch unless explicitly asked.

4. **Goal-Driven Execution** — Define success criteria. Loop until verified.
   For every task: what does "done" look like? Write it down before coding.
   After coding: verify the criteria are met. Run tests. Check the specific
   behavior that was requested, not a generalization of it.

**Configuration paradox**: more rules make agents confused, not disciplined.
Criterion for adding a line to this file or any instruction:
*"Would removing this cause an irrecuperable error?"*
Do NOT add: architecture overviews (read from code), style guides (infer from patterns),
dependency lists (read from requirements.txt).

## SOLID principles in this codebase

Every module docstring declares: Scope, Boundaries, Freeze Criteria.
These match the SOLID mindset.

| Principle | Application in this repo |
|-----------|--------------------------|
| **S** — Single Responsibility | Each module has one job. `editor_storage.py` = pure I/O, no UI. `editor_keybindings.py` = key dispatch only. `editor_layout.py` = panel visibility only. |
| **O** — Open/Closed | Adding a command = one `registry.register()` call in `app.py`. No edits to `editor_commands.py`. Adding a Vim verb = one block in `editor_keybindings.py`. |
| **L** — Liskov Substitution | `VimTextArea(TextArea)` — all TextArea behavior preserved via `super()._on_key()` when not handling Vim keys. |
| **I** — Interface Segregation | `StatusSnapshot` dataclass has exactly 9 fields, all used by `StatusBar`. No unused fields. `CommandResult` has `ok` + `message` only. |
| **D** — Dependency Inversion | `editor_storage.py` depends on no UI module. `editor_commands.py` depends on no feature module — handlers injected at startup. `app.py` depends on abstract interfaces (registry, storage). |

## Critical technical gotchas

### Textual 8.x theme system
- **`App.dark` was removed in Textual 8**. Use `app.theme = "textual-dark"` (string).
- Query available themes: `sorted(app.available_themes)` — 21 built-in.
- **CSS variables**: only these exist in Textual themes:
  `$background`, `$surface`, `$primary`, `$foreground`, `$accent`, `$panel`,
  `$success`, `$warning`, `$error`. `$text-muted` does NOT exist.
- CSS uses theme variables exclusively — no hard-coded hex in `editor_styles.py`.
  But `editor_command_palette.py` and `editor_theme_picker.py` had hard-coded hex
  that was migrated to theme variables. If adding new CSS, use variables only.

### macOS `super` (Cmd) bindings
- `super+h/j/k/l` and `super+n/o` only work in terminals that forward Cmd:
  Ghostty, Wezterm, Kitty, iTerm2 with config. **Terminal.app blocks them.**
- Always provide `ctrl+` fallback for any `super` binding.
- User uses Ghostty — `super` bindings work there. Bind both `ctrl+` and `super+`
  for maximum compatibility.

### Modifier key propagation in Vim handler
- `handle_vim_key` swallows ALL unhandled keys in non-insert modes by default.
- **Fix**: check `"+" in key` before swallowing. If key has modifier prefix (ctrl+/super+/alt+/shift+),
  return `False` so the event propagates to app-level BINDINGS.
- Example: `super+h` reaches `action_pane_focus_left` because `handle_vim_key` returns `False`
  for keys containing "+".

### Test isolation
- Pilot tests: `pytest.mark.asyncio` + `app.run_test()` + `await pilot.pause()`.
- `tmp_document` fixture patches `app._load_config` with a synthetic dict.
  This pattern avoids hitting the real `config.yaml` during tests.
- `conftest.py` adds project root to `sys.path` so `import app` works inside `tests/`.

### Binding system
- `BINDINGS` on `App` class — processed at `__init__` time. Cannot be modified
  at runtime. Hotkey config in `config.yaml` is loaded by `editor_config.py` and
  can be displayed/saved via `:hotkeys` / `:hotkey-set` commands, but active
  bindings come from `app.py`'s static `BINDINGS` list.
- Action method naming: `action_<name>` where `<name>` = command name with
  hyphens replaced by underscores. E.g., `pane-files-toggle` → `action_pane_files_toggle`.

### Storage
- `editor_storage.py` = pure Python. No Textual imports. Safe to import in tests.
- Atomic save: temp file + `os.replace()`. Crash-safe.
- Stable line IDs: `assign_line_ids(previous_pairs, new_lines)` reuses ids for
  unchanged text only.
- `list_documents(vault: Path)` returns sorted `list[Path]` of `.json` files,
  excluding `.tmp` artefacts.

### Deprecated/dead code
- `editor_palettes.py` — dead. Replaced by `editor_theme_picker.py` + `editor_themes.py`.
- `Palette` dataclass, `PALETTES`, `apply_color_palette` — all removed.
- `toggle_light_dark_mode` → `editor_themes.toggle_light_dark(app)`.

## Module inventory

| Module | Responsibility | Boundaries | Freeze criteria |
|--------|---------------|------------|-----------------|
| `app.py` | Composition root, lifecycle, command registration | No Vim dispatch, no disk I/O, no status rendering | — |
| `editor_keybindings.py` | Vim key dispatch (`handle_vim_key`) | No app state mutation aside from mode/prefix | All documented verbs work in their modes. Modifier keys (ctrl+/super+/alt+) propagate to app bindings. |
| `editor_storage.py` | Atomic JSON load/save, stable IDs, `list_documents` | No Textual, no UI | Load/save atomic, IDs stable, rename validated. |
| `editor_commands.py` | Pluggable command registry (OCP) | No feature handlers — injected at startup | `register`, `execute`, `fuzzy_find` all work. |
| `editor_status.py` | Status bar render from `StatusSnapshot` | No state mutation | Mode chip colors correct, 6 segments render. |
| `editor_layout.py` | Panel register/show/hide/toggle | No widget creation | register/show/hide/toggle round-trip. |
| `editor_panel_files.py` | `FileTreePanel(DirectoryTree)` filtered to `.json`, posts `DocumentSelected` | No document loading | Tree shows only .json, DocumentSelected fires on click. |
| `editor_theme_picker.py` | Theme picker modal — lists `app.available_themes`, sets `app.theme` | No theme implementation | Enter picks top match, Escape cancels. |
| `editor_themes.py` | `toggle_light_dark`, `list_themes`, `is_dark_theme` | No UI | toggle_light_dark flips theme, list_themes returns sorted themes. |
| `editor_styles.py` | CSS string with theme variables only | No palette logic | CSS uses only $variables. |
| `editor_config.py` | Hotkey load/save from `config.yaml` | No app imports | load_hotkeys/save_hotkeys round-trip correctly. |
| `editor_command_palette.py` | Fuzzy command palette modal | No command execution | Typing filters, Enter submits top match, Escape cancels. |
| `editor_doc_picker.py` | Document picker modal — lists vault .json files, fuzzy filter | No document loading | Enter selects, Escape cancels, file tree refreshed on select. |
| `editor_new_doc.py` | New document name prompt modal | No disk I/O | Enter submits name, Escape cancels, invalid names rejected. |
| `editor_rename.py` | Rename prompt modal | No disk I/O | Enter renames, Escape cancels. |
| `editor_hotkey_set.py` | Hotkey setter modal | No config writing | Enter sets hotkey, Escape cancels. |
| `editor_register.py` | Vim yank/paste register | No UI | yy/p/P/x all work. |
| `config.yaml` | User-editable config (hotkeys, theme, vault path, panels) | — | — |
| `files/` | Vault directory — all .json documents | — | — |

## Adding a command

**Pipeline (3 steps):**

1. **Entry** → Add to `DEFAULT_CONFIG["commands"]` in `app.py`:
   ```python
   "command-name": {
       "enabled": True,
       "description": "What it does.",
       "hotkeys": [],
   }
   ```

2. **Registration** → Add handler in `_register_commands()`:
   ```python
   self.command_registry.register(make(
       "command-name",
       "What it does.",
       self._cmd_handler,
   ))
   ```

3. **Binding** → Add `Binding("key", "action_name", "Display")` to `BINDINGS` list
   (if the command needs a keyboard shortcut).

**Handler template** (closure over app state):
```python
def _cmd_handler(self, app: Any) -> CommandResult:
    # Do work here
    return CommandResult(True, "status message")
```

## Command naming convention

Prefix by domain to avoid collisions:

| Prefix | Domain | Examples |
|--------|--------|----------|
| `theme-` | Color/theming | `theme-toggle`, `theme-pick` |
| `pane-` | Layout/panels | `pane-files-toggle`, `pane-focus-files` |
| `doc-` | Document I/O | `doc-save`, `doc-rename`, `doc-new`, `doc-open` |
| `hotkeys` | Hotkey management | `hotkeys`, `hotkey-set` |

## Hotkey configuration

Hotkeys stored in `config.yaml` under `commands[name].hotkeys: []`.
Format: `"ctrl+<key>"`, `"super+<key>"`, `"ctrl+shift+<key>"`.

Display current bindings: `:hotkeys` command.
Set a binding: `:hotkey-set` → modal → enter `<action> <key-combo>`.
Changes persist to `config.yaml`. Active bindings at runtime come from
`app.py`'s static `BINDINGS` list (loaded from config on restart).

## Vim verbs implemented

- Motion: `h j k l 0 $ gg G w b e W B E`
- Insert entry: `i a I A o O`
- Delete: `x dd`
- Yank/paste: `yy p P`
- Visual: `v V`; in visual: `y d` + motion
- Join: `J` (normal mode — joins current line with next)
- Undo/redo: `u ctrl+r`
- Command palette: `:` (opens modal)
- Other: `escape` → normal mode
- Prefix system: `g` ( gg top-of-doc), `d` (dd delete line), `y` (yy yank line)

**Not implemented** (deferred): `gU`/`gu` (uppercase/lowercase) — requires motion-object system.

## Testing

```bash
# Full suite
.venv/bin/python -m pytest tests/ -q

# Single file
.venv/bin/python -m pytest tests/test_app_pilot.py -q

# Single test
.venv/bin/python -m pytest tests/test_app_pilot.py::test_app_starts_in_normal_mode -v
```

Required: `pytest>=8.0`, `pytest-asyncio>=0.23`.

## Run the app

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

## File locations

- Vault: `files/` (all `.json` files are documents)
- Default document: `files/document.json`
- Config: `config.yaml`
- Tests: `tests/`

## Design decisions worth preserving

- Mode chip (NORMAL/INSERT/VISUAL) lives in `StatusBar`, not Footer.
  Moving it to Footer requires subclassing Footer — deferred.
- Tabs NOT implemented — sidebar with FileTreePanel already provides
  multi-document navigation. Tabs would multiply editor instances.
- `gU`/`gu` (uppercase/lowercase) NOT implemented — requires motion-object
  system extension (gUiw, gU$, etc.). `J` (join) is implemented.
- Focus border: CSS `:focus` pseudo-class on `#editor` and `#pane-files`.
  Textual renders focus ring automatically for focusable widgets.
- No new dependencies. Everything built with Textual built-in widgets
  (`Tabs`, `DirectoryTree`, `ModalScreen`, `OptionList`, `Input`).
- Modifier keys (`ctrl+`, `super+`, `alt+`) always propagate from
  `handle_vim_key` to app-level BINDINGS — critical for global shortcuts.

## Audit cycle — how to use this file

After any session of changes, run:

```bash
# 1. Tests green
.venv/bin/python -m pytest tests/ -q

# 2. Import check
.venv/bin/python -c "from app import SimpleTextEditorApp; print('OK')"

# 3. Read AGENTS.md and verify:
#    - New module has Scope/Boundaries/Freeze criteria docstring
#    - New command follows naming convention (theme-/pane-/doc-)
#    - New command has entry in DEFAULT_CONFIG + _register_commands
#    - New binding in BINDINGS (if applicable)
#    - New module does NOT import from modules that depend on it (no cycles)
#    - Frozen modules NOT modified (check module inventory)
```

If a module's freeze criteria are met and it works correctly: **do not modify it**.
If you need new functionality: add a new module, register it in `app.py`, done.