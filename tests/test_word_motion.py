"""Tests for word-motion helpers in editor_keybindings."""

from __future__ import annotations

import pytest

from editor_keybindings import next_word_end, next_word_start, prev_word_start


# ---------------------------------------------------------------------------
# next_word_start (Vim `w` / `W`)
# ---------------------------------------------------------------------------


def test_next_word_start_simple() -> None:
    lines = ["hello world"]
    # cursor at H (col 0) → next word starts at col 6 ("world")
    assert next_word_start(lines, (0, 0)) == (0, 6)


def test_next_word_start_skips_to_next_line() -> None:
    lines = ["one", "two"]
    assert next_word_start(lines, (0, 1)) == (1, 0)


def test_next_word_start_at_end_of_doc() -> None:
    lines = ["only"]
    # cursor at end → stays at end
    assert next_word_start(lines, (0, 3)) == (0, len("only"))


def test_next_word_start_treats_punctuation_as_separate_word() -> None:
    lines = ["foo.bar"]
    # `\w+` regex: "foo" then "bar"; cursor at 0 → next start at 4
    assert next_word_start(lines, (0, 0)) == (0, 4)


def test_next_big_word_start_treats_punctuation_as_part_of_word() -> None:
    lines = ["foo.bar baz"]
    # `\S+` regex: "foo.bar" is one WORD; next WORD = "baz" at col 8
    assert next_word_start(lines, (0, 0), big=True) == (0, 8)


# ---------------------------------------------------------------------------
# prev_word_start (Vim `b` / `B`)
# ---------------------------------------------------------------------------


def test_prev_word_start_within_line() -> None:
    lines = ["hello world"]
    # cursor at col 8 (inside "world") → previous word start = "hello" at 0
    assert prev_word_start(lines, (0, 8)) == (0, 6)


def test_prev_word_start_jumps_to_previous_line() -> None:
    lines = ["one two", "three"]
    # cursor at start of line 1 → "two" at col 4 of line 0
    assert prev_word_start(lines, (1, 0)) == (0, 4)


def test_prev_word_start_at_doc_start() -> None:
    lines = ["only"]
    assert prev_word_start(lines, (0, 0)) == (0, 0)


# ---------------------------------------------------------------------------
# next_word_end (Vim `e` / `E`)
# ---------------------------------------------------------------------------


def test_next_word_end_simple() -> None:
    lines = ["hello world"]
    # cursor at col 0 → end of "hello" at col 4
    assert next_word_end(lines, (0, 0)) == (0, 4)


def test_next_word_end_skips_to_next_word() -> None:
    lines = ["hello world"]
    # cursor at col 4 (already at end of "hello") → end of "world" at col 10
    assert next_word_end(lines, (0, 4)) == (0, 10)


def test_next_word_end_jumps_lines() -> None:
    lines = ["one", "two"]
    # cursor at end of "one" (col 2) → end of "two" at col 2 of line 1
    assert next_word_end(lines, (0, 2)) == (1, 2)
