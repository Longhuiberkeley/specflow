"""specflow hook — Install and run git hooks for RBAC enforcement.

Subcommands:
  specflow hook install       — Write .git/hooks/pre-commit
  specflow hook pre-commit    — Run pre-commit validation (called by the hook)
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import yaml

from specflow.lib import rbac as rbac_lib
from specflow.lib.adapters import load_adapters_config, get_adapter

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
NC = "\033[0m"


def _hook_template(root: Path) -> str:
    config = load_adapters_config(root)
    ci_cfg = config.get("ci") or {}
    provider = ci_cfg.get("provider")

    if provider:
        try:
            adapter = get_adapter(provider)
            if "get_hook_script" in adapter.supported_operations:
                return adapter.get_hook_script()
        except ValueError:
            pass

    return (
        "#!/usr/bin/env bash\n"
        "# specflow pre-commit hook — installed by `specflow hook install`\n"
        "# Delegates to the Python CLI so the logic stays version-controlled.\n"
        "exec uv run specflow hook pre-commit \"$@\"\n"
    )


def _install(root: Path) -> int:
    git_dir = root / ".git"
    if not git_dir.is_dir():
        print(f"{RED}✗ Not a git repository: {root}{NC}")
        return 1

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "pre-commit"
    hook_path.write_text(_hook_template(root), encoding="utf-8")
    mode = hook_path.stat().st_mode
    hook_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"{GREEN}✓ Installed .git/hooks/pre-commit{NC}")
    return 0


def _pre_commit(root: Path) -> int:
    author = os.environ.get("GIT_AUTHOR_EMAIL") or rbac_lib.current_git_author_email(root)
    changes = rbac_lib.staged_artifact_changes(root)
    if not changes:
        return 0

    failures: list[str] = []
    for change in changes:
        path = change["path"]
        old_status = change["old_status"]
        new_status = change["new_status"]

        if not new_status or new_status == old_status:
            continue

        artifact_id = Path(path).stem
        ok, reason = rbac_lib.authorize_status_transition(
            root, artifact_id, new_status, author
        )
        if not ok:
            failures.append(reason)
            continue

        ok, reason = rbac_lib.check_independence(root, path, new_status, author)
        if not ok:
            failures.append(reason)

    if failures:
        print(f"{RED}✗ specflow pre-commit: RBAC check failed{NC}")
        for f in failures:
            print(f"  {RED}•{NC} {f}")
        print(
            f"\n{YELLOW}Note:{NC} the pre-commit hook is advisory. Real enforcement "
            f"requires branch protection + required signed commits on the hosting platform."
        )
        return 1

    return 0


def run(root: Path, args: dict) -> int:
    root = root.resolve()
    sub = args.get("hook_subcommand")
    if sub == "install":
        return _install(root)
    if sub == "pre-commit":
        return _pre_commit(root)
    print(f"{RED}✗ unknown hook subcommand: {sub}{NC}")
    return 1


def run_ci_gate(root: Path, args: dict) -> int:
    """Run RBAC checks against a git diff between two refs (CI server-side gate).

    Uses only git operations -- provider-agnostic.
    """
    root = root.resolve()
    base_ref = args.get("base", "")
    head_ref = args.get("head", "")

    if not base_ref or not head_ref:
        print(f"{RED}✗ --base and --head refs are required{NC}")
        return 1

    diff_result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...{head_ref}"],
        capture_output=True, text=True, cwd=str(root), check=False,
    )
    if diff_result.returncode != 0:
        print(f"{RED}✗ git diff failed: {diff_result.stderr.strip()}{NC}")
        return 1

    changed_files = [
        line.strip() for line in diff_result.stdout.splitlines()
        if line.strip().startswith("_specflow/") and line.strip().endswith(".md")
        and not line.strip().rsplit("/", 1)[-1].startswith("_")
    ]

    if not changed_files:
        print(f"{GREEN}✓ No artifact status changes in this diff{NC}")
        return 0

    log_result = subprocess.run(
        ["git", "log", "--format=%ae", f"{base_ref}..{head_ref}"],
        capture_output=True, text=True, cwd=str(root), check=False,
    )
    authors = [line.strip().lower() for line in log_result.stdout.splitlines() if line.strip()]
    author_email = authors[-1] if authors else ""

    failures: list[str] = []

    for filepath in changed_files:
        old_fm = _parse_ref_frontmatter(root, base_ref, filepath)
        new_fm = _parse_ref_frontmatter(root, head_ref, filepath)

        old_status = (old_fm or {}).get("status", "")
        new_status = (new_fm or {}).get("status", "")

        if not new_status or new_status == old_status:
            continue

        artifact_id = Path(filepath).stem

        ok, reason = rbac_lib.authorize_status_transition(
            root, artifact_id, new_status, author_email
        )
        if not ok:
            failures.append(reason)
            continue

        ok, reason = rbac_lib.check_independence(
            root, filepath, new_status, author_email
        )
        if not ok:
            failures.append(reason)

    if failures:
        print(f"{RED}✗ specflow ci-gate: RBAC check failed{NC}")
        for f in failures:
            print(f"  {RED}•{NC} {f}")
        return 1

    print(f"{GREEN}✓ All artifact status transitions pass RBAC checks{NC}")
    return 0


def _parse_ref_frontmatter(root: Path, ref: str, filepath: str) -> dict | None:
    """Parse YAML frontmatter from a git ref for a specific file."""
    result = subprocess.run(
        ["git", "show", f"{ref}:{filepath}"],
        capture_output=True, text=True, cwd=str(root), check=False,
    )
    if result.returncode != 0:
        return None
    text = result.stdout
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end == -1:
        return None
    try:
        fm = yaml.safe_load(text[3:end])
    except Exception:
        return None
    if not isinstance(fm, dict):
        return None
    return fm
