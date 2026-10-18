"""REQ-069 OBL-7 / AC9 (STORY-744, DEC-104): a DEC tagged `framing` with no
links is a complete ruling on a fuzzy idea, not an orphan; without the tag the
`links/orphan` row fires exactly as before. Rule id unchanged, so the negative
fixture registry is untouched."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from conftest import write_artifact
from test_artifact_lint import project_root  # noqa: F401 — reuse scaffold fixture

from specflow.commands import artifact_lint as lint_cmd


def _orphan_subjects(root: Path) -> set[str]:
    _, findings = lint_cmd.collect(root.resolve(), ["links"], as_of=date(2026, 10, 18))
    return {f.subjects[0] for f in findings if f.rule_id == "links/orphan"}


def test_framing_tagged_decision_is_not_an_orphan(project_root: Path):
    write_artifact(project_root, "DEC-900", "decision", "Dropped: some kind of dashboard",
                   status="approved", tags=["framing"])
    assert "DEC-900" not in _orphan_subjects(project_root)


def test_untagged_decision_still_trips_orphan(project_root: Path):
    write_artifact(project_root, "DEC-901", "decision", "Keep argparse", status="approved")
    assert "DEC-901" in _orphan_subjects(project_root)


def test_framing_tag_on_other_types_is_not_an_exemption(project_root: Path):
    write_artifact(project_root, "REQ-900", "requirement", "Tagged but not a DEC",
                   status="approved", tags=["framing"])
    assert "REQ-900" in _orphan_subjects(project_root)
