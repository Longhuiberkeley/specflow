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
