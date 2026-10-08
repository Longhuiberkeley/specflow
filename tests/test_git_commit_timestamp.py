"""STORY-712 (v1.17.2 P-14) — `git_utils.get_commit_timestamp` is the public
helper for a commit's committer time; `change-impact` uses it (not the private
`_run_git`) and normalises the offset-aware `%cI` value to the impact log's
UTC ``Z`` form.
"""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from specflow.commands import change_impact as change_impact_cmd
from specflow.lib import git_utils

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")

_ENV = {
    "GIT_AUTHOR_DATE": "2026-10-08T10:15:00+02:00",
    "GIT_COMMITTER_DATE": "2026-10-08T10:15:00+02:00",
}


def _git(root: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    import os
    full_env = {**os.environ, **(env or {})}
    return subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True, check=False, env=full_env)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "r"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "T")
    _git(root, "config", "commit.gpgsign", "false")
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    _git(root, "add", "-A")
    assert _git(root, "commit", "-q", "-m", "init").returncode == 0
    # A root commit has no parent, so `diff-tree` lists nothing for it; the
    # commit under test is the second one.
    (root / "app.py").write_text("print(1)\n", encoding="utf-8")
    _git(root, "add", "-A")
    assert _git(root, "commit", "-q", "-m", "add app", env=_ENV).returncode == 0
    return root


def test_get_commit_timestamp_returns_strict_iso_with_offset(repo: Path):
    sha = git_utils.get_current_sha(repo)
    value = git_utils.get_commit_timestamp(repo, sha)
    assert value is not None
    parsed = datetime.fromisoformat(value)
    assert parsed.tzinfo is not None
    assert parsed.astimezone(timezone.utc) == datetime(2026, 10, 8, 8, 15, tzinfo=timezone.utc)
    # HEAD resolves too; the helper takes any ref git show accepts.
    assert git_utils.get_commit_timestamp(repo, "HEAD") == value


def test_get_commit_timestamp_is_none_for_bad_ref_or_non_repo(repo: Path, tmp_path: Path):
    assert git_utils.get_commit_timestamp(repo, "0" * 40) is None
    assert git_utils.get_commit_timestamp(repo, "no-such-ref") is None
    plain = tmp_path / "plain"
    plain.mkdir()
    assert git_utils.get_commit_timestamp(plain, "HEAD") is None


def test_change_impact_uses_public_helper_and_utc_z(repo: Path, monkeypatch):
    calls: list[tuple[Path, str]] = []
    real = git_utils.get_commit_timestamp

    def spy(root: Path, sha: str):
        calls.append((root, sha))
        return real(root, sha)

    monkeypatch.setattr(git_utils, "get_commit_timestamp", spy)
    files, sha, ts = change_impact_cmd._detect_source_file_changes(repo)
    assert files == ["app.py"]
    assert calls == [(repo, sha)]
    # Offset +02:00 normalised to UTC, impact-log format.
    assert ts == "2026-10-08T08:15:00Z"


def test_change_impact_timestamp_empty_when_helper_fails(repo: Path, monkeypatch):
    monkeypatch.setattr(git_utils, "get_commit_timestamp", lambda root, sha: None)
    files, sha, ts = change_impact_cmd._detect_source_file_changes(repo)
    assert files == ["app.py"] and sha and ts == ""


def test_change_impact_no_longer_calls_private_run_git_for_timestamp():
    import inspect
    src = inspect.getsource(change_impact_cmd._detect_source_file_changes)
    assert "_run_git" not in src
    assert "get_commit_timestamp" in src
