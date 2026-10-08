"""specflow hook — Install and run git hooks for RBAC enforcement.

Subcommands:
  specflow hook install [--force]  — Write the pre-commit hook into the directory
                                     git runs hooks from (worktree/core.hooksPath aware)
  specflow hook pre-commit         — Run pre-commit validation (called by the hook)
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import config as config_lib
from specflow.lib import git_utils
from specflow.lib import rbac as rbac_lib
from specflow.lib.adapters import load_adapters_config, get_adapter
from specflow.lib.adapters.github_actions import _DEFAULT_HOOK_SCRIPT, _SPECFLOW_REPO
from specflow.lib.display import RED, GREEN, YELLOW, NC


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

    return _DEFAULT_HOOK_SCRIPT


# Header line every specflow-written hook starts with (identical across
# released templates, so older specflow hooks still upgrade in place). A hook
# without it belongs to someone else -- including a user's own hook that merely
# CALLS `specflow hook pre-commit`, which is exactly what the refusal message
# and the adapter skill tell pre-commit/lefthook/husky users to do.
HOOK_OWNERSHIP_MARKER = "# specflow pre-commit hook — installed by"
HOOK_DELEGATE_LINE = "specflow hook pre-commit"
FORCE_HINT = "specflow hook install --force"
_INSTALL_HINT = f"uv tool install git+{_SPECFLOW_REPO}"


def backup_file(root: Path, path: Path, category: str) -> Path:
    """Copy ``path`` under ``.specflow/cache/backups/<timestamp>/<category>/``.

    Same convention ``refresh``/scaffold use for replaced checklists. Returns
    the backup path.
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = root / ".specflow" / "cache" / "backups" / stamp / category
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = backup_root / path.name
    shutil.copy2(str(path), str(backup))
    return backup


def _display_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def install_pre_commit_hook(root: Path, *, force: bool = False) -> dict:
    """Install the specflow pre-commit hook; shared by ``init`` and ``hook install``.

    Resolves the hooks directory through git (linked worktrees and
    ``core.hooksPath`` included) and never replaces a hook it does not own
    unless ``force``. Any existing hook whose content differs from the template
    (foreign under ``force``, or an older specflow hook) is backed up under
    ``.specflow/cache/backups/<ts>/hooks/`` before it is rewritten. A
    ``core.hooksPath`` from the global or system git config is shared by every
    repository on the machine, so installing there is also refused unless
    ``force``.
    Returns ``{"status", "path", "display", "backup", "hooks_path",
    "hooks_path_scope"}`` where ``status`` is one of ``installed``,
    ``unchanged``, ``refused``, ``refused-hooks-path`` or ``not-git``; callers
    print in their own style.
    """
    hooks_path, scope = git_utils.core_hooks_path_scoped(root)
    result: dict = {
        "status": "not-git", "path": None, "display": "", "backup": None,
        "hooks_path": hooks_path, "hooks_path_scope": scope,
    }
    hooks_dir = git_utils.hooks_dir(root)
    if hooks_dir is None:
        return result
    hook_path = hooks_dir / "pre-commit"
    result["path"] = hook_path
    result["display"] = _display_path(root, hook_path)
    if hooks_path and scope in ("global", "system") and not force:
        result["status"] = "refused-hooks-path"
        return result
    script = _hook_template(root)

    if hook_path.exists():
        existing = hook_path.read_text(encoding="utf-8", errors="ignore")
        if existing == script:
            _ensure_executable(hook_path)
            result["status"] = "unchanged"
            return result
        if HOOK_OWNERSHIP_MARKER not in existing and not force:
            result["status"] = "refused"
            return result
        result["backup"] = backup_file(root, hook_path, "hooks")

    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(script, encoding="utf-8")
    _ensure_executable(hook_path)
    result["status"] = "installed"
    return result


