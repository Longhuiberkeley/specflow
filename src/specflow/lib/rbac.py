"""Role-based access control for status transitions.

Policy-driven: role names are user-defined in .specflow/config.yaml under the
`team` section. This module stays domain-agnostic — regulated industry packs
(ISO 26262, ASPICE, DO-178C) ship their own role templates.

Solo-dev default: when every role list is empty, all transitions are allowed
and independence checks are skipped. No config change needed to opt out.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import yaml

from specflow.lib.config import read_config


def _team_section(root: Path) -> dict[str, Any]:
    """Return the `team` block from config, or an empty dict."""
    cfg = read_config(root)
    team = cfg.get("team") or {}
    if not isinstance(team, dict):
        return {}
    return team


def _has_configured_roles(team: dict[str, Any]) -> bool:
    """True if at least one role has members — gates enforcement on/off."""
    roles = team.get("roles") or {}
    if not isinstance(roles, dict):
        return False
    for members in roles.values():
        if isinstance(members, list) and members:
            return True
    return False


def resolve_author_roles(root: Path, email: str) -> list[str]:
    """Return the list of role names a given email holds.

    Lookups are case-insensitive on the email. An email can hold multiple roles.
    """
    if not email:
        return []
    team = _team_section(root)
    roles_map = team.get("roles") or {}
    target = email.strip().lower()
    assigned: list[str] = []
    for role_name, members in roles_map.items():
        if not isinstance(members, list):
            continue
        for m in members:
            if isinstance(m, str) and m.strip().lower() == target:
                assigned.append(role_name)
                break
    return assigned


def authorize_status_transition(
    root: Path,
    artifact_id: str,
    new_status: str,
    author_email: str,
) -> tuple[bool, str]:
    """Check whether the given author may set `new_status` on `artifact_id`.

    Returns (True, "") if allowed, else (False, reason).
    Solo-dev fast path: no roles configured → always allowed.
    """
    team = _team_section(root)
    if not _has_configured_roles(team):
        return (True, "")

    policy = team.get("policy") or {}
    transitions = policy.get("transitions") or {}
    required_roles = transitions.get(new_status) or []
    if not required_roles:
        # No policy for this transition → allowed
        return (True, "")

    author_roles = resolve_author_roles(root, author_email)
    for role in author_roles:
        if role in required_roles:
            return (True, "")

    allowed = ", ".join(required_roles)
    roles_map = team.get("roles") or {}
    members: list[str] = []
    for role in required_roles:
        for m in roles_map.get(role) or []:
            if isinstance(m, str):
                members.append(m)

    reason = (
        f"{artifact_id}: author '{author_email}' lacks required role for "
        f"'{new_status}' transition. Needs one of: {allowed}. "
        f"Authorized: {', '.join(members) if members else '(none)'}"
    )
    return (False, reason)


def _run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=str(root),
        check=False,
    )


def check_independence(
    root: Path,
    artifact_file: str,
    new_status: str,
    author_email: str,
) -> tuple[bool, str]:
    """Block verifier == implementer when transitioning to a verification status.

    An artifact's "implementers" are the set of author emails that have
    previously committed to the artifact's file. If the current author appears
    in that set AND the transition is to a status marked as a verification
    status, the commit is rejected.

    Verification statuses are declared in config.team.policy.verification_statuses
    (default: ["verified"]).

    Solo-dev fast path: no roles configured → always allowed.
    """
    team = _team_section(root)
    if not _has_configured_roles(team):
        return (True, "")

    policy = team.get("policy") or {}
    verification_statuses = policy.get("verification_statuses") or ["verified"]
    if new_status not in verification_statuses:
        return (True, "")

    result = _run_git(root, ["log", "--format=%ae", "--", artifact_file])
    if result.returncode != 0:
        return (True, "")

    prior_authors = {
        line.strip().lower()
        for line in result.stdout.splitlines()
        if line.strip()
    }
    if author_email.strip().lower() in prior_authors:
        return (
            False,
            f"Independence violation: '{author_email}' implemented {artifact_file} "
            f"and cannot also verify it (implementer != verifier).",
        )
    return (True, "")


def check_gpg_signature(root: Path, commit_ref: str = "HEAD") -> dict[str, Any]:
    """Return GPG signature info for a commit.

    Uses `git verify-commit` (returns 0 only if signed AND trusted).
    When the commit is signed but untrusted, we still surface the key ID.
    """
    verify = _run_git(root, ["verify-commit", "--raw", commit_ref])
    signed = verify.returncode == 0

    show = _run_git(
        root,
        ["log", "-1", "--format=%GK|%GS|%G?", commit_ref],
    )
    key_id = ""
    signer = ""
    status_char = ""
    if show.returncode == 0 and show.stdout.strip():
        parts = show.stdout.strip().split("|", 2)
        if len(parts) == 3:
            key_id, signer, status_char = parts

    return {
        "signed": signed or status_char in ("G", "U", "X", "Y"),
        "trusted": signed,
        "key_id": key_id,
        "signer": signer,
        "status": status_char,
    }


def current_git_author_email(root: Path) -> str:
    """Return the configured git author email for this repo."""
    result = _run_git(root, ["config", "user.email"])
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def staged_artifact_changes(root: Path) -> list[dict[str, Any]]:
    """Return frontmatter diffs for staged _specflow/**.md files.

    For each staged file, returns:
      {path, old_status, new_status, old_fm, new_fm}
    `old_*` values are taken from `HEAD:<path>` (empty/None if file is new).
    `new_*` values are taken from the staged index (`:<path>`).
    """
    diff = _run_git(root, ["diff", "--cached", "--name-only", "--diff-filter=AM"])
    if diff.returncode != 0:
        return []

    changes: list[dict[str, Any]] = []
    for line in diff.stdout.splitlines():
        path = line.strip()
        if not path:
            continue
        if not path.startswith("_specflow/"):
            continue
        if not path.endswith(".md"):
            continue
        name = path.rsplit("/", 1)[-1]
        if name.startswith("_"):
            continue

        new_fm = _parse_staged_frontmatter(root, f":{path}")
        old_fm = _parse_staged_frontmatter(root, f"HEAD:{path}")

        changes.append(
            {
                "path": path,
                "old_status": (old_fm or {}).get("status", ""),
                "new_status": (new_fm or {}).get("status", ""),
                "old_fm": old_fm or {},
                "new_fm": new_fm or {},
            }
        )
    return changes


def _parse_staged_frontmatter(root: Path, spec: str) -> dict[str, Any] | None:
    """Read `git show <spec>` and parse its YAML frontmatter."""
    result = _run_git(root, ["show", spec])
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


def render_codeowners(root: Path) -> str:
    """Render a CODEOWNERS file body from team.roles + policy.directory_ownership.

    Returns an empty string if no roles are configured (signal to skip writing).
    """
    team = _team_section(root)
    if not _has_configured_roles(team):
        return ""

    roles = team.get("roles") or {}
    policy = team.get("policy") or {}
    ownership: dict[str, list[str]] = policy.get("directory_ownership") or {}

    lines: list[str] = [
        "# CODEOWNERS — generated by specflow init from .specflow/config.yaml",
        "# Edit team.policy.directory_ownership in config to change these mappings.",
        "",
    ]

    # If no explicit mapping, default to: every spec dir is owned by all reviewers+approvers.
    if not ownership:
        default_roles = [r for r in ("reviewer", "approver") if roles.get(r)]
        if default_roles:
            emails = []
            for r in default_roles:
                emails.extend(roles.get(r) or [])
            if emails:
                lines.append(f"_specflow/specs/ {' '.join(_to_codeowner_tokens(emails))}")
    else:
        for path, role_list in ownership.items():
            emails: list[str] = []
            for role in role_list or []:
                emails.extend(roles.get(role) or [])
            if emails:
                lines.append(f"{path} {' '.join(_to_codeowner_tokens(emails))}")

    lines.append("")
    return "\n".join(lines)


def _to_codeowner_tokens(emails: list[str]) -> list[str]:
    """Convert emails to CODEOWNERS tokens.

    GitHub expects @username or email. We pass emails through unchanged;
    users who prefer @handles should set those in config.yaml.
    """
    seen: set[str] = set()
    out: list[str] = []
    for e in emails:
        if not isinstance(e, str):
            continue
        e = e.strip()
        if not e or e in seen:
            continue
        seen.add(e)
        out.append(e)
    return out
