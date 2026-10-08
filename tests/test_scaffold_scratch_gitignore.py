"""STORY-712 (v1.17.2 P-14) — consumer scaffolds keep scratch dirs out of git.

`init` never touches a consumer's root `.gitignore`, so machine-local scratch
under `.specflow/` (`checklist-log/`, `locks/`) is ignored the way `locks/`
already was: a per-directory `.gitignore` containing `*` plus `!.gitignore`,
so the ignore file itself is committed and still applies in a clone. An
existing user-authored file there is left alone; the legacy self-ignoring
bare `*` form is upgraded.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from specflow.commands import init as init_cmd
from specflow.lib import scaffold as scaffold_lib

EXPECTED = "*\n!.gitignore\n"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )


def _init(tmp_path: Path) -> Path:
    root = tmp_path / "p"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    return root


def test_init_writes_scratch_gitignores(tmp_path: Path):
    root = _init(tmp_path)
    for d in ("checklist-log", "locks"):
        ignore = root / ".specflow" / d / ".gitignore"
        assert ignore.is_file(), f"{d}/.gitignore missing after init"
        assert ignore.read_text(encoding="utf-8") == EXPECTED
    assert "checklist-log" in scaffold_lib.SCRATCH_DIRS


def test_existing_scratch_gitignore_is_preserved(tmp_path: Path):
    d = tmp_path / ".specflow" / "checklist-log"
    d.mkdir(parents=True)
    (d / ".gitignore").write_text("# mine\n!keep.yaml\n", encoding="utf-8")
    assert scaffold_lib.ensure_scratch_gitignore(d) is False
    assert (d / ".gitignore").read_text(encoding="utf-8") == "# mine\n!keep.yaml\n"
    # A re-run of init on top (merge mode) must not overwrite it either.
    root = tmp_path
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    assert (d / ".gitignore").read_text(encoding="utf-8") == "# mine\n!keep.yaml\n"


def test_ensure_scratch_gitignore_creates_dir_and_file(tmp_path: Path):
    d = tmp_path / "fresh" / "checklist-log"
    assert scaffold_lib.ensure_scratch_gitignore(d) is True
    assert (d / ".gitignore").read_text(encoding="utf-8") == EXPECTED
    assert scaffold_lib.ensure_scratch_gitignore(d) is False


def test_legacy_self_ignoring_star_is_upgraded(tmp_path: Path):
    """A bare ``*`` (pre-v1.17.2 / lib/locks.py form) ignores itself and never
    ships in a clone; it is machine-written, so upgrade it in place."""
    d = tmp_path / ".specflow" / "locks"
    d.mkdir(parents=True)
    (d / ".gitignore").write_text("*\n", encoding="utf-8")
    assert scaffold_lib.ensure_scratch_gitignore(d) is True
    assert (d / ".gitignore").read_text(encoding="utf-8") == EXPECTED


@pytest.mark.skipif(shutil.which("git") is None, reason="git not on PATH")
def test_scratch_gitignore_is_tracked_and_ignores_logs_in_git(tmp_path: Path):
    """The reviewer's clone scenario: after init + commit the ignore file is in
    ``git ls-files`` (so a teammate's checkout has it) while a checklist log
    written next to it is ignored."""
    root = _init(tmp_path)
    assert _git(root, "init", "-q").returncode == 0
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")

    log = root / ".specflow" / "checklist-log" / "2026-01-01T00-00-00Z_check-REQ-001.yaml"
    log.write_text("overall: passed\n", encoding="utf-8")
    lock = root / ".specflow" / "locks" / "mutation.lock"
    lock.write_text("", encoding="utf-8")

    for scratch in (log, lock):
        res = _git(root, "check-ignore", "-q", str(scratch.relative_to(root)))
        assert res.returncode == 0, f"{scratch.relative_to(root)} is not ignored"

    assert _git(root, "add", "-A").returncode == 0
    assert _git(root, "commit", "-q", "-m", "scaffold").returncode == 0
    tracked = set(_git(root, "ls-files").stdout.split())
    assert ".specflow/checklist-log/.gitignore" in tracked
    assert ".specflow/locks/.gitignore" in tracked
    assert ".specflow/checklist-log/2026-01-01T00-00-00Z_check-REQ-001.yaml" not in tracked
    assert ".specflow/locks/mutation.lock" not in tracked

    # A fresh clone carries the ignore file, so logs written there stay untracked.
    clone = tmp_path / "clone"
    assert _git(tmp_path, "clone", "-q", str(root), str(clone)).returncode == 0
    assert (clone / ".specflow" / "checklist-log" / ".gitignore").read_text(encoding="utf-8") == EXPECTED
    (clone / ".specflow" / "checklist-log" / "later.yaml").write_text("x\n", encoding="utf-8")
    assert ".specflow/checklist-log/later.yaml" not in _git(clone, "status", "--porcelain").stdout
