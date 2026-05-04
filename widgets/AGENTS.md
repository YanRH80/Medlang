# widgets/ — Custom Textual widgets (non-modal)

## Scope

Persistent UI widgets that live inside the main app screen. As of now:
the file tree panel.

## Boundaries

- Widgets do NOT load documents. They post `Message` instances (see
  `messages.py`) and the app reacts.
- Widgets do NOT mutate disk.
- Widgets handle their own keyboard nav (e.g. `j`/`k` in the file tree).

## Adding a widget

1. New file `widgets/<name>.py` defining a `Widget` subclass.
2. If it needs to communicate with the app, post a `Message` defined in
   the root `messages.py`.
3. Mount it via `LayoutManager.register(...)` in `app.py:_setup_layout`.

## Freeze criteria

- File tree shows `.json` only, posts `DocumentSelected` on click.
- File tree responds to `j`/`k` navigation.
- File tree consumes `space` to open WhichKey.

## Module inventory

| File | Purpose |
|------|---------|
| `files_panel.py` | `FileTreePanel(DirectoryTree)`, filtered to `.json` |
