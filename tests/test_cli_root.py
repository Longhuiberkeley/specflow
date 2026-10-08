"""STORY-713 / F-027: `specflow` resolves the project root by walking up.

Before v1.17.2 every handler used ``Path.cwd()`` as the project root, so
``cd _specflow/work && specflow trace DEC-001`` answered "Artifact 'DEC-001'
not found". The root is now the nearest directory (cwd or an ancestor) that
holds ``.specflow/``; ``init`` alone keeps scaffolding the current directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specflow import cli


def _scaffold(tmp_path: Path, monkeypatch, name: str = "proj") -> Path:
    root = tmp_path / name
    root.mkdir()
    monkeypatch.chdir(root)
    assert cli.main(["init", "--platform", "claude-code", "--no-ci"]) == 0
    assert cli.main(["create", "--type", "requirement", "--title", "Root walk-up"]) == 0
    return root


def test_find_project_root_walks_up_from_artifact_dir(tmp_path, monkeypatch):
    root = _scaffold(tmp_path, monkeypatch)
    work = root / "_specflow" / "work" / "stories"
    assert work.is_dir()
    monkeypatch.chdir(work)
    assert cli._find_project_root() == root.resolve()


def test_find_project_root_from_nested_non_project_dir(tmp_path, monkeypatch):
    root = _scaffold(tmp_path, monkeypatch)
    nested = root / "src" / "pkg" / "deep"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    assert cli._find_project_root() == root.resolve()
    # The explicit-start form is what tests and embedders use.
    assert cli._find_project_root(nested) == root.resolve()


def test_find_project_root_without_project_is_cwd(tmp_path, monkeypatch):
    plain = tmp_path / "plain" / "sub"
    plain.mkdir(parents=True)
    monkeypatch.chdir(plain)
    assert cli._find_project_root() == plain.resolve()


def test_nearest_project_wins_over_an_outer_one(tmp_path, monkeypatch):
    outer = _scaffold(tmp_path, monkeypatch, "outer")
    inner = outer / "inner"
    inner.mkdir()
    monkeypatch.chdir(inner)
    assert cli.main(["init", "--platform", "claude-code", "--no-ci"]) == 0
    monkeypatch.chdir(inner / "_specflow")
    assert cli._find_project_root() == inner.resolve()


def test_trace_and_status_work_from_inside_specflow_dir(tmp_path, monkeypatch, capsys):
    root = _scaffold(tmp_path, monkeypatch)
    monkeypatch.chdir(root / "_specflow" / "specs" / "requirements")
    capsys.readouterr()
    assert cli.main(["trace", "REQ-001"]) == 0
    out = capsys.readouterr().out
    assert "REQ-001" in out and "not found" not in out
    assert cli.main(["status"]) == 0
    assert "not initialized" not in capsys.readouterr().out


def test_commands_without_project_keep_their_message(tmp_path, monkeypatch, capsys):
    plain = tmp_path / "nowhere"
    plain.mkdir()
    monkeypatch.chdir(plain)
    assert cli.main(["status"]) == 1
    assert "not initialized" in capsys.readouterr().out
    # A command that needs no project is unaffected by the walk-up.
    assert cli.main(["schema", "requirement"]) in (0, 1)


def test_init_keeps_cwd_and_notes_enclosing_project(tmp_path, monkeypatch, capsys):
    outer = _scaffold(tmp_path, monkeypatch, "outer")
    nested = outer / "apps" / "svc"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    capsys.readouterr()
    assert cli.main(["init", "--platform", "claude-code", "--no-ci"]) == 0
    out = capsys.readouterr().out
    assert (nested / ".specflow").is_dir(), "init must scaffold the current directory, not the ancestor"
    assert "already a SpecFlow project" in out and str(outer.resolve()) in out
    # Outer project untouched by the nested init.
    assert (outer / "_specflow" / "specs" / "requirements" / "REQ-001.md").exists()


def test_init_in_a_fresh_dir_prints_no_note(tmp_path, monkeypatch, capsys):
    root = tmp_path / "fresh"
    root.mkdir()
    monkeypatch.chdir(root)
    assert cli.main(["init", "--platform", "claude-code", "--no-ci"]) == 0
    assert "already a SpecFlow project" not in capsys.readouterr().out


@pytest.mark.parametrize("argv", [["standards"], ["standards", "--help"]])
def test_standards_bare_is_not_silent(argv, capsys):
    """F-069: a bare `specflow standards` used to exit 1 with no output."""
    try:
        rc = cli.main(argv)
    except SystemExit as exc:  # --help exits 0 via argparse
        rc = exc.code
    captured = capsys.readouterr()
    if argv == ["standards"]:
        assert rc == 1
        assert "standards subcommand required (gaps)" in captured.err
    else:
        assert rc == 0 and "gaps" in captured.out
