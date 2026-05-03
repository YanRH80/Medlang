"""Document persistence: atomic JSON load/save with stable line IDs.

Scope
-----
Owns reading and writing the line-list JSON document on disk. Each line
carries an opaque `id` that survives unrelated edits, so downstream tools
can reference lines without losing track when other lines change.

Responsibilities
- `load(path)`            -> (text, [ids]) tuple
- `save(path, text, ids)` -> writes atomically (temp + rename), returns the
                             new id list (newly allocated where needed).
- `rename(old, new)`      -> moves the file on disk, returns the new path.

Boundaries
----------
- Does NOT depend on Textual or any UI widget. Pure I/O over plain types.
- Does NOT decide *when* to save. Callers (the app) drive that.
- Does NOT enforce a schema beyond `{"lines": [{"id": str, "text": str}, ...]}`.

Freeze criteria
---------------
This module can be considered frozen once:
- `load` recovers gracefully from missing files, malformed JSON, and the
  schema variations we have shipped historically.
- `save` is atomic: a crash mid-write leaves the previous file untouched.
- Stable IDs: `assign_line_ids(old_pairs, new_lines)` reuses ids for
  unchanged lines and only allocates fresh UUIDs for genuinely new lines.
- `rename` validates the target before touching the filesystem.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class LoadedDocument:
    """Result of loading a document: text plus aligned ids."""

    text: str
    line_ids: list[str]


@dataclass(frozen=True)
class StorageError(Exception):
    """Raised for recoverable storage failures (load, save, rename)."""

    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


def _new_id() -> str:
    """Return a fresh opaque line id."""

    return uuid.uuid4().hex


def assign_line_ids(
    previous: Iterable[tuple[str, str]],
    new_lines: list[str],
) -> list[str]:
    """Reuse ids for lines whose text already existed; allocate new ids elsewhere.

    `previous` is an iterable of `(text, id)` pairs from the last known
    state. Each id is consumed at most once, so duplicates in the new list
    only inherit one previous id and the rest get fresh uuids.
    """

    available: dict[str, list[str]] = {}
    for text, line_id in previous:
        available.setdefault(text, []).append(line_id)

    result: list[str] = []
    for line in new_lines:
        bucket = available.get(line)
        if bucket:
            result.append(bucket.pop(0))
            if not bucket:
                del available[line]
        else:
            result.append(_new_id())
    return result


def load(path: Path) -> LoadedDocument:
    """Load a document from disk.

    Returns an empty document if the file does not exist. Falls back to an
    empty document on JSON or schema errors so the editor can still open.
    """

    if not path.exists():
        return LoadedDocument(text="", line_ids=[])

    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return LoadedDocument(text="", line_ids=[])

    if not isinstance(raw, dict):
        return LoadedDocument(text="", line_ids=[])

    lines = raw.get("lines")
    if not isinstance(lines, list):
        return LoadedDocument(text="", line_ids=[])

    line_texts: list[str] = []
    line_ids: list[str] = []
    for item in lines:
        if not isinstance(item, dict):
            continue
        line_texts.append(str(item.get("text", "")))
        line_ids.append(str(item.get("id", _new_id())))

    return LoadedDocument(text="\n".join(line_texts), line_ids=line_ids)


def save(
    path: Path,
    text: str,
    previous_pairs: Iterable[tuple[str, str]] = (),
) -> list[str]:
    """Atomically write the document. Returns the line ids written.

    The atomicity guarantee is: if the process crashes mid-write, the
    original `path` is unchanged. We achieve that by writing to a temp file
    and then renaming it onto the target path.

    `previous_pairs` lets us preserve ids across unrelated edits. If empty,
    every line gets a fresh id.
    """

    new_lines = [] if text == "" else text.split("\n")
    line_ids = assign_line_ids(previous_pairs, new_lines)
    payload = {
        "lines": [
            {"id": line_id, "text": line_text}
            for line_id, line_text in zip(line_ids, new_lines, strict=False)
        ]
    }

    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        os.replace(tmp, path)
    except OSError as exc:  # pragma: no cover - filesystem failure
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise StorageError(f"failed to save {path.name}: {exc}") from exc

    return line_ids


def rename(old_path: Path, new_name: str) -> Path:
    """Rename the document on disk. Returns the new path.

    `new_name` must be a bare filename (no directory traversal, no path
    separators). The target file must not already exist.
    """

    if not new_name or "/" in new_name or "\\" in new_name or new_name in {".", ".."}:
        raise StorageError(f"invalid filename: {new_name!r}")

    new_path = old_path.with_name(new_name)
    if new_path == old_path:
        return old_path
    if new_path.exists():
        raise StorageError(f"target already exists: {new_path.name}")

    try:
        if old_path.exists():
            os.replace(old_path, new_path)
        else:
            # Nothing on disk yet; just hand back the new path.
            pass
    except OSError as exc:  # pragma: no cover - filesystem failure
        raise StorageError(f"failed to rename: {exc}") from exc

    return new_path
