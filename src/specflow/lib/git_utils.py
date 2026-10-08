"""Git subprocess helpers for baseline creation and change-record generation.

Uses plain subprocess calls — no external git library dependency.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


_COMMIT_END = "---SPECFLOW-COMMIT-END---"
_FIELD_SEP = "\x1f"  # ASCII unit separator


def _run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a git command in the given directory, capturing output.

    A machine without a ``git`` binary yields a failed result (returncode 127)
    instead of raising, so every caller degrades to its not-a-repo path.
    """
    try:
        return subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=str(root),
            check=False,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            ["git", *args], 127, "", "git: command not found"
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


def get_commit_timestamp(root: Path, sha: str) -> str | None:
    """Committer timestamp of ``sha`` as strict ISO-8601 (``git show -s
    --format=%cI``, e.g. ``2026-10-08T10:15:00+02:00``), or ``None`` when
    the ref does not resolve, ``root`` is not a repository, or git is absent.
    Offset-aware: callers that compare against UTC strings normalise it."""
    result = _run_git(root, ["show", "-s", "--format=%cI", sha])
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


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


def file_history(
    root: Path,
    file_path: str,
    rev: str,
    *,
    follow: bool = True,
) -> list[dict[str, str]] | None:
    """Return the commits in ``rev`` that touched ``file_path``, oldest first.

    ``rev`` is anything ``git log`` accepts as a revision (``base..head``, a
    SHA, ``HEAD``). ``file_path`` is the path as it exists at the newest end of
    ``rev``; with ``follow`` (the default) renames are followed backwards, so a
    file that ``renumber-drafts`` renamed from ``REQ-FOO-ab12.md`` keeps its
    earlier commits. Each entry is
    ``{sha, author_email, change, old_path, new_path}`` where ``change`` is the
    git status letter (A/M/R/C/D/...) and ``old_path`` is the path in the
    commit's parent ('' for an addition). Commits that touched the file
    without a diff entry (e.g. merges) carry ``change`` ''.

    Returns None when git fails (unknown ref, not a repository).
    """
    args = ["log", "--format=%x00%H%x09%ae", "--name-status"]
    if follow:
        args.append("--follow")
    args += [rev, "--", file_path]
    result = _run_git(root, args)
    if result.returncode != 0:
        return None

    entries: list[dict[str, str]] = []
    for chunk in result.stdout.split("\x00"):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        lines = [ln for ln in chunk.splitlines() if ln.strip()]
        header = lines[0].split("\t", 1)
        sha = header[0].strip()
        email = header[1].strip().lower() if len(header) > 1 else ""
        change, old_path, new_path = "", file_path, file_path
        for ln in lines[1:]:
            parts = ln.split("\t")
            letter = parts[0][:1]
            if letter in ("R", "C") and len(parts) >= 3:
                change, old_path, new_path = letter, parts[1], parts[2]
            elif len(parts) >= 2:
                change, old_path, new_path = letter, parts[1], parts[1]
            if letter == "A":
                old_path = ""
            break
        entries.append({
            "sha": sha,
            "author_email": email,
            "change": change,
            "old_path": old_path,
            "new_path": new_path,
        })
    entries.reverse()
    return entries


def core_hooks_path(root: Path) -> str:
    """Return the configured ``core.hooksPath`` for ``root``, or '' when unset.

    When set (husky, lefthook and similar tools do this), git ignores
    ``.git/hooks`` entirely, so a hook installed there is never run.
    """
    return core_hooks_path_scoped(root)[0]


def core_hooks_path_scoped(root: Path) -> tuple[str, str]:
    """Return ``(core.hooksPath, scope)`` for ``root``; ``('', '')`` when unset.

    ``scope`` is git's config scope (``local``, ``worktree``, ``global``,
    ``system``, ``command``). A global or system hooks path is shared by every
    repository on the machine, so an installer must not write there blindly.
    """
    result = _run_git(root, ["config", "--show-scope", "--get", "core.hooksPath"])
    if result.returncode != 0 or not result.stdout.strip():
        return "", ""
    scope, _, value = result.stdout.strip().partition("\t")
    if not value:  # very old git without --show-scope support printed no scope
        return scope.strip(), ""
    return value.strip(), scope.strip()


def toplevel(root: Path) -> Path | None:
    """Return the top-level directory of the working tree containing ``root``.

    None outside a git working tree (or without a git binary).
    """
    result = _run_git(root, ["rev-parse", "--show-toplevel"])
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip()).resolve()


def hooks_dir(root: Path) -> Path | None:
    """Return the directory git runs hooks from for ``root``, or None.

    ``root`` must be the top level of its working tree: a project nested inside
    another repository (a monorepo subdirectory, a dotfiles repo in ``$HOME``)
    returns None rather than the parent repository's hooks directory, where the
    hook would run with the wrong cwd and silently check nothing.

    Uses ``git rev-parse --git-path hooks`` so linked worktrees (where
    ``root/.git`` is a file pointing at the common dir) and ``core.hooksPath``
    overrides both resolve to the directory git actually reads. The result is
    resolved against ``root`` (git prints it relative to the cwd). Falls back
    to ``root/.git/hooks`` when git itself is unavailable but a ``.git``
    directory exists.
    """
    top = toplevel(root)
    if top is None:
        if (root / ".git").is_dir() and _run_git(root, ["--version"]).returncode == 127:
            return (root / ".git" / "hooks").resolve()
        return None
    if top != root.resolve():
        return None
    result = _run_git(root, ["rev-parse", "--git-path", "hooks"])
    if result.returncode == 0 and result.stdout.strip():
        raw = Path(result.stdout.strip())
        return (raw if raw.is_absolute() else root / raw).resolve()
    if (root / ".git").exists():
        return (root / ".git" / "hooks").resolve()
    return None
