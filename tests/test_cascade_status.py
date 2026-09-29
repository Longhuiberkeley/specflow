"""cascade-status walks only legal transitions and fails loudly (STORY-697, DEC-093).

Before the fix, a verified STORY with ``--include-req`` proposed
``approved -> verified`` for its REQ (and ARCH/DDD) in one hop. The real
schemas only allow ``verified`` from ``implemented``, so ``update_artifact``
refused, the command printed a cross and still exited 0. It also promoted a
REQ to verified while a sibling STORY implementing it was unverified.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specflow.lib import artifacts as art_lib
from test_cascade_support import allowed, project, put, run_cli, spy_updates, status_of


def _verified_story_with_approved_specs(tmp_path: Path) -> Path:
    root = project(tmp_path)
    put(root, "REQ-001", "approved")
    put(root, "ARCH-001", "approved")
    put(root, "DDD-001", "approved")
    put(root, "STORY-001", "verified", [("REQ-001", "implements"), ("ARCH-001", "guided_by"),
                                         ("DDD-001", "specified_by")])
    art_lib.rebuild_index(root)
    return root


def test_include_req_walks_approved_to_verified_through_implemented(tmp_path, monkeypatch):
    root = _verified_story_with_approved_specs(tmp_path)
    calls = spy_updates(monkeypatch)

    code, out = run_cli(root, monkeypatch, "cascade-status", "STORY-001", "--include-req")

    assert code == 0, out
    for art_id in ("REQ-001", "ARCH-001", "DDD-001"):
        assert status_of(root, art_id) == "verified", out
    for art_id, art_type, frm, to in calls:
        assert frm in allowed(root, art_type).get(to, []), (art_id, frm, to)
    assert ("REQ-001", "requirement", "approved", "implemented") in calls
    assert ("REQ-001", "requirement", "implemented", "verified") in calls


def test_exit_code_is_nonzero_when_a_proposed_transition_fails(tmp_path, monkeypatch):
    root = _verified_story_with_approved_specs(tmp_path)
    monkeypatch.setattr(art_lib, "update_artifact",
                        lambda *a, **k: {"ok": False, "error": "disk on fire"})

    code, out = run_cli(root, monkeypatch, "cascade-status", "STORY-001", "--include-req")

    assert code != 0, out
    assert "disk on fire" in out


def test_success_exit_never_accompanies_a_failure_mark(tmp_path, monkeypatch):
    # The pre-fix symptom: a "✗" line and exit 0 in the same run.
    root = _verified_story_with_approved_specs(tmp_path)
    code, out = run_cli(root, monkeypatch, "cascade-status", "STORY-001", "--include-req")
    assert not (code == 0 and "✗" in out), out


@pytest.mark.parametrize("req_status", ["approved", "implemented"])
def test_req_not_verified_while_a_sibling_story_is_unverified(tmp_path, monkeypatch, req_status):
    root = project(tmp_path)
    put(root, "REQ-001", req_status)
    put(root, "STORY-001", "verified", [("REQ-001", "implements")])
    put(root, "STORY-002", "implemented", [("REQ-001", "implements")])
    art_lib.rebuild_index(root)

    code, out = run_cli(root, monkeypatch, "cascade-status", "STORY-001", "--include-req")

    assert code == 0, out
    assert status_of(root, "REQ-001") == "implemented", out
    assert "STORY-002" in out  # the hold names the unverified sibling


def test_req_verified_once_every_implementing_story_is_verified(tmp_path, monkeypatch):
    root = project(tmp_path)
    put(root, "REQ-001", "implemented")
    put(root, "STORY-001", "verified", [("REQ-001", "implements")])
    put(root, "STORY-002", "verified", [("REQ-001", "derives_from")])
    put(root, "STORY-003", "cancelled", [("REQ-001", "implements")])  # terminal: ignored
    art_lib.rebuild_index(root)

    code, out = run_cli(root, monkeypatch, "cascade-status", "STORY-001", "--include-req")

    assert code == 0, out
    assert status_of(root, "REQ-001") == "verified"


def test_draft_spec_is_refused_with_reason_and_nonzero_exit(tmp_path, monkeypatch):
    root = project(tmp_path)
    put(root, "ARCH-001", "draft")
    put(root, "STORY-001", "implemented", [("ARCH-001", "guided_by")])
    art_lib.rebuild_index(root)

    code, out = run_cli(root, monkeypatch, "cascade-status", "STORY-001")

    assert code != 0, out
    assert status_of(root, "ARCH-001") == "draft"
    assert "ARCH-001" in out and "draft" in out


def test_dry_run_prints_the_legal_walk_and_writes_nothing(tmp_path, monkeypatch):
    root = _verified_story_with_approved_specs(tmp_path)

    code, out = run_cli(root, monkeypatch, "cascade-status", "STORY-001", "--include-req",
                        "--dry-run")

    assert code == 0, out
    assert "approved → implemented → verified" in out
    assert status_of(root, "REQ-001") == "approved"


def test_derives_from_req_is_cascaded_like_implements(tmp_path, monkeypatch):
    # One role set with the status-cascade lint: derives_from counts for REQ.
    root = project(tmp_path)
    put(root, "REQ-001", "approved")
    put(root, "STORY-001", "implemented", [("REQ-001", "derives_from")])
    art_lib.rebuild_index(root)

    code, out = run_cli(root, monkeypatch, "cascade-status", "STORY-001", "--include-req")

    assert code == 0, out
    assert status_of(root, "REQ-001") == "implemented"


def test_implemented_story_leaves_specs_already_beyond_target_alone(tmp_path, monkeypatch):
    root = project(tmp_path)
    put(root, "ARCH-001", "verified")
    put(root, "DDD-001", "deprecated")
    put(root, "STORY-001", "implemented", [("ARCH-001", "guided_by"), ("DDD-001", "specified_by")])
    art_lib.rebuild_index(root)
    calls = spy_updates(monkeypatch)

    code, out = run_cli(root, monkeypatch, "cascade-status", "STORY-001")

    assert code == 0, out
    assert calls == []
