"""Shared base class for modal screens.

Scope
-----
Every modal in `modals/` follows the same visual pattern: centered on a
dimmed background, a rounded `#dialog` container in `$surface`, escape
to dismiss. `BaseModalScreen` consolidates the dismiss-on-escape
binding so individual modals only specify their own contents, sizing
and any extra bindings.

Boundaries
----------
- Does NOT compose specific dialogs. Subclasses define `compose`.
- Does NOT execute commands. Modals return data via `dismiss(value)`.
- Does NOT impose a shared CSS string today (each modal owns its own
  CSS). If we ever consolidate into a single stylesheet, this is the
  place for the shared rules.

Freeze criteria
---------------
- Every modal subclass inherits from `BaseModalScreen`.
- Modal CSS uses only Textual theme variables (no hard-coded hex).
"""

from __future__ import annotations

from typing import Generic, TypeVar

from textual.screen import ModalScreen


_ScreenResult = TypeVar("_ScreenResult")


class BaseModalScreen(ModalScreen[_ScreenResult], Generic[_ScreenResult]):
    """Modal screen with the standard escape-to-dismiss binding.

    Subclasses still define their own CSS for layout (height, width,
    custom widgets), but every modal inherits the dismiss-on-escape
    behavior from here. New modals should subclass this rather than
    `ModalScreen` directly.

    Subclasses parameterize the result type the same way as
    `ModalScreen`: `class FooScreen(BaseModalScreen[str | None]): ...`.
    """

    BINDINGS = [("escape", "dismiss", "Cancel")]