def _ensure_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _install(root: Path, force: bool = False) -> int:
    res = install_pre_commit_hook(root, force=force)
    status, display = res["status"], res["display"]
    if status == "not-git":
        print(f"{RED}✗ Not a git repository (or not its top-level directory): {root}{NC}")
        return 1
    if status == "refused-hooks-path":
        print(f"{RED}✗ core.hooksPath={res['hooks_path']} comes from your "
              f"{res['hooks_path_scope']} git config -- left as-is{NC}")
        print("  A hook installed there would run in every repository on this machine.")
        print("  Set a repo-local path first (git config core.hooksPath <dir>),")
        print(f"  or install there anyway: {FORCE_HINT}")
        return 1
    if status == "refused":
        print(f"{RED}✗ {display} exists and is not specflow-owned -- left as-is{NC}")
        print(f"  Replace it (a backup is taken first): {FORCE_HINT}")
        print(f"  Or keep your hook and add this line to it: {HOOK_DELEGATE_LINE}")
        return 1
    if res["backup"] is not None:
        print(f"{YELLOW}! Backed up the previous hook to {_display_path(root, res['backup'])}{NC}")
    if status == "unchanged":
        print(f"{GREEN}✓ {display} is up to date{NC}")
    else:
        print(f"{GREEN}✓ Installed {display}{NC}")
    if res["hooks_path"]:
        print(f"  {YELLOW}note:{NC} core.hooksPath={res['hooks_path']} -- git runs hooks from there, not .git/hooks")
    return 0


def _run_lint(root: Path, check_type: str) -> subprocess.CompletedProcess | None:
    """Run ``specflow artifact-lint --type <check_type>``; None when the CLI is not on PATH."""
    try:
        return subprocess.run(
            ["specflow", "artifact-lint", "--type", check_type],
            capture_output=True, text=True, cwd=str(root), check=False,
        )
    except FileNotFoundError:
        return None


def _not_on_path_message(check_type: str) -> str:
    return (
        f"cannot run `specflow artifact-lint --type {check_type}`: 'specflow' is "
        f"not on PATH (install: {_INSTALL_HINT})"
    )


def _pre_commit(root: Path) -> int:
    # STORY-678: a repository written by a newer on-disk format must not be
    # checked by a stale engine — refuse with the exact upgrade instruction.
    mismatch = config_lib.format_version_mismatch(root)
    if mismatch:
        print(f"{RED}✗ specflow pre-commit: refusing to run stale checks{NC}")
        print(f"  {mismatch}")
        return 1

    author = os.environ.get("GIT_AUTHOR_EMAIL") or rbac_lib.current_git_author_email(root)
    # RBAC reads staged frontmatter, so it sees additions/modifications only;
    # the link and schema lints must also run when the only staged artifact
    # change is a deletion or rename (a removed REQ breaks inbound links).
    changes = rbac_lib.staged_artifact_changes(root)
    staged_paths = rbac_lib.staged_specflow_paths(root)
    if not changes and not staged_paths:
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
            f"\n{YELLOW}Note:{NC} local hook blocked this transition; durable "
            f"enforcement is hosting-side."
        )
        return 1

    # Link integrity check (blocking — broken links are corrupted accounting)
    link_result = _run_lint(root, "links")
    if link_result is None:
        print(f"{RED}✗ specflow pre-commit: {_not_on_path_message('links')}{NC}")
        return 1
    if link_result.returncode != 0:
        print(f"{RED}✗ specflow pre-commit: link integrity check failed{NC}")
        print(link_result.stdout[-2000:] if len(link_result.stdout) > 2000 else link_result.stdout)
        print(f"\n{YELLOW}Fix before committing — re-run `specflow artifact-lint --type links` for details.{NC}")
        return 1

    # Schema validation (blocking — schema violations produce invalid artifacts)
    schema_result = _run_lint(root, "schema")
    if schema_result is None:
        print(f"{RED}✗ specflow pre-commit: {_not_on_path_message('schema')}{NC}")
        return 1
    if schema_result.returncode != 0:
        print(f"{RED}✗ specflow pre-commit: schema validation failed{NC}")
        print(schema_result.stdout[-2000:] if len(schema_result.stdout) > 2000 else schema_result.stdout)
        print(f"\n{YELLOW}Fix before committing — re-run `specflow artifact-lint --type schema` for details.{NC}")
        return 1

    # Advisory lint checks (YELLOW warnings — print on failure but NEVER block).
    # CI Pass 1 (artifact-lint) remains the authoritative blocker; blocking
    # locally on these would teach bypassing the hook, which BP-006 forbids. These are
    # status-cascade and story-linkage: real signals worth surfacing early, but
    # not worth aborting a commit over.
    for check_type in ("status-cascade", "story-linkage"):
        advisory = _run_lint(root, check_type)
        if advisory is None:
            print(f"{YELLOW}⚠ specflow pre-commit: {_not_on_path_message(check_type)}{NC}")
            break
        # Surface findings whether blocking OR warning-only. artifact-lint
        # exits 0 for warning-only output, so gating on returncode alone left
        # the common cascade signals (e.g. "STORY verified but its REQ is still
        # approved" — a warning) silently deferred to CI instead of surfaced
        # early as the comment above promises. A clean run prints
        # "(all checks clean)"; anything else is worth showing.
        out = advisory.stdout.strip()
        if out and "all checks clean" not in out:
            print(f"{YELLOW}⚠ specflow pre-commit: {check_type} check has findings{NC}")
            print(advisory.stdout[-1500:] if len(advisory.stdout) > 1500 else advisory.stdout)

    # Suspect flag check (warning — committing against suspect specs risks rework).
    # STORY-686: read the staged frontmatter already parsed in-process; the old
    # per-artifact `specflow status --artifact` subprocess never parsed (status
    # takes no artifact argument), so this check was dead.
    for change in changes:
        staged_fm = change.get("new_fm") or {}
        if staged_fm.get("suspect") is True:
            artifact_id = staged_fm.get("id") or Path(change["path"]).stem
            print(f"{YELLOW}⚠ specflow pre-commit: {artifact_id} is flagged suspect.{NC}")
            print(f"  {YELLOW}Proceeding may waste effort if upstream specs are stale.{NC}")

    return 0


