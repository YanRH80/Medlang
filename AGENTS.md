# AGENTS.md — Medlang

Terminal Vim-like JSON editor built on Textual 8.x. Modal modes, fuzzy
command palette, leader keys (LazyVim-style WhichKey), file panel, JSON
vault with stable line IDs.

## Behavioral principles (Karpathy)

1. **Think Before Coding** — Don't assume. Read the relevant files. Ask
   on ambiguity. Pausing costs less than rewriting.
2. **Simplicity First** — Minimum code that solves the problem. A
   function beats a class beats a pattern beats an architecture.
3. **Surgical Changes** — Touch only what you must. Diff reviewability
   is the goal. Don't fix pre-existing debt unless asked.
4. **Goal-Driven Execution** — Define success criteria up front. Verify
   after coding. Run tests for the specific behavior requested.

## Directory layout

```
medlang/
├── app.py                       composition root + lifecycle
├── config.py                    DEFAULT_CONFIG + load_config + validate
├── config.yaml                  user-editable config
├── styles.tcss                  global CSS (theme variables only)
├── messages.py                  custom Textual messages
├── commands.py                  pluggable command registry
├── storage.py                   atomic JSON load/save + stable line IDs
├── register.py                  Vim yank/paste register
├── status_bar.py                modeline widget
├── layout.py                    panel show/hide/toggle
├── themes.py                    theme list + dark/light toggle
├── hotkey_config.py             hotkey load/save (config.yaml)
│
├── vim/                         Vim-specific dispatch
│   ├── modes.py                 VimMode + transition()
│   └── keybindings.py           handle_vim_key + word motion
│
├── modals/                      modal screens
│   ├── _base.py                 BaseModalScreen (escape-to-dismiss)
│   ├── command_palette.py       fuzzy palette (`:` and Ctrl+P)
│   ├── theme_picker.py          pick from app.available_themes
│   ├── doc_picker.py            fuzzy file picker
│   ├── new_doc.py               filename prompt
│   ├── rename.py                filename prompt
│   ├── hotkey_set.py            <action> <key-combo> setter
│   └── which_key.py             leader key hint overlay
│
├── widgets/                     non-modal widgets
│   └── files_panel.py           FileTreePanel (.json filtered)
│
├── features/                    high-level command modules
│   ├── theme.py                 theme-toggle, theme-pick
│   ├── document.py              doc-new/open/save/rename/delete
│   ├── pane.py                  pane-files-toggle, pane-focus-*
│   ├── hotkey.py                hotkeys, hotkey-set
│   └── leader.py                LEADER_MAP + dispatch
│
├── files/                       JSON vault
└── tests/
    ├── conftest.py              shared fixtures (tmp_document)
    ├── unit/                    pure unit tests
    └── integration/             Pilot tests
```

## Compartmentalized navigation

Each subdirectory has its own AGENTS.md. **Read only the directory you
work in plus this root file.** That keeps a typical session under ~120
LOC of documentation.

| Task | Read |
|------|------|
| Add a Vim verb | `vim/AGENTS.md` + `vim/keybindings.py` |
| Add a modal | `modals/AGENTS.md` + `modals/_base.py` + closest sibling |
| Add a widget | `widgets/AGENTS.md` |
| Add a command | `features/AGENTS.md` + closest sibling feature |
| Storage / config | `storage.py` / `config.py` (no subdir) |

## SOLID applied here

| Letter | How |
|--------|-----|
| **S** Single Responsibility | One module, one job. `storage.py` is pure I/O. `vim/keybindings.py` is dispatch only. |
| **O** Open/Closed | Add commands by dropping a `features/<name>.py` with `register(app, registry)`. `app.py` only lists modules. |
| **L** Liskov | `VimTextArea(TextArea)` preserves all parent behavior. Modals subclass `BaseModalScreen` without breaking `ModalScreen` contracts. |
| **I** Interface Segregation | `StatusSnapshot` has only fields `StatusBar` reads. `CommandResult` has `ok` + `message`. |
| **D** Dependency Inversion | `commands.py` registry knows nothing about specific commands. Handlers injected at startup. `vim/keybindings.py` calls `app.open_command_palette()` (interface), never the modal class directly. |

## Critical technical gotchas

### Textual 8.x

- `App.dark` was removed. Use `app.theme = "tokyo-night"` (string).
- Available CSS theme variables: `$background`, `$surface`, `$primary`,
  `$foreground`, `$accent`, `$panel`, `$success`, `$warning`, `$error`.
  **`$text-muted` does NOT exist.**
- CSS lives in `styles.tcss`. Theme variables only — no hex.
- `BINDINGS` are processed at App `__init__` and cannot be edited at
  runtime. `config.yaml` `commands[name].hotkeys` is informational and
  applies on next launch.

### Vim handler key propagation

- `handle_vim_key` returns `False` for keys containing `+` (i.e.
  `ctrl+p`, `super+h`) so app BINDINGS receive them.
- Unhandled keys in non-INSERT modes are swallowed
  (`event.stop()`), preventing accidental edits.

### Tests

- `tmp_document` fixture (in `tests/conftest.py`) patches
  `app._load_config` to return a synthetic config. **Never hits the real
  `config.yaml`.**
- Pilot tests use `pytest.mark.asyncio` + `app.run_test()` + `await
  pilot.pause()`.

### macOS Cmd

- `super+*` bindings are NOT used. They get intercepted by macOS even
  in Ghostty (`cmd+shift+h` → "Hide Others"). All app bindings use
  `ctrl+`. Leader keys (`space ...`) cover the rest.

## Adding a command — 3 steps

1. **Config entry** in `config.py:DEFAULT_CONFIG["commands"]`:
   ```python
   "my-cmd": {"enabled": True, "description": "...", "hotkeys": []}
   ```
2. **Handler + register** in the appropriate `features/*.py`:
   ```python
   def _cmd_my(app):
       return CommandResult(True, "ran")

   def register(app, registry):
       ...
       registry.register(_make(cfg, "my-cmd", "...", _cmd_my))
   ```
3. **Binding (optional)**: if it needs a global key, append a
   `Binding(...)` to `app.BINDINGS`. If it should be a leader key,
   append to `LEADER_MAP` in `features/leader.py` and `COMMANDS` in
   `modals/which_key.py`.

## Vim verbs implemented

- Motion: `h j k l 0 $ gg G w b e W B E`
- Insert entry: `i a I A o O`
- Delete: `x dd`
- Yank/paste: `yy p P`
- Visual: `v V`; in visual: `y d` + motion
- Join: `J`
- Undo/redo: `u Ctrl+R`
- Command palette: `:`
- Leader: `space` then one of `n o s d p b h l ?`

Not implemented (deferred): `gU`/`gu` (case change) — requires motion-
object grammar.

## Testing

```bash
.venv/bin/python -m pytest tests/ -q                     # full suite
.venv/bin/python -m pytest tests/unit -q                 # unit only
.venv/bin/python -m pytest tests/integration -q          # Pilot only
```

Required: `pytest>=8.0`, `pytest-asyncio>=0.23`.

## Run

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

## Audit cycle

After any session:

```bash
# 1. Tests green
.venv/bin/python -m pytest tests/ -q

# 2. Import smoke test
.venv/bin/python -c "from app import SimpleTextEditorApp; print('OK')"

# 3. App actually starts (visual check)
.venv/bin/python app.py
```

If frozen modules listed in their AGENTS.md still meet their freeze
criteria: do not modify them. New functionality goes in a new module
plus a `register(app, registry)` plug-in.
