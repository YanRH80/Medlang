# features/ — High-level command modules

## Scope

Each file groups commands for one user-facing domain:

- `theme.py` — theme commands (`theme-toggle`, `theme-pick`)
- `document.py` — `doc-new`, `doc-open`, `doc-save`, `doc-rename`, `doc-delete`
- `pane.py` — `pane-files-toggle`, `pane-focus-files`, `pane-focus-editor`
- `hotkey.py` — `hotkeys`, `hotkey-set`
- `leader.py` — WhichKey + leader-key dispatch table

## Plugin pattern

Each feature module exports a `register(app, registry)` function that
plugs its commands into the running app. `app.py` only knows the list of
modules; nothing else.

```python
# features/theme.py
def register(app: SimpleTextEditorApp, registry: CommandRegistry) -> None:
    registry.register(Command(
        name="theme-toggle",
        description="Toggle dark/light theme.",
        handler=lambda app: CommandResult(True, toggle_light_dark(app)),
    ))
    registry.register(Command(
        name="theme-pick",
        description="Open the theme picker.",
        handler=_cmd_theme_pick,
    ))


def _cmd_theme_pick(app: SimpleTextEditorApp) -> CommandResult:
    app.open_theme_picker()
    return CommandResult(True, "theme picker opened")
```

`app.py:_register_commands` becomes:

```python
from features import theme, document, pane, hotkey, leader

for module in (theme, document, pane, hotkey, leader):
    module.register(self, self.command_registry)
```

## Boundaries

- Features import from `commands.py`, `storage.py`, `modals/*`, etc.
- Features do NOT import from each other (no `features.theme` from
  `features.document`).
- Features may import `app` only via `TYPE_CHECKING` for type hints.

## Naming convention

| Prefix | Domain |
|--------|--------|
| `theme-` | Color/theming |
| `pane-` | Layout/panels |
| `doc-` | Document I/O |
| `hotkeys`, `hotkey-set` | Hotkey management |

## Freeze criteria

- All commands registered exactly once.
- Each command has an entry in `config.py:DEFAULT_CONFIG["commands"]`.
- Adding a command does NOT touch `app.py` (only the relevant
  `features/*.py`).
