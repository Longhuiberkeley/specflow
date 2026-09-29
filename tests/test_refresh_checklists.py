"""STORY-687 fix pass — `specflow refresh --checklists` repairs existing projects.

copy_checklists used to copy only MISSING files, so a project initialised
before a shipped checklist was fixed kept the broken/stale copy forever and
the only remedy was hand-deleting files under `.specflow/`. Now:

- a shipped-name checklist that no longer parses is replaced (backed up first);
- `--force` replaces drifted shipped-name checklists (backed up first);
- a parseable, user-edited checklist is preserved without `--force`;
- user-added (non-shipped) checklists are never touched.
"""

from __future__ import annotations

from pathlib import Path

from specflow import cli
from specflow.commands import init as init_cmd
from specflow.commands import refresh as refresh_cmd
from specflow.lib import checklists as checklists_lib
from specflow.lib import scaffold as scaffold_lib

_TEMPLATES = Path(scaffold_lib.__file__).resolve().parents[1] / "templates"
_SHIPPED = _TEMPLATES / "checklists" / "in-process" / "story-writing.yaml"


def _init(tmp_path: Path) -> Path:
    root = tmp_path / "p"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    return root


def _local(root: Path) -> Path:
    return root / ".specflow" / "checklists" / "in-process" / "story-writing.yaml"


def _backups(root: Path) -> list[Path]:
    return list((root / ".specflow" / "cache" / "backups").rglob("story-writing.yaml"))


def test_refresh_replaces_unparseable_shipped_checklist(tmp_path: Path, capsys):
    root = _init(tmp_path)
    _local(root).write_text("items:\n  - id: X\n   check: [broken\n", encoding="utf-8")

    assert refresh_cmd.run(root, {"platform": "claude-code", "checklists": True}) == 0

    assert _local(root).read_bytes() == _SHIPPED.read_bytes()
    assert _backups(root), "broken copy must be backed up before replacement"
    assert "story-writing.yaml" in capsys.readouterr().out


def test_refresh_preserves_edited_checklist_without_force(tmp_path: Path, capsys):
    root = _init(tmp_path)
    edited = _SHIPPED.read_text(encoding="utf-8") + "\n# local note\n"
    _local(root).write_text(edited, encoding="utf-8")

    assert refresh_cmd.run(root, {"platform": "claude-code", "checklists": True}) == 0

    assert _local(root).read_text(encoding="utf-8") == edited
    assert "--checklists --force" in capsys.readouterr().out


def test_refresh_force_replaces_drifted_checklist(tmp_path: Path):
    root = _init(tmp_path)
    _local(root).write_text(
        _SHIPPED.read_text(encoding="utf-8") + "\n# stale\n", encoding="utf-8"
    )

    assert refresh_cmd.run(
        root, {"platform": "claude-code", "checklists": True, "force": True}
    ) == 0

    assert _local(root).read_bytes() == _SHIPPED.read_bytes()
    assert _backups(root)


def test_refresh_never_touches_user_added_checklist(tmp_path: Path):
    root = _init(tmp_path)
    mine = root / ".specflow" / "checklists" / "in-process" / "my-team.yaml"
    mine.write_text("not: [valid\n", encoding="utf-8")

    assert refresh_cmd.run(
        root, {"platform": "claude-code", "checklists": True, "force": True}
    ) == 0

    assert mine.read_text(encoding="utf-8") == "not: [valid\n"


def test_refresh_dry_run_reports_without_writing(tmp_path: Path, capsys):
    root = _init(tmp_path)
    broken = "items: [\n"
    _local(root).write_text(broken, encoding="utf-8")

    assert refresh_cmd.run(
        root, {"platform": "claude-code", "checklists": True, "dry_run": True}
    ) == 0

    assert _local(root).read_text(encoding="utf-8") == broken
    assert "unparseable" in capsys.readouterr().out


def test_cli_refresh_checklists_force(tmp_path: Path, monkeypatch):
    root = _init(tmp_path)
    _local(root).write_text("items: [\n", encoding="utf-8")
    monkeypatch.chdir(root)
    assert cli.main(["refresh", "--checklists"]) == 0
    assert _local(root).read_bytes() == _SHIPPED.read_bytes()


def test_parse_error_message_names_the_repair_command(tmp_path: Path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("items: [\n", encoding="utf-8")
    checklists_lib.parse_checklist_file(bad)
    assert "specflow refresh --checklists" in capsys.readouterr().err
