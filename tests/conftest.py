"""Make the project root importable from inside `tests/` and share fixtures.

Scope
-----
- Adds project root to sys.path so `import app` works from any test file.
- Provides the `tmp_document` fixture used by every Pilot integration test.
  Patches `app._load_config` to return a synthetic config pointing at a
  throwaway JSON document, so tests never touch the real `config.yaml`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@pytest.fixture
def tmp_document(tmp_path: Path, monkeypatch):
    """Point the app at a throwaway JSON document for each test."""

    import app as app_module

    doc_path = tmp_path / "doc.json"

    cfg = {
        "app": {"title": "T", "subtitle": "S"},
        "editor": {
            "placeholder": "",
            "soft_wrap": False,
            "show_line_numbers": True,
            "vim_start_mode": "normal",
            "palette": "midnight",
        },
        "storage": {
            "document_path": str(doc_path),
            "auto_save": True,
        },
        "commands": {},
    }

    monkeypatch.setattr(app_module, "_load_config", lambda: (cfg, []))
    return doc_path
