"""Brownfield upgrade fixture (STORY-718, REQ-057).

A consumer repository initialised by the previous release must survive the
engine at HEAD: every read-only command runs on a ``git archive`` of the
latest ``v*`` tag (this repo's own ledger as of that release) without a
traceback and with a documented exit code only. Findings counts are NOT
compared against the archived baseline: new rules legitimately add findings.

The tag is resolved dynamically; where no tag is reachable (shallow clone,
tarball checkout) the module skips rather than fails.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.slow

# command → documented exit codes (docs/cli-reference.md and the handlers)
READ_ONLY_COMMANDS: dict[tuple[str, ...], set[int]] = {
    ("status",): {0, 1},
    ("brief", "--next"): {0, 1},
    ("artifact-lint",): {0, 1},
    ("rtm",): {0},
    ("refresh", "--dry-run"): {0, 1},
    ("project-audit", "--dry-run", "--quick"): {0, 2, 3, 4},
}


def _latest_release_tag() -> str | None:
    result = subprocess.run(
        ["git", "tag", "--list", "v*", "--sort=-v:refname"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return None
    tags = [t for t in result.stdout.split() if t[1:].replace(".", "").isdigit()]
    return tags[0] if tags else None


@pytest.fixture(scope="module")
def archived_release(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, Path]:
    tag = _latest_release_tag()
    if tag is None:
        pytest.skip("no v* release tag reachable (shallow clone or tarball checkout)")
    work = tmp_path_factory.mktemp("brownfield")
    archive = work / "release.tar"
    result = subprocess.run(
        ["git", "archive", "--format=tar", "-o", str(archive), tag],
        cwd=str(REPO_ROOT), capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"git archive {tag} failed: {result.stderr.strip()}")
    root = work / "repo"
    root.mkdir()
    with tarfile.open(archive) as tar:
        tar.extractall(root, filter="data")
    assert (root / ".specflow" / "config.yaml").exists(), "archived release is not a SpecFlow project"
    assert (root / "_specflow").is_dir()
    # A brownfield repo is a git repository with history; recreate the minimum.
    git = ["git", "-c", "user.email=t@example.com", "-c", "user.name=t"]
    subprocess.run([*git, "init", "-q"], cwd=str(root), check=True, capture_output=True)
    subprocess.run([*git, "add", "-A"], cwd=str(root), check=True, capture_output=True)
    subprocess.run([*git, "commit", "-q", "-m", f"archive of {tag}"], cwd=str(root),
                   check=True, capture_output=True)
    return tag, root


def _run_head_engine(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env.setdefault("NO_COLOR", "1")
    return subprocess.run(
        [sys.executable, "-m", "specflow", *args],
        cwd=str(root), capture_output=True, text=True, check=False, env=env, timeout=600,
    )


@pytest.mark.parametrize("command", sorted(READ_ONLY_COMMANDS), ids=lambda c: " ".join(c))
def test_read_only_command_survives_the_previous_release(archived_release, command):
    tag, root = archived_release
    before = sorted(p.relative_to(root) for p in root.rglob("*") if ".git" not in p.parts)
    result = _run_head_engine(root, *command)
    combined = result.stdout + result.stderr
    assert "Traceback (most recent call last)" not in combined, (
        f"specflow {' '.join(command)} crashed on the {tag} ledger:\n{combined[-3000:]}"
    )
    assert result.returncode in READ_ONLY_COMMANDS[command], (
        f"specflow {' '.join(command)} exited {result.returncode} on the {tag} ledger "
        f"(documented: {sorted(READ_ONLY_COMMANDS[command])}):\n{combined[-3000:]}"
    )
    after = sorted(p.relative_to(root) for p in root.rglob("*") if ".git" not in p.parts)
    assert after == before, f"specflow {' '.join(command)} created or deleted files on a read-only run"


def test_previous_release_ledger_needs_no_format_migration(archived_release):
    """The archived release's format_version is one the HEAD engine supports."""
    from specflow.lib import config as config_lib

    _, root = archived_release
    assert config_lib.format_version_mismatch(root) is None
