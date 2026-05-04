"""Panel management: register, show, hide, and toggle UI panels.

Scope
-----
Owns a registry of named panels and exposes show/hide/toggle visibility.
Panels are plain Textual widgets mounted into a container via `dock` CSS
properties. The module does NOT compose the central editor; that is the
app's concern.

Boundaries
----------
- Does NOT create widgets. Callers pass widget instances to `register`.
- Does NOT handle resize. Width is set at registration time. Future
  iterations can add runtime resize via `widget.styles.width = f"{n}"`.
- Does NOT know about file trees or theme pickers. Those are callers.

Freeze criteria
--------------
- `register` mounts a panel and respects `initial_visible`.
- `show` / `hide` / `toggle` / `is_visible` round-trip correctly.
- New panels require only one `register` call in the app.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from textual.containers import Container
from textual.widget import Widget


@dataclass
class Panel:
    id: str
    widget: Widget
    dock: Literal["left", "right"]
    initial_visible: bool = True
    width: int = 30


class LayoutManager:
    def __init__(self, host: Container) -> None:
        self._host = host
        self._panels: dict[str, Panel] = {}

    def register(self, panel: Panel) -> None:
        widget = panel.widget
        widget.id = panel.id
        widget.styles.width = f"{panel.width}"
        widget.styles.dock = panel.dock
        widget.styles.display = "block" if panel.initial_visible else "none"
        self._host.mount(widget)
        self._panels[panel.id] = panel

    def show(self, id: str) -> None:
        if id not in self._panels:
            return
        self._panels[id].widget.styles.display = "block"

    def hide(self, id: str) -> None:
        if id not in self._panels:
            return
        self._panels[id].widget.styles.display = "none"

    def toggle(self, id: str) -> bool:
        if id not in self._panels:
            return False
        panel = self._panels[id]
        visible = panel.widget.styles.display != "none"
        if visible:
            self.hide(id)
        else:
            self.show(id)
        return not visible

    def is_visible(self, id: str) -> bool:
        if id not in self._panels:
            return False
        return self._panels[id].widget.styles.display != "none"