def run(root: Path, args: dict) -> int:
    root = root.resolve()
    sub = args.get("hook_subcommand")
    if sub == "install":
        return _install(root, force=bool(args.get("force")))
    if sub == "pre-commit":
        return _pre_commit(root)
    print(f"{RED}✗ unknown hook subcommand: {sub}{NC}")
    return 1


def run_ci_gate(root: Path, args: dict) -> int:
    """Run RBAC checks on every commit between two refs (CI server-side gate).

    STORY-698: a pull request is evaluated as a HISTORY, not as one net
    base-to-head diff. For each changed artifact the gate walks the commits in
    ``base..head`` that touched it (oldest first, following renumber renames)
    and checks every consecutive (old, new) status pair for

    * schema legality (``allowed_status`` of the artifact's type),
    * authorisation of THAT commit's author, and
    * independence of THAT commit's author from the file's earlier authors.

    A net diff hides an unauthorised intermediate approval (draft -> approved
    by a non-approver, later verified by a reviewer) and an illegal hidden
    step (approved -> cancelled -> implemented). Solo-dev fast path: with no
    team roles configured every check passes, as before.

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

    enforce_legality = rbac_lib._has_configured_roles(rbac_lib._team_section(root))
    schema_dir = root / ".specflow" / "schema"

    failures: list[str] = []

    for filepath in changed_files:
        artifact_id = Path(filepath).stem
        for step in _status_steps(root, base_ref, head_ref, filepath):
            where = f" [commit {step['sha'][:8]}]" if step["sha"] else ""
            author_email = step["author"]
            old_status = step["old"]
            new_status = step["new"]

            if enforce_legality:
                reason = _illegal_step_reason(
                    schema_dir, step["type"], artifact_id, old_status, new_status,
                )
                if reason:
                    failures.append(
                        f"{reason} by '{author_email}'{where}"
                    )
                else:
                    # One commit may record several legal CLI steps
                    # (cascade-status, or two `update` calls before a
                    # commit). Each policy-gated status passed through on
                    # the way is charged to this commit's author (H2).
                    reason = _intermediate_authority_reason(
                        root, schema_dir, step["type"], artifact_id,
                        old_status, new_status, author_email,
                    )
                    if reason:
                        failures.append(f"{reason}{where}")

            ok, reason = rbac_lib.authorize_status_transition(
                root, artifact_id, new_status, author_email
            )
            if not ok:
                failures.append(f"{reason}{where}")
                continue

            ok, reason = rbac_lib.check_independence(
                root, step["path"], new_status, author_email,
                upto=step["sha"] or head_ref,
            )
            if not ok:
                failures.append(f"{reason}{where}")

    if failures:
        print(f"{RED}✗ specflow ci-gate: RBAC check failed{NC}")
        for f in failures:
            print(f"  {RED}•{NC} {f}")
        return 1

    print(f"{GREEN}✓ All artifact status transitions pass RBAC checks{NC}")
    return 0


def _status_steps(
    root: Path, base_ref: str, head_ref: str, filepath: str,
) -> list[dict[str, str]]:
    """Every status change of ``filepath`` in ``base..head``, oldest first.

    Each step is ``{sha, author, old, new, type, path}`` where ``path`` is the
    file's path at that commit (renames are followed). Commits git reports
    without a diff entry (merges) are not walked; if the walk does not arrive
    at the head status, one closing step from the last walked status to the
    head status is charged to the newest commit author in the range, so a
    status change can never slip through unexamined.
    """
    history = git_utils.file_history(root, filepath, f"{base_ref}..{head_ref}") or []
    walked = [e for e in history if e["change"] and e["change"] != "D"]

    steps: list[dict[str, str]] = []
    if walked:
        first = walked[0]
        start_fm = (
            _parse_ref_frontmatter(root, f"{first['sha']}^", first["old_path"])
            if first["old_path"] else None
        )
    else:
        start_fm = _parse_ref_frontmatter(
            root, _merge_base(root, base_ref, head_ref) or base_ref, filepath
        )
    reached = (start_fm or {}).get("status", "") or ""

    for entry in walked:
        old_fm = (
            _parse_ref_frontmatter(root, f"{entry['sha']}^", entry["old_path"])
            if entry["old_path"] else None
        )
        new_fm = _parse_ref_frontmatter(root, entry["sha"], entry["new_path"])
        old_status = (old_fm or {}).get("status", "") or ""
        new_status = (new_fm or {}).get("status", "") or ""
        if new_status:
            reached = new_status
        if not new_status or new_status == old_status:
            continue
        steps.append({
            "sha": entry["sha"],
            "author": entry["author_email"],
            "old": old_status,
            "new": new_status,
            "type": (new_fm or {}).get("type", "") or "",
            "path": entry["new_path"],
        })

    head_fm = _parse_ref_frontmatter(root, head_ref, filepath) or {}
    head_status = head_fm.get("status", "") or ""
    if head_status and head_status != reached:
        log = subprocess.run(
            ["git", "log", "-1", "--format=%ae", f"{base_ref}..{head_ref}"],
            capture_output=True, text=True, cwd=str(root), check=False,
        )
        steps.append({
            "sha": "",
            "author": log.stdout.strip().lower(),
            "old": reached,
            "new": head_status,
            "type": head_fm.get("type", "") or "",
            "path": filepath,
        })
    return steps


def _merge_base(root: Path, base_ref: str, head_ref: str) -> str:
    result = subprocess.run(
        ["git", "merge-base", base_ref, head_ref],
        capture_output=True, text=True, cwd=str(root), check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _status_map(schema_dir: Path, art_type: str) -> dict[str, list[str]]:
    """``allowed_status`` of ``art_type`` as {status: [predecessors]}; {} if none."""
    if not art_type:
        return {}
    schema = art_lib._read_schema(schema_dir, art_type)
    allowed = (schema or {}).get("allowed_status")
    if not isinstance(allowed, dict) or not allowed:
        return {}
    out: dict[str, list[str]] = {}
    for status, preds in allowed.items():
        if preds is None:
            preds = []
        elif not isinstance(preds, list):
            preds = [preds]
        out[str(status)] = [str(p) for p in preds]
    return out


def _legal_path(
    allowed: dict[str, list[str]], old_status: str, new_status: str,
    passable=None,
) -> list[str] | None:
    """Shortest chain of single legal steps from ``old`` to ``new``.

    Returns the statuses after ``old`` (ending with ``new``), or None when
    ``new`` is unreachable. ``passable(status)`` may veto an intermediate
    status (never ``new`` itself).
    """
    if old_status == new_status:
        return []
    succ: dict[str, list[str]] = {}
    for status, preds in allowed.items():
        for pred in preds:
            succ.setdefault(pred, []).append(status)
    prev: dict[str, str] = {old_status: ""}
    queue = [old_status]
    while queue:
        cur = queue.pop(0)
        for nxt in succ.get(cur, []):
            if nxt in prev:
                continue
            if nxt != new_status and passable is not None and not passable(nxt):
                continue
            prev[nxt] = cur
            if nxt == new_status:
                path = [nxt]
                while prev[path[-1]] != old_status:
                    path.append(prev[path[-1]])
                return list(reversed(path))
            queue.append(nxt)
    return None


def _illegal_step_reason(
    schema_dir: Path, art_type: str, artifact_id: str,
    old_status: str, new_status: str,
) -> str:
    """Return a reason when ``new`` cannot be reached from ``old``, else ''.

    A commit is a snapshot, not a CLI step: one commit may record several
    legal ``specflow update`` steps (``cascade-status`` walks approved ->
    implemented -> verified in one run). So a step is legal when a chain of
    single legal transitions leads from ``old`` to ``new``; the authority for
    each status passed through is checked separately
    (:func:`_intermediate_authority_reason`).

    Mirrors ``specflow update``'s gate otherwise: an artifact's creation (no
    old status) is not a transition; an unknown old status may be repaired to
    any legal status; an unknown type or a schema without a map is not judged
    here (artifact-lint owns those).
    """
    if not old_status:
        return ""
    allowed = _status_map(schema_dir, art_type)
    if not allowed:
        return ""
    if new_status not in allowed:
        return (
            f"{artifact_id}: illegal transition '{old_status}' -> '{new_status}' "
            f"('{new_status}' is not a {art_type} status)"
        )
    if old_status not in allowed:
        return ""  # repair path: current status itself is invalid
    if _legal_path(allowed, old_status, new_status) is not None:
        return ""
    preds = allowed.get(new_status) or []
    allowed_from = ", ".join(preds) if preds else "(none)"
    return (
        f"{artifact_id}: illegal transition '{old_status}' -> '{new_status}' "
        f"(not reachable by legal steps; allowed from: {allowed_from})"
    )


def _intermediate_authority_reason(
    root: Path, schema_dir: Path, art_type: str, artifact_id: str,
    old_status: str, new_status: str, author_email: str,
) -> str:
    """Reason when every legal chain ``old -> ... -> new`` passes a status
    ``author`` may not set, else ''.

    ``new`` itself is authorised by the caller. A chain the author is allowed
    to walk end to end clears the step; otherwise the first gated status on
    the shortest chain is reported against this commit's author.
    """
    allowed = _status_map(schema_dir, art_type)
    if not old_status or old_status not in allowed or new_status not in allowed:
        return ""
    path = _legal_path(allowed, old_status, new_status)
    if not path or len(path) == 1:
        return ""

    def passable(status: str) -> bool:
        return rbac_lib.authorize_status_transition(
            root, artifact_id, status, author_email)[0]

    if _legal_path(allowed, old_status, new_status, passable=passable) is not None:
        return ""
    for status in path[:-1]:
        ok, reason = rbac_lib.authorize_status_transition(
            root, artifact_id, status, author_email)
        if not ok:
            return (f"{reason} (passed through in one commit on "
                    f"'{old_status}' -> '{new_status}')")
    return ""


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
