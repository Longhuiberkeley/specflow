"""Tests for the pre-commit hook (specflow.commands.hook).

Focus: the advisory status-cascade / story-linkage checks (C11) must print a
YELLOW warning on failure but NEVER return non-zero — CI Pass 1 (artifact-lint)
remains the authoritative blocker; blocking locally trains --no-verify, which
BP-006 forbids.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from specflow.commands import hook as hook_cmd


def _completed(returncode: int, stdout: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def test_pre_commit_advisory_checks_do_not_block(tmp_path, monkeypatch, capsys):
    # A status-cascade FAILURE must surface as a warning but the hook still
    # returns 0 (commit proceeds). links/schema are clean.
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    (root / "_specflow").mkdir()

    change = {
        "path": "_specflow/work/stories/STORY-001.md",
        "old_status": "draft",
        "new_status": "approved",
    }
    monkeypatch.setattr(hook_cmd.rbac_lib, "staged_artifact_changes", lambda r: [change])
    monkeypatch.setattr(hook_cmd.rbac_lib, "current_git_author_email", lambda r: "a@b.com")
    monkeypatch.setattr(hook_cmd.rbac_lib, "authorize_status_transition", lambda *a, **k: (True, ""))
    monkeypatch.setattr(hook_cmd.rbac_lib, "check_independence", lambda *a, **k: (True, ""))

    def fake_run(cmd, **kw):
        check_type = cmd[cmd.index("--type") + 1] if "--type" in cmd else None
        if check_type == "status-cascade":
            return _completed(1, "STORY-001 verified but ARCH-001 still approved")
        # links, schema, story-linkage, and `status` all pass cleanly.
        return _completed(0)

    monkeypatch.setattr(hook_cmd.subprocess, "run", fake_run)

    rc = hook_cmd._pre_commit(root)
    out = capsys.readouterr().out
    assert rc == 0
    # The failing check is surfaced (truthful) ...
    assert "status-cascade" in out
    assert "ARCH-001" in out
    # ... but reported as a warning, not a blocking failure.
    assert "✗" not in out


def test_pre_commit_still_blocks_on_broken_links(tmp_path, monkeypatch, capsys):
    # Regression guard: the advisory carve-out must not weaken the existing
    # blocking link-integrity check. A broken-links failure still returns 1.
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    (root / "_specflow").mkdir()

    change = {
        "path": "_specflow/work/stories/STORY-001.md",
        "old_status": "draft",
        "new_status": "approved",
    }
    monkeypatch.setattr(hook_cmd.rbac_lib, "staged_artifact_changes", lambda r: [change])
    monkeypatch.setattr(hook_cmd.rbac_lib, "current_git_author_email", lambda r: "a@b.com")
    monkeypatch.setattr(hook_cmd.rbac_lib, "authorize_status_transition", lambda *a, **k: (True, ""))
    monkeypatch.setattr(hook_cmd.rbac_lib, "check_independence", lambda *a, **k: (True, ""))

    def fake_run(cmd, **kw):
        check_type = cmd[cmd.index("--type") + 1] if "--type" in cmd else None
        if check_type == "links":
            return _completed(1, "broken link: REQ-999")
        return _completed(0)

    monkeypatch.setattr(hook_cmd.subprocess, "run", fake_run)

    rc = hook_cmd._pre_commit(root)
    assert rc == 1


def test_pre_commit_advisory_surfaces_warning_only_findings(tmp_path, monkeypatch, capsys):
    # T2.6: artifact-lint exits 0 for warning-only output (the common cascade
    # case, e.g. "STORY verified but its REQ still approved"). The advisory
    # must surface that warning, not stay silent just because returncode == 0.
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    (root / "_specflow").mkdir()

    change = {
        "path": "_specflow/work/stories/STORY-001.md",
        "old_status": "draft",
        "new_status": "approved",
    }
    monkeypatch.setattr(hook_cmd.rbac_lib, "staged_artifact_changes", lambda r: [change])
    monkeypatch.setattr(hook_cmd.rbac_lib, "current_git_author_email", lambda r: "a@b.com")
    monkeypatch.setattr(hook_cmd.rbac_lib, "authorize_status_transition", lambda *a, **k: (True, ""))
    monkeypatch.setattr(hook_cmd.rbac_lib, "check_independence", lambda *a, **k: (True, ""))

    def fake_run(cmd, **kw):
        check_type = cmd[cmd.index("--type") + 1] if "--type" in cmd else None
        if check_type == "status-cascade":
            # returncode 0 (warning-only) BUT stdout carries findings — exactly
            # the case that was silently dropped before the fix.
            return _completed(
                0,
                "STORY-001 verified but REQ-001 still approved\n"
                "  Result: PASS (1 warnings)",
            )
        return _completed(0)  # links, schema, story-linkage, status all clean

    monkeypatch.setattr(hook_cmd.subprocess, "run", fake_run)

    rc = hook_cmd._pre_commit(root)
    out = capsys.readouterr().out
    assert rc == 0
    # The warning-only finding is now surfaced (was silent before T2.6).
    assert "status-cascade" in out
    assert "REQ-001" in out


# --- STORY-662: failure routing + RBAC copy ---

def _setup_clean_rbac(root: Path, monkeypatch) -> None:
    """Standard staged-change scaffolding with passing RBAC checks."""
    change = {
        "path": "_specflow/work/stories/STORY-001.md",
        "old_status": "draft",
        "new_status": "approved",
    }
    monkeypatch.setattr(hook_cmd.rbac_lib, "staged_artifact_changes", lambda r: [change])
    monkeypatch.setattr(hook_cmd.rbac_lib, "current_git_author_email", lambda r: "a@b.com")
    monkeypatch.setattr(hook_cmd.rbac_lib, "authorize_status_transition", lambda *a, **k: (True, ""))
    monkeypatch.setattr(hook_cmd.rbac_lib, "check_independence", lambda *a, **k: (True, ""))


def test_pre_commit_link_failure_routes_to_artifact_lint(tmp_path, monkeypatch, capsys):
    """STORY-662: a link failure names `specflow artifact-lint --type links`
    and stops — the copy never teaches the git bypass flag."""
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    (root / "_specflow").mkdir()
    _setup_clean_rbac(root, monkeypatch)

    def fake_run(cmd, **kw):
        check_type = cmd[cmd.index("--type") + 1] if "--type" in cmd else None
        if check_type == "links":
            return _completed(1, "broken link: REQ-999")
        return _completed(0)

    monkeypatch.setattr(hook_cmd.subprocess, "run", fake_run)

    rc = hook_cmd._pre_commit(root)
    out = capsys.readouterr().out
    assert rc == 1
    assert "artifact-lint --type links" in out
    assert "--no-verify" not in out


def test_pre_commit_schema_failure_routes_to_artifact_lint(tmp_path, monkeypatch, capsys):
    """STORY-662: a schema failure names `specflow artifact-lint --type schema`
    and stops — no bypass teaching."""
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    (root / "_specflow").mkdir()
    _setup_clean_rbac(root, monkeypatch)

    def fake_run(cmd, **kw):
        check_type = cmd[cmd.index("--type") + 1] if "--type" in cmd else None
        if check_type == "schema":
            return _completed(1, "STORY-001: missing required field 'created'")
        return _completed(0)

    monkeypatch.setattr(hook_cmd.subprocess, "run", fake_run)

    rc = hook_cmd._pre_commit(root)
    out = capsys.readouterr().out
    assert rc == 1
    assert "artifact-lint --type schema" in out
    assert "--no-verify" not in out


def test_pre_commit_rbac_failure_copy_is_not_advisory(tmp_path, monkeypatch, capsys):
    """STORY-662: the RBAC failure note says the local hook BLOCKED the
    transition and durable enforcement is hosting-side — it no longer calls
    the hook advisory."""
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    (root / "_specflow").mkdir()

    change = {
        "path": "_specflow/work/stories/STORY-001.md",
        "old_status": "draft",
        "new_status": "approved",
    }
    monkeypatch.setattr(hook_cmd.rbac_lib, "staged_artifact_changes", lambda r: [change])
    monkeypatch.setattr(hook_cmd.rbac_lib, "current_git_author_email", lambda r: "a@b.com")
    monkeypatch.setattr(
        hook_cmd.rbac_lib, "authorize_status_transition",
        lambda *a, **k: (False, "author may not approve their own artifact"),
    )
    monkeypatch.setattr(hook_cmd.rbac_lib, "check_independence", lambda *a, **k: (True, ""))

    rc = hook_cmd._pre_commit(root)
    out = capsys.readouterr().out
    assert rc == 1
    assert "local hook blocked this transition" in out
    assert "durable enforcement is hosting-side" in out
    assert "advisory" not in out


def test_no_bypass_flag_in_shipped_hook_text():
    """I3 (enforcement in code, not prompt text): the git bypass flag must not
    appear anywhere in the shipped hook module — not in output strings, not in
    comments that could be quoted back at users."""
    source = Path(hook_cmd.__file__).read_text(encoding="utf-8")
    assert "--no-verify" not in source


# --- STORY-686 AC2: suspect warning is read in-process from staged frontmatter ---

def test_pre_commit_suspect_warning_reads_staged_frontmatter(tmp_path, monkeypatch, capsys):
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    changes = [
        {
            "path": "_specflow/work/stories/STORY-001.md",
            "old_status": "draft", "new_status": "draft",
            "old_fm": {}, "new_fm": {"id": "STORY-001", "suspect": True},
        },
        {
            "path": "_specflow/work/stories/STORY-002.md",
            "old_status": "draft", "new_status": "draft",
            "old_fm": {}, "new_fm": {"id": "STORY-002", "suspect": False},
        },
    ]
    monkeypatch.setattr(hook_cmd.rbac_lib, "staged_artifact_changes", lambda r: changes)
    monkeypatch.setattr(hook_cmd.rbac_lib, "current_git_author_email", lambda r: "a@b.com")
    calls: list[list[str]] = []

    def fake_run(cmd, **kw):
        calls.append(list(cmd))
        return _completed(0, "(all checks clean)")

    monkeypatch.setattr(hook_cmd.subprocess, "run", fake_run)

    rc = hook_cmd._pre_commit(root)
    out = capsys.readouterr().out
    assert rc == 0
    assert "STORY-001 is flagged suspect" in out
    assert "STORY-002" not in out
    specflow_calls = [c for c in calls if c and c[0] == "specflow"]
    assert not any("status" in c for c in specflow_calls), "no per-artifact `specflow status` subprocess"
    assert len(specflow_calls) == 4, "only links, schema, status-cascade, story-linkage lint runs"


# ---------------------------------------------------------------------------
# STORY-698: per-step schema legality helper used by the CI gate walk.
# ---------------------------------------------------------------------------


def _req_schema_dir(tmp_path: Path) -> Path:
    schema_dir = tmp_path / "schema"
    schema_dir.mkdir()
    (schema_dir / "requirement.yaml").write_text(
        "type: requirement\n"
        "allowed_status:\n"
        "  draft: []\n"
        "  approved: [draft]\n"
        "  implemented: [approved]\n"
        "  verified: implemented\n",  # bare-string predecessor is coerced
        encoding="utf-8",
    )
    return schema_dir


def test_illegal_step_reason_legal_and_illegal(tmp_path):
    sd = _req_schema_dir(tmp_path)
    assert hook_cmd._illegal_step_reason(sd, "requirement", "REQ-001", "draft", "approved") == ""
    assert hook_cmd._illegal_step_reason(sd, "requirement", "REQ-001", "implemented", "verified") == ""
    # One commit may record several legal steps: reachable means legal
    # (the authority for each status passed through is checked separately).
    assert hook_cmd._illegal_step_reason(sd, "requirement", "REQ-001", "draft", "implemented") == ""
    reason = hook_cmd._illegal_step_reason(sd, "requirement", "REQ-001", "verified", "approved")
    assert reason == ("REQ-001: illegal transition 'verified' -> 'approved' "
                      "(not reachable by legal steps; allowed from: draft)")
    unknown = hook_cmd._illegal_step_reason(sd, "requirement", "REQ-001", "draft", "done")
    assert "'done' is not a requirement status" in unknown


def test_illegal_step_reason_skips_creation_repair_and_unknown_type(tmp_path):
    sd = _req_schema_dir(tmp_path)
    # Creation (no prior status) is not a transition.
    assert hook_cmd._illegal_step_reason(sd, "requirement", "REQ-001", "", "verified") == ""
    # Repair path: an invalid current status may move to any legal status.
    assert hook_cmd._illegal_step_reason(sd, "requirement", "REQ-001", "draftt", "implemented") == ""
    # No schema for the type: artifact-lint owns that, the gate does not judge.
    assert hook_cmd._illegal_step_reason(sd, "story", "STORY-001", "draft", "verified") == ""


def test_legal_path_is_the_shortest_chain_and_honours_passable(tmp_path):
    allowed = {"draft": [], "approved": ["draft"], "implemented": ["approved"],
               "verified": ["implemented"], "cancelled": ["draft", "approved"]}
    assert hook_cmd._legal_path(allowed, "approved", "verified") == ["implemented", "verified"]
    assert hook_cmd._legal_path(allowed, "draft", "cancelled") == ["cancelled"]
    assert hook_cmd._legal_path(allowed, "cancelled", "implemented") is None
    assert hook_cmd._legal_path(allowed, "draft", "verified",
                                passable=lambda s: s != "approved") is None


# ---------------------------------------------------------------------------
# STORY-708 (wave P-2): PATH guard, hooks-dir resolution, staged deletions,
# foreign-hook safety. These use a REAL temporary git repository where the
# behaviour under test is git's, and monkeypatches only where it is not.

import os
import shutil
import stat

import pytest

from specflow.commands import init as init_cmd
from specflow.lib import git_utils, rbac as rbac_lib
from specflow.lib.adapters.github_actions import _DEFAULT_HOOK_SCRIPT

_GIT_ID = ["-c", "user.email=t@example.com", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
_REAL_RUN = subprocess.run


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return _REAL_RUN(["git", *_GIT_ID, *args], cwd=str(root), capture_output=True, text=True, check=True)


def _repo(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir()
    _git(root, "init", "-q")
    (root / "README.md").write_text("x\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "init")
    return root


def _artifact(root: Path, rel: str, fm: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{fm}---\n\nbody\n", encoding="utf-8")
    return path


# --- F-120: shell guard before exec --------------------------------------

@pytest.mark.skipif(shutil.which("bash") is None, reason="bash required")
def test_hook_script_without_specflow_on_path_names_the_install_command(tmp_path):
    hook = tmp_path / "pre-commit"
    hook.write_text(_DEFAULT_HOOK_SCRIPT, encoding="utf-8")
    empty = tmp_path / "empty-path"
    empty.mkdir()
    res = _REAL_RUN(
        ["env", "-i", f"PATH={empty}", shutil.which("bash"), str(hook)],
        capture_output=True, text=True, check=False,
    )
    assert res.returncode == 1, res  # not the opaque 127 of a missing exec target
    assert "not on PATH" in res.stderr
    assert "uv tool install git+https://github.com/Longhuiberkeley/specflow" in res.stderr


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash required")
def test_hook_script_with_specflow_on_path_delegates_to_pre_commit(tmp_path):
    hook = tmp_path / "pre-commit"
    hook.write_text(_DEFAULT_HOOK_SCRIPT, encoding="utf-8")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "specflow"
    fake.write_text("#!/bin/sh\necho \"fake specflow: $*\"\nexit 0\n", encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    res = _REAL_RUN(
        ["env", "-i", f"PATH={bindir}", shutil.which("bash"), str(hook), "extra"],
        capture_output=True, text=True, check=False,
    )
    assert res.returncode == 0, res
    assert "fake specflow: hook pre-commit extra" in res.stdout


def test_pre_commit_reports_missing_cli_instead_of_tracebacking(tmp_path, monkeypatch, capsys):
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    change = {"path": "_specflow/work/stories/STORY-001.md", "old_status": "draft", "new_status": "draft"}
    monkeypatch.setattr(hook_cmd.rbac_lib, "staged_artifact_changes", lambda r: [change])
    monkeypatch.setattr(hook_cmd.rbac_lib, "staged_specflow_paths", lambda r: [change["path"]])
    monkeypatch.setattr(hook_cmd.rbac_lib, "current_git_author_email", lambda r: "a@b.com")

    def missing(cmd, **kw):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(hook_cmd.subprocess, "run", missing)
    rc = hook_cmd._pre_commit(root)
    out = capsys.readouterr().out
    assert rc == 1
    assert "not on PATH" in out and "uv tool install" in out


# --- F-121: hooks dir resolved through git ---------------------------------

def test_hooks_dir_plain_repo_and_non_repo(tmp_path):
    root = _repo(tmp_path)
    assert git_utils.hooks_dir(root) == (root / ".git" / "hooks").resolve()
    plain = tmp_path / "plain"
    plain.mkdir()
    assert git_utils.hooks_dir(plain) is None
    assert git_utils.core_hooks_path(root) == ""


def test_hooks_dir_in_linked_worktree_is_the_common_hooks_dir(tmp_path):
    main = _repo(tmp_path, "main")
    wt = tmp_path / "wt"
    _git(main, "worktree", "add", "-q", str(wt))
    assert (wt / ".git").is_file()  # the case the old `.git.is_dir()` check refused
    assert git_utils.hooks_dir(wt) == (main / ".git" / "hooks").resolve()

    res = hook_cmd.install_pre_commit_hook(wt)
    assert res["status"] == "installed"
    assert res["path"] == (main / ".git" / "hooks" / "pre-commit").resolve()
    assert res["path"].read_text(encoding="utf-8") == _DEFAULT_HOOK_SCRIPT
    assert os.access(res["path"], os.X_OK)


def test_hooks_dir_honours_core_hooks_path(tmp_path):
    root = _repo(tmp_path)
    _git(root, "config", "core.hooksPath", ".husky")
    assert git_utils.core_hooks_path(root) == ".husky"
    assert git_utils.hooks_dir(root) == (root / ".husky").resolve()
    res = hook_cmd.install_pre_commit_hook(root)
    assert res["status"] == "installed" and res["hooks_path"] == ".husky"
    assert (root / ".husky" / "pre-commit").exists()


# --- F-124: never clobber a foreign hook -----------------------------------

def test_install_refuses_foreign_hook_with_force_hint(tmp_path, capsys):
    root = _repo(tmp_path)
    hook = root / ".git" / "hooks" / "pre-commit"
    foreign = "#!/bin/sh\nexec lefthook run pre-commit\n"
    hook.write_text(foreign, encoding="utf-8")

    rc = hook_cmd.run(root, {"hook_subcommand": "install"})
    out = capsys.readouterr().out
    assert rc == 1
    assert hook.read_text(encoding="utf-8") == foreign  # untouched
    assert "not specflow-owned" in out
    assert "specflow hook install --force" in out
    assert "specflow hook pre-commit" in out  # the keep-your-hook alternative
    assert not (root / ".specflow" / "cache" / "backups").exists()


def test_install_force_backs_up_then_replaces_foreign_hook(tmp_path, capsys):
    root = _repo(tmp_path)
    hook = root / ".git" / "hooks" / "pre-commit"
    foreign = "#!/bin/sh\nexec lefthook run pre-commit\n"
    hook.write_text(foreign, encoding="utf-8")

    rc = hook_cmd.run(root, {"hook_subcommand": "install", "force": True})
    out = capsys.readouterr().out
    assert rc == 0
    assert hook.read_text(encoding="utf-8") == _DEFAULT_HOOK_SCRIPT
    backups = list((root / ".specflow" / "cache" / "backups").glob("*/hooks/pre-commit"))
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == foreign
    assert "Backed up" in out and "Installed" in out


def test_install_updates_owned_hook_in_place_and_reports_unchanged(tmp_path, capsys):
    root = _repo(tmp_path)
    hook = root / ".git" / "hooks" / "pre-commit"
    # The v1.17.1 template (header line present, no PATH guard) is specflow-owned
    # and upgrades without --force; the superseded content is backed up.
    older = (
        "#!/usr/bin/env bash\n"
        "# specflow pre-commit hook — installed by `specflow hook install` or `specflow init`\n"
        "# Delegates to the Python CLI so the logic stays version-controlled.\n"
        "exec specflow hook pre-commit \"$@\"\n"
    )
    hook.write_text(older, encoding="utf-8")
    assert hook_cmd.run(root, {"hook_subcommand": "install"}) == 0
    assert hook.read_text(encoding="utf-8") == _DEFAULT_HOOK_SCRIPT
    backups = list((root / ".specflow" / "cache" / "backups").glob("*/hooks/pre-commit"))
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == older
    assert "Installed" in capsys.readouterr().out
    # Second run: identical content is reported, not rewritten, not backed up again.
    assert hook_cmd.run(root, {"hook_subcommand": "install"}) == 0
    assert "up to date" in capsys.readouterr().out
    assert len(list((root / ".specflow" / "cache" / "backups").glob("*/hooks/pre-commit"))) == 1


def test_install_refuses_user_hook_that_merely_calls_specflow(tmp_path, capsys):
    """A user's own hook that CALLS `specflow hook pre-commit` (what the refusal
    message and the adapter skill tell pre-commit/lefthook/husky users to do)
    is not specflow-owned: neither `hook install` nor an `init` re-run may
    replace it."""
    root = _repo(tmp_path)
    hook = root / ".git" / "hooks" / "pre-commit"
    users = "#!/bin/sh\npre-commit run --all-files || exit 1\nspecflow hook pre-commit\n"
    hook.write_text(users, encoding="utf-8")

    rc = hook_cmd.run(root, {"hook_subcommand": "install"})
    out = capsys.readouterr().out
    assert rc == 1 and "not specflow-owned" in out and "specflow hook install --force" in out
    assert hook.read_bytes() == users.encode("utf-8")

    init_cmd._install_pre_commit_hook(root)
    assert "not specflow-owned" in capsys.readouterr().out
    assert hook.read_bytes() == users.encode("utf-8")
    assert not (root / ".specflow" / "cache" / "backups").exists()

    # --force is the only way through, and it keeps a copy.
    assert hook_cmd.run(root, {"hook_subcommand": "install", "force": True}) == 0
    assert hook.read_text(encoding="utf-8") == _DEFAULT_HOOK_SCRIPT
    backups = list((root / ".specflow" / "cache" / "backups").glob("*/hooks/pre-commit"))
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == users


def test_hooks_dir_refuses_project_nested_inside_another_repo(tmp_path, capsys):
    """A subdirectory of a repo (monorepo subproject, $HOME dotfiles) is not a
    hooks target: the parent's hook would run with the wrong cwd."""
    parent = _repo(tmp_path)
    nested = parent / "apps" / "svc"
    nested.mkdir(parents=True)
    assert git_utils.toplevel(nested) == parent.resolve()
    assert git_utils.hooks_dir(nested) is None
    assert hook_cmd.install_pre_commit_hook(nested)["status"] == "not-git"
    assert not (parent / ".git" / "hooks" / "pre-commit").exists()
    assert hook_cmd.run(nested, {"hook_subcommand": "install"}) == 1
    assert "top-level" in capsys.readouterr().out


