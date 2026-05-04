# vim/ — Vim-specific dispatch

## Scope

Owns the Vim mental model:

- **Modes** (`VimMode` enum): `NORMAL`, `INSERT`, `VISUAL`, `VISUAL_LINE`.
- **Key dispatch** (`handle_vim_key`): translates `event.key` into editor verbs.
- **Word motion** (`next_word_start`, `prev_word_start`, `next_word_end`):
  pure functions over `(lines, cursor) -> cursor`.

## Boundaries

- NO Textual app or screen imports. Only `textual.widgets.text_area.Selection`.
- NO disk I/O.
- NO command registration. Vim verbs that need to invoke `:` commands call
  `app.open_command_palette()`; the palette executes from the registry.
- Modifier keys (`ctrl+/super+/alt+`) propagate to app-level BINDINGS by
  returning `False` when `"+" in key`. Critical for global shortcuts.

## Adding a Vim verb

1. Add the key handling block in `handle_vim_key` under the appropriate mode.
2. If the verb requires app state mutation beyond mode/prefix, expose a
   helper on `app` (e.g. `app.enter_visual_mode`) and call it.
3. Add an integration test in `tests/integration/test_keybindings_integration.py`.

## Freeze criteria

- All documented verbs work in their modes (motion, insert, delete, yank,
  paste, visual, undo/redo, join).
- Two-key prefixes (`dd`, `yy`, `gg`) work via `app.vim_prefix`.
- `space` opens WhichKey, `:` opens command palette.
- Modifier keys propagate.

## Module inventory

| File | Purpose |
|------|---------|
| `keybindings.py` | `VimMode`, `handle_vim_key`, word motion helpers |
