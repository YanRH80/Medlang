"""High-level command modules (theme, document, pane, hotkey, leader).

Each feature module exports `register(app, registry)` to plug in its
commands at startup. This keeps `app.py` a thin composition root.
"""