def test_install_refuses_global_core_hooks_path(tmp_path, monkeypatch, capsys):
    root = _repo(tmp_path)
    shared = tmp_path / "githooks"
    shared.mkdir()
    gconf = tmp_path / "gitconfig"
    gconf.write_text(f"[core]\n\thooksPath = {shared}\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(gconf))
    assert git_utils.core_hooks_path_scoped(root) == (str(shared), "global")
    assert git_utils.hooks_dir(root) == shared.resolve()

    res = hook_cmd.install_pre_commit_hook(root)
    assert res["status"] == "refused-hooks-path" and res["hooks_path_scope"] == "global"
    assert not (shared / "pre-commit").exists()
    assert hook_cmd.run(root, {"hook_subcommand": "install"}) == 1
    out = capsys.readouterr().out
    assert "global git config" in out and "every repository" in out and "--force" in out
    init_cmd._install_pre_commit_hook(root)
    assert "machine-wide" in capsys.readouterr().out
    assert not (shared / "pre-commit").exists()

    # A repo-local hooksPath is the user's deliberate choice for THIS repo.
    _git(root, "config", "core.hooksPath", ".husky")
    assert git_utils.core_hooks_path_scoped(root) == (".husky", "local")
    assert hook_cmd.install_pre_commit_hook(root)["status"] == "installed"
    assert (root / ".husky" / "pre-commit").exists()

    # --force installs into the shared directory on purpose.
    _git(root, "config", "--unset", "core.hooksPath")
    assert hook_cmd.install_pre_commit_hook(root, force=True)["status"] == "installed"
    assert (shared / "pre-commit").exists()


def test_installer_degrades_without_a_git_binary(tmp_path, monkeypatch, capsys):
    root = _repo(tmp_path)

    def no_git(cmd, *a, **k):
        if cmd and cmd[0] == "git":
            raise FileNotFoundError(2, "No such file or directory", "git")
        return _REAL_RUN(cmd, *a, **k)

    monkeypatch.setattr(git_utils.subprocess, "run", no_git)
    assert git_utils.is_git_repo(root) is False
    assert git_utils.toplevel(root) is None
    assert git_utils.core_hooks_path_scoped(root) == ("", "")
    # A real .git directory still gets the hook (plain repos need no git call).
    assert git_utils.hooks_dir(root) == (root / ".git" / "hooks").resolve()
    assert hook_cmd.install_pre_commit_hook(root)["status"] == "installed"
    plain = tmp_path / "plain"
    plain.mkdir()
    assert git_utils.hooks_dir(plain) is None
    init_cmd._install_pre_commit_hook(plain)  # must not raise
    assert "specflow hook install" in capsys.readouterr().out


def test_cli_hook_install_accepts_force(tmp_path, monkeypatch):
    """Parser wiring for the --force the refusal message advertises (cli.py)."""
    from specflow import cli
    root = _repo(tmp_path)
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexec lefthook run pre-commit\n", encoding="utf-8")
    monkeypatch.chdir(root)
    assert cli.main(["hook", "install"]) == 1
    assert cli.main(["hook", "install", "--force"]) == 0
    assert hook.read_text(encoding="utf-8") == _DEFAULT_HOOK_SCRIPT


def test_init_uses_shared_installer_and_hint(tmp_path, capsys):
    root = _repo(tmp_path)
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    init_cmd._install_pre_commit_hook(root)
    out = capsys.readouterr().out
    assert "not specflow-owned" in out and "specflow hook install --force" in out
    assert hook.read_text(encoding="utf-8") == "#!/bin/sh\nexit 0\n"

    plain = tmp_path / "plain"
    plain.mkdir()
    init_cmd._install_pre_commit_hook(plain)
    assert "specflow hook install" in capsys.readouterr().out  # says how to install later

    hook.unlink()
    init_cmd._install_pre_commit_hook(root)
    assert "Installed" in capsys.readouterr().out
    assert hook.read_text(encoding="utf-8") == _DEFAULT_HOOK_SCRIPT


# --- F-122: staged deletions and renames still trigger the lints -----------

def test_staged_specflow_paths_sees_deletions_and_renames(tmp_path):
    root = _repo(tmp_path)
    _artifact(root, "_specflow/specs/requirements/REQ-001.md", "id: REQ-001\nstatus: approved\n")
    _artifact(root, "_specflow/specs/requirements/REQ-002.md", "id: REQ-002\nstatus: approved\n")
    (root / "_specflow/specs/requirements/_index.yaml").write_text("{}\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "artifacts")

    _git(root, "rm", "-q", "_specflow/specs/requirements/REQ-001.md")
    _git(root, "mv", "_specflow/specs/requirements/REQ-002.md", "_specflow/specs/requirements/REQ-003.md")
    (root / "_specflow/specs/requirements/_index.yaml").write_text("{a: 1}\n", encoding="utf-8")
    _git(root, "add", "_specflow/specs/requirements/_index.yaml")

    assert rbac_lib.staged_artifact_changes(root) == []  # unchanged contract: A/M only
    paths = rbac_lib.staged_specflow_paths(root)
    assert "_specflow/specs/requirements/REQ-001.md" in paths
    assert "_specflow/specs/requirements/REQ-003.md" in paths
    assert not any(p.endswith("_index.yaml") for p in paths)


def test_pre_commit_runs_links_lint_when_only_a_deletion_is_staged(tmp_path, monkeypatch, capsys):
    root = _repo(tmp_path)
    _artifact(root, "_specflow/specs/requirements/REQ-001.md", "id: REQ-001\nstatus: approved\n")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "artifact")
    _git(root, "rm", "-q", "_specflow/specs/requirements/REQ-001.md")

    monkeypatch.setattr(hook_cmd.config_lib, "format_version_mismatch", lambda r: "")
    monkeypatch.setattr(hook_cmd.rbac_lib, "current_git_author_email", lambda r: "a@b.com")
    lint_calls: list[str] = []

    def fake_run(cmd, **kw):
        if cmd[0] == "git":
            return _REAL_RUN(cmd, **kw)
        lint_calls.append(cmd[cmd.index("--type") + 1])
        if lint_calls[-1] == "links":
            return _completed(1, "broken link: STORY-001 -> REQ-001")
        return _completed(0, "(all checks clean)")

    monkeypatch.setattr(hook_cmd.subprocess, "run", fake_run)
    rc = hook_cmd._pre_commit(root)
    assert lint_calls[:1] == ["links"]
    assert rc == 1
    assert "link integrity check failed" in capsys.readouterr().out


def test_pre_commit_still_early_returns_with_nothing_staged(tmp_path, monkeypatch):
    root = _repo(tmp_path)
    monkeypatch.setattr(hook_cmd.config_lib, "format_version_mismatch", lambda r: "")
    monkeypatch.setattr(hook_cmd.rbac_lib, "current_git_author_email", lambda r: "a@b.com")
    calls: list[list[str]] = []

    def fake_run(cmd, **kw):
        if cmd[0] == "git":
            return _REAL_RUN(cmd, **kw)
        calls.append(list(cmd))
        return _completed(0)

    monkeypatch.setattr(hook_cmd.subprocess, "run", fake_run)
    assert hook_cmd._pre_commit(root) == 0
    assert calls == []  # no cry-wolf: a non-artifact commit runs no lint
