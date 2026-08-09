"""Tests for checklist result persistence (specflow.lib.checklists).

Focus: the honest-outcome fix for empty persisted results — an empty result
list must NOT be reported as 'passed' (vacuous truth over all() is dishonest
because nothing was actually verified).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.commands import checklist_run
from specflow.lib.artifacts import Artifact
from specflow.lib.checklists import AssembledChecklist, ChecklistResult, persist_results


def test_persist_results_empty_is_incomplete_not_passed(tmp_path: Path):
    """An empty result list (no automated items ran) must NOT be reported as
    'passed'. Vacuous truth (all() over []) is dishonest — nothing was
    verified. The honest non-pass outcome is 'incomplete'."""
    path = persist_results(tmp_path, "REQ-001", "requirement-review", [])
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["overall"] == "incomplete"
    assert data["overall"] != "passed"


def test_persist_results_all_passed_is_passed(tmp_path: Path):
    """Non-empty, all-passed results stay 'passed' (regression guard)."""
    results = [
        ChecklistResult(item_id="R1", result="passed"),
        ChecklistResult(item_id="R2", result="passed"),
    ]
    path = persist_results(tmp_path, "REQ-001", "requirement-review", results)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["overall"] == "passed"


def test_persist_results_any_failed_is_failed(tmp_path: Path):
    """Any failed result → 'failed' (unchanged behavior, regression guard)."""
    results = [
        ChecklistResult(item_id="R1", result="passed"),
        ChecklistResult(item_id="R2", result="failed", detail="boom"),
    ]
    path = persist_results(tmp_path, "REQ-001", "requirement-review", results)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["overall"] == "failed"


def test_no_matching_items_persists_incomplete(tmp_path: Path, monkeypatch):
    """The CLI no-match path must record incomplete instead of a silent no-op."""
    artifact = Artifact(
        path=tmp_path / "REQ-001.md",
        frontmatter={"id": "REQ-001", "type": "requirement", "status": "draft"},
        body="# Requirement\n",
        links=[],
    )
    monkeypatch.setattr(
        checklist_run,
        "assemble_checklist",
        lambda *_args, **_kwargs: AssembledChecklist(artifact_id=artifact.id),
    )
    monkeypatch.setattr(checklist_run, "update_artifact_checklists_applied", lambda *_args: None)

    assert checklist_run._check_artifact(tmp_path, artifact, None, False) == 0

    logs = list((tmp_path / ".specflow" / "checklist-log").glob("*.yaml"))
    assert len(logs) == 1
    data = yaml.safe_load(logs[0].read_text(encoding="utf-8"))
    assert data["overall"] == "incomplete"
