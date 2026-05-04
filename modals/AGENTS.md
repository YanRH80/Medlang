# modals/ — Modal screens

## Scope

Every transient overlay the user sees: command palette, theme picker,
document picker, new-doc prompt, rename prompt, hotkey setter, WhichKey.
Each modal is a `ModalScreen[ResultType]` that returns the user's choice
(or `None` on cancel) via `dismiss(value)`.

## Boundaries

- Modals do NOT execute commands. They return data; the caller (usually
  `app.py` or a `features/*` module) acts on the result.
- Modals do NOT touch the filesystem. Caller validates and writes.
- Each modal owns its own CSS so layout is decoupled from the rest of
  the app.
- CSS uses **theme variables only** (`$primary`, `$surface`, `$accent`,
  `$panel`, `$foreground`, `$background`, `$success`, `$warning`,
  `$error`). No hardcoded hex.

## Adding a modal

1. New file `modals/<name>.py` defining a `ModalScreen[ReturnType]` subclass.
2. `BINDINGS = [("escape", "dismiss", "Cancel")]`.
3. Caller does `self.push_screen(MyModal(...), self._on_dismiss)`.
4. Test it in `tests/integration/test_<name>.py`.

## Freeze criteria

- Each modal has Enter to confirm, Escape to cancel.
- All modals use only theme variables in CSS.
- All modals return `None` on cancel and a typed value on success.

## Module inventory

| File | Purpose |
|------|---------|
| `command_palette.py` | Fuzzy command picker (`:` and `Ctrl+P`) |
| `theme_picker.py` | Pick one of `app.available_themes` |
| `doc_picker.py` | Pick a `.json` file from the vault |
| `new_doc.py` | Filename prompt for new document |
| `rename.py` | Filename prompt for rename |
| `hotkey_set.py` | Set `<action> <key-combo>` binding |
| `which_key.py` | LazyVim-style leader hint overlay |
