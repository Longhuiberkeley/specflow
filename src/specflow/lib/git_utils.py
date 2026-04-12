"""Git subprocess helpers for baseline creation and change-record generation.

Uses plain subprocess calls — no external git library dependency.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


_COMMIT_END = "---SPECFLOW-COMMIT-END---"
_FIELD_SEP = "\x1f"  # ASCII unit separator


def _run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a git command in the given directory, capturing output."""
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=str(root),
        check=False,
    )


def is_git_repo(root: Path) -> bool:
    """Return True if root is inside a git working tree."""
    result = _run_git(root, ["rev-parse", "--is-inside-work-tree"])
    return result.returncode == 0 and result.stdout.strip() == "true"


def get_current_sha(root: Path) -> str:
    """Return the current HEAD SHA, or '' if not a git repo or no HEAD."""
    result = _run_git(root, ["rev-parse", "HEAD"])
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def resolve_ref(root: Path, ref: str) -> str:
    """Resolve a git ref (tag, branch, SHA) to its SHA, or '' if not found."""
    result = _run_git(root, ["rev-parse", "--verify", ref])
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_commits_since(root: Path, since_ref: str) -> list[dict[str, str]]:
    """Return commits from <since_ref>..HEAD as a list of dicts.

    Each dict contains: sha, author_name, author_email, date_iso, subject, body.
    Uses --first-parent to avoid double-reporting merge commits.
    Returns [] if the ref cannot be resolved or there are no commits.
    """
    # Format fields separated by unit separator, commits separated by sentinel
    fmt = _FIELD_SEP.join(["%H", "%an", "%ae", "%aI", "%s", "%b"]) + _COMMIT_END
    result = _run_git(
        root,
        [
            "log",
            f"--format={fmt}",
            "--first-parent",
            f"{since_ref}..HEAD",
        ],
    )
    if result.returncode != 0:
        return []

    commits: list[dict[str, str]] = []
    raw = result.stdout
    for chunk in raw.split(_COMMIT_END):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        parts = chunk.split(_FIELD_SEP)
        if len(parts) < 6:
            continue
        commits.append(
            {
                "sha": parts[0],
                "author_name": parts[1],
                "author_email": parts[2],
                "date_iso": parts[3],
                "subject": parts[4],
                "body": parts[5],
            }
        )
    return commits


def get_changed_files(root: Path, sha: str) -> list[str]:
    """Return the list of files changed in a commit (paths relative to repo root)."""
    result = _run_git(
        root,
        ["diff-tree", "--no-commit-id", "-r", "--name-only", sha],
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def is_spec_artifact_path(file_path: str) -> bool:
    """Return True if the path is a SpecFlow spec-artifact markdown file.

    Artifact files live under _specflow/specs/ or _specflow/work/,
    end with .md, and do not start with an underscore (excludes _index.yaml).
    """
    if not file_path.endswith(".md"):
        return False
    if not (
        file_path.startswith("_specflow/specs/")
        or file_path.startswith("_specflow/work/")
    ):
        return False
    name = file_path.rsplit("/", 1)[-1]
    if name.startswith("_"):
        return False
    return True


def artifact_id_from_path(file_path: str) -> str:
    """Extract the artifact ID from a file path (REQ-001.md -> REQ-001)."""
    name = file_path.rsplit("/", 1)[-1]
    if name.endswith(".md"):
        name = name[:-3]
    return name
