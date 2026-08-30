"""Locking tests for the v1.14.5 schema/lint registrations (STORY-647).

v1.14.5 shipped four wiring changes with zero locking coverage (UT-079/IT-046
recorded green runs over suites that never exercised them — the evidentiary
gap found in the v1.14.5 post-release audit):

  1. experiment.yaml optional_fields += ``competition`` (stamped on every
     logged EXPT by the autoresearch CLI; omission produced one unknown-field
     info finding per experiment, ~50 per LOOP).
  2. competition.yaml optional_fields += ``custom_categories``
     (protocol-instructed on COMP creation).
  3. loop.yaml allowed_link_roles += ``derives_from`` (the LOOP→MON escalation
     edge; matches finding/run/monitor siblings).
  4. lint accepts protocol-shaped ``condensation_brief_<N>`` stamps alongside
     the plural ``condensation_briefs`` (loop.yaml lists only the plural).

These tests pin all four: silently reverting any registration fails here
instead of shipping unnoticed.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import lint as lint_lib

PACK_SCHEMAS = (
    Path(__file__).parent.parent / "src" / "specflow" / "packs" / "autoresearch" / "schemas"
)


def _schema(name: str) -> dict:
    return yaml.safe_load((PACK_SCHEMAS / name).read_text(encoding="utf-8"))


def _art(fm: dict, links: list[art_lib.Link] | None = None) -> art_lib.Artifact:
    return art_lib.Artifact(
        path=Path(f"{fm['id']}.md"),
        frontmatter=fm,
        body="body",
        links=links or [],
    )


def _no_unknown_field_or_role_issues(issues: list[dict]) -> None:
    bad = [
        i["message"] for i in issues
        if "Unknown field" in i["message"] or "Unknown link role" in i["message"]
        or "not allowed" in i["message"].lower()
    ]
    assert not bad, f"registration regressed: {bad}"


def test_expt_competition_field_registered():
    """AC: an EXPT stamped with `competition` (autoresearch CLI writes it on
    every logged experiment) produces zero unknown-field findings."""
    schema = _schema("experiment.yaml")
    assert "competition" in schema["optional_fields"], (
        "experiment.yaml lost the `competition` optional field"
    )
    fm = {
        "id": "EXPT-001",
        "title": "Locked EXPT",
        "type": "experiment",
        "status": "kept",
        "created": "2026-08-30",
        "loop": "LOOP-001",
        "competition": "COMP-001",
        "metric_value": 0.87,
        "change_category": "features",
        "summary": "locking test",
    }
    _no_unknown_field_or_role_issues(lint_lib.validate_artifact_schema(_art(fm), schema))


def test_comp_custom_categories_field_registered():
    """AC: a COMP carrying `custom_categories` (protocol-instructed) produces
    zero unknown-field findings."""
    schema = _schema("competition.yaml")
    assert "custom_categories" in schema["optional_fields"], (
        "competition.yaml lost the `custom_categories` optional field"
    )
    fm = {
        "id": "COMP-001",
        "title": "Locked COMP",
        "type": "competition",
        "status": "active",
        "created": "2026-08-30",
        "verify_command": "uv run pytest -q",
        "metric_name": "auc",
        "metric_direction": "maximize",
        "custom_categories": {"screener": ["stability", "cost"]},
    }
    _no_unknown_field_or_role_issues(lint_lib.validate_artifact_schema(_art(fm), schema))


def test_loop_numbered_condensation_briefs_accepted():
    """AC: protocol-shaped ``condensation_brief_<N>`` stamps (the protocol
    numbers them: condensation_brief_10, condensation_brief_20, …) pass lint
    alongside the plural ``condensation_briefs`` form."""
    schema = _schema("loop.yaml")
    fm = {
        "id": "LOOP-001",
        "title": "Locked LOOP",
        "type": "loop",
        "status": "running",
        "created": "2026-08-30",
        "competition": "COMP-001",
        "mode": "explore",
        "budget": "40",
        "condensation_briefs": "plural-form summary",
        "condensation_brief_10": "first protocol-stamped brief",
        "condensation_brief_20": "second protocol-stamped brief",
    }
    _no_unknown_field_or_role_issues(lint_lib.validate_artifact_schema(_art(fm), schema))


def test_loop_derives_from_link_role_allowed():
    """AC: LOOP→MON escalation edges (`derives_from`) are a legal link role —
    the edge that renders monitor-escalated loops upstream in `specflow trace`."""
    schema = _schema("loop.yaml")
    assert "derives_from" in schema["allowed_link_roles"], (
        "loop.yaml lost the `derives_from` allowed link role"
    )
    fm = {
        "id": "LOOP-001",
        "title": "Locked LOOP",
        "type": "loop",
        "status": "running",
        "created": "2026-08-30",
        "competition": "COMP-001",
        "mode": "validate",
        "budget": "20",
    }
    links = [art_lib.Link(target="MON-007", role="derives_from")]
    issues = lint_lib.validate_artifact_schema(_art(fm, links=links), schema)
    _no_unknown_field_or_role_issues(issues)
