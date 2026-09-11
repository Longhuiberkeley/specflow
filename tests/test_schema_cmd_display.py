"""STORY-652 follow-up (second-opinion review): the `specflow schema` display
must mirror :func:`specflow.lib.artifacts.entry_statuses` exactly.

The prior display printed a declared ``initial_statuses`` list verbatim, while
creation filtered invalid entries and fell back to computed roots — so an
empty or all-invalid declared list displayed bogus entry points that create
would never use. These tests pin the display to the effective entry statuses.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.commands import schema_cmd

_WIDGET_SCHEMA = {
    "type": "widget",
    "prefix": "WID",
    "directory": "_specflow/widgets/",
    "required_fields": ["id", "title", "type", "status", "created"],
    "allowed_link_roles": ["derives_from"],
}


def _project(tmp_path: Path, initial_statuses=None) -> Path:
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    schema = dict(_WIDGET_SCHEMA)
    schema["allowed_status"] = {
        "draft": [],
        "review": ["draft"],
        "done": ["review", "draft"],
    }
    if initial_statuses is not None:
        schema["initial_statuses"] = initial_statuses
    (schema_dir / "widget.yaml").write_text(yaml.safe_dump(schema))
    return root


def test_initial_statuses_displayed_instead_of_roots(tmp_path, capsys):
    root = _project(tmp_path, ["done"])
    rc = schema_cmd.run(root, {"type": "widget"})
    assert rc == 0
    out = capsys.readouterr().out
    assert "Initial status(es)" in out
    assert "done" in out
    assert "Root status(es)" not in out


def test_empty_initial_statuses_falls_back_to_roots(tmp_path, capsys):
    root = _project(tmp_path, [])
    rc = schema_cmd.run(root, {"type": "widget"})
    assert rc == 0
    out = capsys.readouterr().out
    assert "Root status(es)" in out
    assert "Initial status(es)" not in out


def test_all_invalid_initial_statuses_fall_back_to_roots(tmp_path, capsys):
    root = _project(tmp_path, ["nope", "also_nope"])
    rc = schema_cmd.run(root, {"type": "widget"})
    assert rc == 0
    out = capsys.readouterr().out
    assert "Root status(es)" in out
    assert "Initial status(es)" not in out


def test_absent_key_shows_roots_unchanged(tmp_path, capsys):
    root = _project(tmp_path)
    rc = schema_cmd.run(root, {"type": "widget"})
    assert rc == 0
    out = capsys.readouterr().out
    assert "Root status(es)" in out
    assert "Initial status(es)" not in out
