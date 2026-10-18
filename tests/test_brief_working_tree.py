"""`specflow brief` reports the uncommitted working tree (STORY-739, REQ-067 OBL-2 / AC3).

Buckets: ``_specflow/`` (ledger), ``.specflow/`` (engine state, informational
only) and everything else (source). The rendered brief prints a "Working tree"
line and ``brief --next`` appends one advisory line only when the ledger or
source bucket is non-empty; exit codes never change.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from specflow.commands import brief as brief_cmd
from specflow.lib import artifacts as art_lib

_STD_FLOW = {"draft": [], "approved": ["draft"], "implemented": ["approved"], "verified": ["implemented"]}
_SCHEMA_TYPES = [("requirement", "REQ"), ("story", "STORY")]


@pytest.fixture(autouse=True)
def _isolated_git(monkeypatch, tmp_path: Path):
    """Keep the user's global/system git config (gpgsign, hooksPath) out of
    the fixture repos, and stop repo discovery from climbing above tmp_path."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))


def _git(repo: Path, *args: str, tmp_path: Path) -> None:
    assert repo.resolve().is_relative_to(tmp_path.resolve())
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
         "-c", "commit.gpgsign=false", *args],
        check=True, capture_output=True, text=True,
    )


def _scaffold(root: Path) -> Path:
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    for art_type, prefix in _SCHEMA_TYPES:
        schema = {"type": art_type, "prefix": prefix, "allowed_status": dict(_STD_FLOW),
                  "category": "work" if prefix == "STORY" else "spec"}
        (schema_dir / f"{art_type}.yaml").write_text(yaml.dump(schema), encoding="utf-8")
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump({"project": {"name": "wt-test"}, "artifact_types": [t for t, _ in _SCHEMA_TYPES],
                   "active_packs": []}),
        encoding="utf-8",
    )
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "planning", "history": []}), encoding="utf-8")
    for sub in ("_specflow/specs/requirements", "_specflow/work/stories"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    art_lib.create_artifact(root, "requirement", title="A req", status="approved", body="b")
    return root


def _committed(repo: Path, tmp_path: Path) -> None:
    _git(repo, "add", "-A", tmp_path=tmp_path)
    _git(repo, "commit", "-q", "-m", "init", tmp_path=tmp_path)


@pytest.fixture
def git_project(tmp_path: Path) -> Path:
    root = _scaffold(tmp_path / "project")
    _git(root, "init", "-q", tmp_path=tmp_path)
    _committed(root, tmp_path)
    return root


def _brief(root: Path, capsys, **args) -> tuple[int, str]:
    rc = brief_cmd.run(root, args)
    return rc, capsys.readouterr().out


def _next(root: Path, capsys) -> tuple[int, list[str]]:
    rc, out = _brief(root, capsys, next=True)
    return rc, [ln for ln in out.splitlines() if ln.strip()]


# ── AC: clean tree → no line ──────────────────────────────────────────

def test_clean_tree_prints_no_working_tree_line(git_project: Path, capsys):
    assert brief_cmd._working_tree(git_project) == {"ledger": [], "source": [], "engine": []}
    rc, out = _brief(git_project, capsys)
    assert rc == 0
    assert "Working tree" not in out
    rc, lines = _next(git_project, capsys)
    assert rc == 0
    assert not any("Working tree" in ln for ln in lines)


# ── AC1 / AC2: ledger + source ────────────────────────────────────────

def test_ledger_and_source_changes_reported_with_counts(git_project: Path, capsys):
    _, baseline = _next(git_project, capsys)
    art_lib.create_artifact(git_project, "story", title="New story", status="draft", body="b")
    (git_project / "src").mkdir()
    (git_project / "src" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    (git_project / "tests").mkdir()
    (git_project / "tests" / "test_mod.py").write_text("def test(): pass\n", encoding="utf-8")

    tree = brief_cmd._working_tree(git_project)
    assert tree is not None
    assert sorted(tree["source"]) == ["src/mod.py", "tests/test_mod.py"]
    assert tree["ledger"] and all(p.startswith("_specflow/") for p in tree["ledger"])
    n_ledger = len(tree["ledger"])

    rc, out = _brief(git_project, capsys)
    assert rc == 0
    wt = [ln for ln in out.splitlines() if "Working tree" in ln]
    assert len(wt) == 1
    assert f"{n_ledger} _specflow/" in wt[0] and "2 source" in wt[0]
    # Answer-first: the line sits in the → Next block, above the inventory.
    assert out.index("Working tree") < out.index("Inventory")

    rc, lines = _next(git_project, capsys)
    assert rc == 0
    assert lines[0] == baseline[0]  # first --next line unchanged
    assert lines[-1] == (
        f"Working tree: {n_ledger} uncommitted _specflow/ path(s) and 2 source path(s) "
        "— commit or review before shipping"
    )
    assert sum("Working tree" in ln for ln in lines) == 1


def test_ledger_only_change(git_project: Path, capsys):
    req = next((git_project / "_specflow/specs/requirements").glob("REQ-*.md"))
    req.write_text(req.read_text(encoding="utf-8") + "\nedited\n", encoding="utf-8")
    _, out = _brief(git_project, capsys)
    assert "1 _specflow/ · 0 source uncommitted" in out
    rc, lines = _next(git_project, capsys)
    assert rc == 0
    assert lines[-1].startswith("Working tree: 1 uncommitted _specflow/ path(s) and 0 source path(s)")


def test_source_only_change(git_project: Path, capsys):
    (git_project / "README.md").write_text("hi\n", encoding="utf-8")
    _, out = _brief(git_project, capsys)
    assert "0 _specflow/ · 1 source uncommitted — e.g. README.md" in out
    rc, lines = _next(git_project, capsys)
    assert rc == 0
    assert lines[-1].startswith("Working tree: 0 uncommitted _specflow/ path(s) and 1 source path(s)")


# ── AC3: .specflow/-only → silent ─────────────────────────────────────

def test_engine_only_changes_stay_silent(git_project: Path, capsys):
    (git_project / ".specflow" / "cache.yaml").write_text("k: v\n", encoding="utf-8")
    state = git_project / ".specflow" / "state.yaml"
    state.write_text(state.read_text(encoding="utf-8") + "# touched\n", encoding="utf-8")
    tree = brief_cmd._working_tree(git_project)
    assert tree is not None and len(tree["engine"]) == 2
    assert not tree["ledger"] and not tree["source"]
    rc, out = _brief(git_project, capsys)
    assert rc == 0 and "Working tree" not in out
    rc, lines = _next(git_project, capsys)
    assert rc == 0 and not any("Working tree" in ln for ln in lines)


def test_engine_count_rides_along_when_other_buckets_dirty(git_project: Path, capsys):
    (git_project / ".specflow" / "cache.yaml").write_text("k: v\n", encoding="utf-8")
    (git_project / "app.py").write_text("x\n", encoding="utf-8")
    _, out = _brief(git_project, capsys)
    assert "0 _specflow/ · 1 source · 1 .specflow/ (engine) uncommitted — e.g. app.py" in out


# ── AC4: not a git repository ─────────────────────────────────────────

def test_not_a_git_repo_prints_nothing_and_does_not_fail(tmp_path: Path, capsys):
    root = _scaffold(tmp_path / "plain")
    (root / "src").mkdir()
    (root / "src" / "a.py").write_text("x\n", encoding="utf-8")
    assert brief_cmd._working_tree(root) is None
    rc, out = _brief(root, capsys)
    assert rc == 0 and "Working tree" not in out
    rc, lines = _next(root, capsys)
    assert rc == 0 and not any("Working tree" in ln for ln in lines)


def test_unborn_repo_prints_nothing(tmp_path: Path, capsys):
    """A repo with no commit yet is setup, not drift: no line, no advisory."""
    root = _scaffold(tmp_path / "fresh")
    _git(root, "init", "-q", tmp_path=tmp_path)
    assert brief_cmd._working_tree(root) is None
    rc, out = _brief(root, capsys)
    assert rc == 0
    assert "Working tree" not in out
    rc, out = _brief(root, capsys, next=True)
    assert rc == 0
    assert "Working tree" not in out


def test_git_missing_degrades_to_none(git_project: Path, monkeypatch):
    def _boom(*a, **k):
        raise FileNotFoundError("git")
    monkeypatch.setattr(brief_cmd.subprocess, "run", _boom)
    assert brief_cmd._working_tree(git_project) is None


# ── Composition: project nested inside a larger repo ─────────────────

def test_nested_project_buckets_relative_to_project_root(tmp_path: Path, capsys):
    mono = tmp_path / "mono"
    root = _scaffold(mono / "services" / "app")
    _git(mono, "init", "-q", tmp_path=tmp_path)
    _committed(mono, tmp_path)
    (mono / "outside.txt").write_text("not ours\n", encoding="utf-8")
    req = next((root / "_specflow/specs/requirements").glob("REQ-*.md"))
    req.write_text(req.read_text(encoding="utf-8") + "\nedited\n", encoding="utf-8")
    tree = brief_cmd._working_tree(root)
    assert tree is not None
    assert tree["ledger"] == [str(req.relative_to(root))]
    assert tree["source"] == []  # outside.txt is above the project root


def test_rename_and_quoted_paths_parse(monkeypatch, tmp_path: Path):
    class _R:
        returncode = 0
        stdout = ('R  _specflow/old.md -> _specflow/new.md\n'
                  '?? "src/with space.py"\n'
                  ' M .specflow/state.yaml\n')
    monkeypatch.setattr(brief_cmd.subprocess, "run", lambda *a, **k: _R())
    assert brief_cmd._working_tree(tmp_path) == {
        "ledger": ["_specflow/new.md"],
        "source": ["src/with space.py"],
        "engine": [".specflow/state.yaml"],
    }
