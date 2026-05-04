"""Custom Textual messages for cross-widget communication.

Scope
-----
Centralizes the `Message` subclasses widgets post to communicate with
the app or with each other. Following the pattern from Posting and
Toolong, having a single module for messages keeps the bus
discoverable and avoids circular imports between widgets and the app.

Boundaries
----------
- Pure data classes. No behavior, no widget references.
- No imports from app.py or any feature module.

Freeze criteria
---------------
- New cross-module messages live here, not inside the widget that posts
  them.
- Each message carries only the data the listener needs (no widget refs).
"""

from __future__ import annotations

from pathlib import Path

from textual.message import Message


class DocumentSelected(Message):
    """Posted when the user picks a document in the file tree.

    The app handles this by opening the document in the editor (saving
    any pending changes first).
    """

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
