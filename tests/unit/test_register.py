"""Pin-down tests for register.Register."""

from __future__ import annotations

import pytest

from register import Register, RegisterContent


# ---------------------------------------------------------------------------
# Mock TextArea-like editor that records every insert and tracks the cursor.
# ---------------------------------------------------------------------------


class FakeDocument:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    def __getitem__(self, idx: int) -> str:
        return self._lines[idx]


class FakeEditor:
    def __init__(self, lines: list[str], cursor: tuple[int, int]) -> None:
        self._lines = list(lines)
        self.cursor_location = cursor
        self.document = FakeDocument(self._lines)
        self.inserts: list[tuple[str, tuple[int, int]]] = []

    def get_cursor_line_end_location(self) -> tuple[int, int]:
        row, _ = self.cursor_location
        return (row, len(self._lines[row]))

    def insert(self, text: str, location: tuple[int, int] | None = None) -> None:
        loc = location if location is not None else self.cursor_location
        self.inserts.append((text, loc))

    def move_cursor(self, location: tuple[int, int]) -> None:
        self.cursor_location = location


# ---------------------------------------------------------------------------
# Register state.
# ---------------------------------------------------------------------------


def test_empty_register_is_empty() -> None:
    r = Register()
    assert r.is_empty()
    assert r.content() is None


def test_yank_stores_charwise() -> None:
    r = Register()
    r.yank("abc", linewise=False)
    content = r.content()
    assert content == RegisterContent("abc", False)


def test_yank_stores_linewise() -> None:
    r = Register()
    r.yank("line1\nline2", linewise=True)
    content = r.content()
    assert content is not None
    assert content.linewise is True
    assert content.text == "line1\nline2"


# ---------------------------------------------------------------------------
# Paste-after.
# ---------------------------------------------------------------------------


def test_paste_after_empty_register_returns_message() -> None:
    r = Register()
    editor = FakeEditor(["foo"], (0, 0))
    assert r.paste_after(editor) == "register empty"
    assert editor.inserts == []


def test_paste_after_linewise_inserts_below() -> None:
    r = Register()
    r.yank("yanked", linewise=True)
    editor = FakeEditor(["foo", "bar"], (0, 1))
    msg = r.paste_after(editor)
    assert msg == "pasted line below"
    assert editor.inserts == [("\nyanked", (0, 3))]
    assert editor.cursor_location == (1, 0)


def test_paste_after_charwise_inserts_after_cursor() -> None:
    r = Register()
    r.yank("X", linewise=False)
    editor = FakeEditor(["foo"], (0, 1))
    msg = r.paste_after(editor)
    assert msg == "pasted after"
    assert editor.inserts == [("X", (0, 2))]


def test_paste_after_charwise_clamps_to_line_end() -> None:
    r = Register()
    r.yank("X", linewise=False)
    editor = FakeEditor(["foo"], (0, 3))
    r.paste_after(editor)
    # Cursor at col 3 (end of "foo"); target_col = min(3+1, 3) = 3.
    assert editor.inserts == [("X", (0, 3))]


def test_paste_after_linewise_strips_trailing_newline() -> None:
    r = Register()
    r.yank("yanked\n", linewise=True)
    editor = FakeEditor(["foo"], (0, 0))
    r.paste_after(editor)
    assert editor.inserts == [("\nyanked", (0, 3))]


# ---------------------------------------------------------------------------
# Paste-before.
# ---------------------------------------------------------------------------


def test_paste_before_empty_register_returns_message() -> None:
    r = Register()
    editor = FakeEditor(["foo"], (0, 0))
    assert r.paste_before(editor) == "register empty"
    assert editor.inserts == []


def test_paste_before_linewise_inserts_above() -> None:
    r = Register()
    r.yank("yanked", linewise=True)
    editor = FakeEditor(["foo", "bar"], (1, 2))
    msg = r.paste_before(editor)
    assert msg == "pasted line above"
    assert editor.inserts == [("yanked\n", (1, 0))]
    assert editor.cursor_location == (1, 0)


def test_paste_before_charwise_inserts_at_cursor() -> None:
    r = Register()
    r.yank("X", linewise=False)
    editor = FakeEditor(["foo"], (0, 1))
    msg = r.paste_before(editor)
    assert msg == "pasted before"
    assert editor.inserts == [("X", None)] or editor.inserts == [("X", (0, 1))]
    # Either default-cursor or explicit cursor location is valid.


# ---------------------------------------------------------------------------
# Round-trip.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text,linewise", [
    ("hello", False),
    ("multi\nline", True),
    ("", False),
])
def test_yank_round_trip(text: str, linewise: bool) -> None:
    r = Register()
    r.yank(text, linewise=linewise)
    content = r.content()
    assert content == RegisterContent(text, linewise)
