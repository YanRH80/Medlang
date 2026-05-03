"""Visual layer: CSS for the editor.

Scope
-----
Holds the global CSS string applied to the app. All color decisions go
through Textual's theme variables so theme switching Just Works.

Boundaries
----------
- Does NOT own UI structure. Widgets are composed in `app.py`.
- Does NOT pick themes. That lives in `editor_theme_picker`.

Freeze criteria
---------------
- Every built-in Textual theme renders with the editor, header,
  and status bar visible and readable.
- CSS uses only theme variables (`$background`, `$surface`, `$primary`,
  `$foreground`, `$accent`, `$panel`) — no hard-coded hex.
"""

from __future__ import annotations

EDITOR_CSS = """
Screen {
    background: $background;
    color: $foreground;
}

#main {
    height: 100%;
}

Header {
    width: 100%;
    height: auto;
    background: $panel;
    color: $foreground;
}

#workspace {
    height: 1fr;
}

#editor {
    height: 100%;
    border: solid $panel;
    background: $surface;
    color: $foreground;
}

#pane-files {
    height: 100%;
    border-right: solid $panel;
    background: $surface;
    color: $foreground;
}

StatusBar {
    width: 100%;
    height: auto;
    background: $panel;
    color: $foreground;
}

/* Active panel borders — set by app on focus/mode change */
#editor.active-normal,
#editor.active-insert,
#editor.active-visual,
#editor.active-visual_line {
    border: solid $primary;
}

#pane-files.active-normal,
#pane-files.active-insert,
#pane-files.active-visual,
#pane-files.active-visual_line {
    border-right: solid $primary;
}

#editor.active-insert {
    border: solid $success;
}

#pane-files.active-insert {
    border-right: solid $success;
}

#editor.active-visual,
#editor.active-visual_line {
    border: solid $accent;
}

#pane-files.active-visual,
#pane-files.active-visual_line {
    border-right: solid $accent;
}
"""