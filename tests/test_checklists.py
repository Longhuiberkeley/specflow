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


# ---------------------------------------------------------------------------
# STORY-682: script-less automated items error, severity honoured, parse
# failures warn.
# ---------------------------------------------------------------------------

from specflow.lib.checklists import (  # noqa: E402
    ChecklistItem,
    assemble_checklist,
    parse_checklist_file,
    run_automated_pass,
)


def _story_artifact(tmp_path: Path) -> Artifact:
    path = tmp_path / "STORY-001.md"
    path.write_text("---\nid: STORY-001\ntype: story\nstatus: draft\n---\n\n# S\n", encoding="utf-8")
    return Artifact(
        path=path,
        frontmatter={"id": "STORY-001", "type": "story", "status": "draft", "title": "S"},
        body="# S\n",
        links=[],
    )


def test_scriptless_automated_item_is_error_not_pass(tmp_path: Path):
    """STORY-682 AC1: an automated item with no script must not silently pass."""
    art = _story_artifact(tmp_path)
    assembled = AssembledChecklist(
        artifact_id=art.id,
        items=[ChecklistItem(id="X-01", check="c", automated=True, severity="warning", script=None)],
    )
    results = run_automated_pass(tmp_path, assembled, art)
    assert len(results) == 1
    assert results[0].result == "error"
    assert results[0].result != "passed"
    assert "no script" in (results[0].detail or "").lower()


def test_results_carry_item_severity(tmp_path: Path):
    art = _story_artifact(tmp_path)
    assembled = AssembledChecklist(
        artifact_id=art.id,
        items=[
            ChecklistItem(id="W-01", check="w", automated=True, severity="warning", script="exit 1"),
            ChecklistItem(id="B-01", check="b", automated=True, severity="blocking", script="exit 0"),
        ],
    )
    results = {r.item_id: r for r in run_automated_pass(tmp_path, assembled, art)}
    assert results["W-01"].result == "failed"
    assert results["W-01"].severity == "warning"
    assert results["B-01"].severity == "blocking"


def _patch_assembled(monkeypatch, items):
    monkeypatch.setattr(
        checklist_run,
        "assemble_checklist",
        lambda root, artifact, phase_transition=None: AssembledChecklist(
            artifact_id=artifact.id, items=items, sources=["test"]
        ),
    )
    monkeypatch.setattr(checklist_run, "update_artifact_checklists_applied", lambda *_args: None)


def test_warning_severity_failure_does_not_block(tmp_path: Path, monkeypatch, capsys):
    """STORY-682 AC2: a failed warning-severity item is a warning, not a blocker."""
    art = _story_artifact(tmp_path)
    _patch_assembled(monkeypatch, [
        ChecklistItem(id="W-01", check="warn check", automated=True, severity="warning", script="exit 1"),
        ChecklistItem(id="J-01", check="judged check", automated=False, severity="blocking"),
    ])
    rc = checklist_run._check_artifact(tmp_path, art, None, False)
    out = capsys.readouterr().out
    assert rc == 0
    assert "Blocking automated check failed" not in out
    # Agent-judged items are still listed because nothing blocked.
    assert "judged check" in out


def test_blocking_severity_failure_blocks(tmp_path: Path, monkeypatch, capsys):
    art = _story_artifact(tmp_path)
    _patch_assembled(monkeypatch, [
        ChecklistItem(id="B-01", check="block check", automated=True, severity="blocking", script="exit 1"),
    ])
    assert checklist_run._check_artifact(tmp_path, art, None, False) == 1
    assert "Blocking automated check failed" in capsys.readouterr().out


def test_persisted_blocking_failures_counts_only_blocking(tmp_path: Path):
    """STORY-682 AC3: blocking_failures counts only items that actually blocked."""
    results = [
        ChecklistResult(item_id="W-01", result="failed", severity="warning"),
        ChecklistResult(item_id="I-01", result="failed", severity="info"),
        ChecklistResult(item_id="B-01", result="failed", severity="blocking"),
        ChecklistResult(item_id="B-02", result="passed", severity="blocking"),
    ]
    path = persist_results(tmp_path, "STORY-001", "check-STORY-001", results)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["blocking_failures"] == 1
    assert data["overall"] == "failed"


def test_persisted_blocking_failures_zero_for_warning_only(tmp_path: Path):
    results = [ChecklistResult(item_id="W-01", result="failed", severity="warning")]
    path = persist_results(tmp_path, "STORY-001", "check-STORY-001", results)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["blocking_failures"] == 0


def _write_bad_checklist(root: Path) -> Path:
    d = root / ".specflow" / "checklists" / "in-process"
    d.mkdir(parents=True, exist_ok=True)
    bad = d / "story-writing.yaml"
    bad.write_text('items:\n  - id: X\n    script: "unterminated \\$1"\n', encoding="utf-8")
    return bad


def test_parse_failure_reports_path_and_reason_to_stderr(tmp_path: Path, capsys):
    """STORY-682 AC4: a YAML parse failure is loud, not a silent []."""
    bad = _write_bad_checklist(tmp_path)
    errors: list[str] = []
    assert parse_checklist_file(bad, errors) == []
    err = capsys.readouterr().err
    assert str(bad) in err
    assert len(errors) == 1 and str(bad) in errors[0]


def test_assemble_checklist_records_parse_errors(tmp_path: Path, capsys):
    bad = _write_bad_checklist(tmp_path)
    art = _story_artifact(tmp_path)
    assembled = assemble_checklist(tmp_path, art)
    assert any(str(bad) in e for e in assembled.parse_errors)


def test_run_summary_surfaces_parse_failures(tmp_path: Path, monkeypatch, capsys):
    bad = _write_bad_checklist(tmp_path)
    art = _story_artifact(tmp_path)
    monkeypatch.setattr(checklist_run, "resolve_link_target", lambda *_a: art.path)
    monkeypatch.setattr(checklist_run, "parse_artifact", lambda *_a: art)
    monkeypatch.setattr(checklist_run, "update_artifact_checklists_applied", lambda *_args: None)
    checklist_run.run(tmp_path, {"artifact_id": "STORY-001"})
    out = capsys.readouterr().out
    assert "failed to parse" in out
    assert str(bad) in out
    assert "All automated checks passed" not in out
    logs = list((tmp_path / ".specflow" / "checklist-log").glob("*.yaml"))
    data = yaml.safe_load(logs[0].read_text(encoding="utf-8"))
    assert data["overall"] == "incomplete"
    assert data["parse_errors"]
