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
    assert not any("status" in c for c in calls), "no per-artifact `specflow status` subprocess"
    assert len(calls) == 4, "only links, schema, status-cascade, story-linkage lint runs"


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
