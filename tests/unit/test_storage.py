"""Tests for storage: load, save, rename, stable line IDs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from storage import (
    LoadedDocument,
    StorageError,
    assign_line_ids,
    load,
    rename,
    save,
)


# ---------------------------------------------------------------------------
# load
# ---------------------------------------------------------------------------


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    doc = load(tmp_path / "nope.json")
    assert doc == LoadedDocument(text="", line_ids=[])


def test_load_malformed_json_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    assert load(p) == LoadedDocument(text="", line_ids=[])


def test_load_wrong_schema_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "wrong.json"
    p.write_text(json.dumps([{"a": 1}]))
    assert load(p) == LoadedDocument(text="", line_ids=[])


def test_load_round_trip(tmp_path: Path) -> None:
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "lines": [
            {"id": "a", "text": "hello"},
            {"id": "b", "text": "world"},
        ]
    }))
    doc = load(p)
    assert doc.text == "hello\nworld"
    assert doc.line_ids == ["a", "b"]


def test_load_handles_missing_id(tmp_path: Path) -> None:
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"lines": [{"text": "hi"}]}))
    doc = load(p)
    assert doc.text == "hi"
    assert len(doc.line_ids) == 1
    assert doc.line_ids[0]  # some id was allocated


# ---------------------------------------------------------------------------
# save (atomic + round-trip)
# ---------------------------------------------------------------------------


def test_save_writes_json(tmp_path: Path) -> None:
    p = tmp_path / "doc.json"
    ids = save(p, "hello\nworld")
    assert len(ids) == 2
    raw = json.loads(p.read_text())
    assert [line["text"] for line in raw["lines"]] == ["hello", "world"]
    assert [line["id"] for line in raw["lines"]] == ids


def test_save_empty_string_writes_empty_lines(tmp_path: Path) -> None:
    p = tmp_path / "doc.json"
    ids = save(p, "")
    assert ids == []
    raw = json.loads(p.read_text())
    assert raw == {"lines": []}


def test_save_then_load_round_trip(tmp_path: Path) -> None:
    p = tmp_path / "doc.json"
    save(p, "alpha\nbeta\ngamma")
    doc = load(p)
    assert doc.text == "alpha\nbeta\ngamma"
    assert len(doc.line_ids) == 3


def test_save_does_not_leave_tmp_file(tmp_path: Path) -> None:
    p = tmp_path / "doc.json"
    save(p, "hello")
    assert not (tmp_path / "doc.json.tmp").exists()


# ---------------------------------------------------------------------------
# Stable line IDs.
# ---------------------------------------------------------------------------


def test_assign_line_ids_reuses_ids_for_unchanged_lines() -> None:
    previous = [("alpha", "id-a"), ("beta", "id-b")]
    new_lines = ["alpha", "beta"]
    ids = assign_line_ids(previous, new_lines)
    assert ids == ["id-a", "id-b"]


def test_assign_line_ids_allocates_for_new_lines() -> None:
    previous = [("alpha", "id-a")]
    new_lines = ["alpha", "newcomer"]
    ids = assign_line_ids(previous, new_lines)
    assert ids[0] == "id-a"
    assert ids[1] != "id-a"
    assert len(ids[1]) == 32  # uuid hex length


def test_assign_line_ids_handles_split() -> None:
    """Split a line: original id stays with one half, new id for the other."""

    previous = [("alpha beta", "id-orig")]
    new_lines = ["alpha", "beta"]
    ids = assign_line_ids(previous, new_lines)
    # Neither half matches "alpha beta" exactly, so both get fresh ids.
    assert ids[0] != "id-orig"
    assert ids[1] != "id-orig"
    assert ids[0] != ids[1]


def test_assign_line_ids_handles_duplicates() -> None:
    previous = [("foo", "id-1"), ("foo", "id-2")]
    new_lines = ["foo", "foo", "foo"]
    ids = assign_line_ids(previous, new_lines)
    assert ids[0] == "id-1"
    assert ids[1] == "id-2"
    assert ids[2] not in {"id-1", "id-2"}  # fresh id for the third copy


def test_save_with_previous_pairs_preserves_ids(tmp_path: Path) -> None:
    p = tmp_path / "doc.json"
    initial_ids = save(p, "alpha\nbeta")
    previous = [("alpha", initial_ids[0]), ("beta", initial_ids[1])]
    # Add a line in the middle; alpha and beta should keep their ids.
    next_ids = save(p, "alpha\nmiddle\nbeta", previous_pairs=previous)
    assert next_ids[0] == initial_ids[0]
    assert next_ids[2] == initial_ids[1]
    assert next_ids[1] not in initial_ids


# ---------------------------------------------------------------------------
# rename
# ---------------------------------------------------------------------------


def test_rename_moves_file(tmp_path: Path) -> None:
    p = tmp_path / "old.json"
    p.write_text("{}")
    new_path = rename(p, "new.json")
    assert new_path == tmp_path / "new.json"
    assert new_path.exists()
    assert not p.exists()


def test_rename_rejects_path_separators(tmp_path: Path) -> None:
    p = tmp_path / "old.json"
    p.write_text("{}")
    with pytest.raises(StorageError):
        rename(p, "subdir/new.json")
    with pytest.raises(StorageError):
        rename(p, "..")


def test_rename_rejects_existing_target(tmp_path: Path) -> None:
    p = tmp_path / "old.json"
    p.write_text("{}")
    other = tmp_path / "taken.json"
    other.write_text("{}")
    with pytest.raises(StorageError):
        rename(p, "taken.json")


def test_rename_to_same_name_is_noop(tmp_path: Path) -> None:
    p = tmp_path / "doc.json"
    p.write_text("{}")
    result = rename(p, "doc.json")
    assert result == p
    assert p.exists()


def test_rename_empty_filename_rejected(tmp_path: Path) -> None:
    p = tmp_path / "doc.json"
    p.write_text("{}")
    with pytest.raises(StorageError):
        rename(p, "")
