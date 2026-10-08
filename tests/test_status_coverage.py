"""Tests for specflow status command coverage metrics."""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.commands import status as status_cmd
from specflow.commands.status import _compute_coverage
from specflow.lib import artifacts as art_lib
from specflow.lib import config as config_lib
from specflow.lib import scaffold as scaffold_lib

_SCHEMA_DIR = Path(__file__).parent.parent / "src" / "specflow" / "templates" / "schemas"


def _scaffold_project(root: Path) -> None:
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    for schema_file in _SCHEMA_DIR.glob("*.yaml"):
        (schema_dir / schema_file.name).write_text(
            schema_file.read_text(encoding="utf-8"), encoding="utf-8"
        )
    config_lib.write_config(root, config_lib.default_config(root.name))
    config_lib.write_state(root, config_lib.default_state())
    scaffold_lib.create_spec_dirs(root)


def _make_art(art_id: str, art_type: str, status: str = "implemented",
              links: list[art_lib.Link] | None = None) -> art_lib.Artifact:
    return art_lib.Artifact(
        path=Path(f"artifact.md"),
        frontmatter={"id": art_id, "title": f"Test {art_id}", "type": art_type, "status": status},
        body="body",
        links=links or [],
    )


class TestReqCoverage:
    def test_no_reqs(self):
        result = _compute_coverage([_make_art("STORY-001", "story")])
        assert result["req_pct"] is None
        assert result["req_total"] == 0

    def test_req_with_story(self):
        arts = [
            _make_art("REQ-001", "requirement"),
            _make_art("STORY-001", "story", links=[art_lib.Link(target="REQ-001", role="implements")]),
        ]
        result = _compute_coverage(arts)
        assert result["req_total"] == 1
        assert result["req_covered"] == 1
        assert result["req_pct"] == 100.0

    def test_req_without_story(self):
        arts = [
            _make_art("REQ-001", "requirement"),
            _make_art("REQ-002", "requirement"),
            _make_art("STORY-001", "story", links=[art_lib.Link(target="REQ-001", role="implements")]),
        ]
        result = _compute_coverage(arts)
        assert result["req_total"] == 2
        assert result["req_covered"] == 1
        assert result["req_pct"] == 50.0

    def test_req_with_story_via_derives_from(self):
        # A4: derives_from (the legacy-story pattern) counts as coverage exactly
        # like implements — status coverage must agree with trace/check_coverage.
        arts = [
            _make_art("REQ-001", "requirement"),
            _make_art("STORY-001", "story", links=[art_lib.Link(target="REQ-001", role="derives_from")]),
        ]
        result = _compute_coverage(arts)
        assert result["req_total"] == 1
        assert result["req_covered"] == 1
        assert result["req_pct"] == 100.0


class TestStoryTestCoverage:
    def test_no_stories(self):
        result = _compute_coverage([_make_art("REQ-001", "requirement")])
        assert result["story_pct"] is None
        assert result["story_total"] == 0

    def test_story_with_verified_spec(self):
        arts = [
            _make_art("REQ-001", "requirement"),
            _make_art("STORY-001", "story", links=[art_lib.Link(target="REQ-001", role="implements")]),
            _make_art("QT-001", "qualification-test", links=[art_lib.Link(target="REQ-001", role="verified_by"), art_lib.Link(target="STORY-001", role="verified_by")]),
        ]
        result = _compute_coverage(arts)
        assert result["story_total"] == 1
        assert result["story_tested"] == 1
        assert result["story_avg_tests"] == 1.0
        assert result["story_pct"] == 100.0

    def test_story_without_verified_spec(self):
        arts = [
            _make_art("REQ-001", "requirement"),
            _make_art("STORY-001", "story", links=[art_lib.Link(target="REQ-001", role="implements")]),
        ]
        result = _compute_coverage(arts)
        assert result["story_total"] == 1
        assert result["story_tested"] == 0
        assert result["story_pct"] == 0.0


class TestChainCompleteness:
    def test_no_specs(self):
        result = _compute_coverage([_make_art("STORY-001", "story")])
        assert result["chain_pct"] is None
        assert result["chain_total"] == 0

    def test_spec_with_verification(self):
        arts = [
            _make_art("DDD-001", "detailed-design"),
            _make_art("UT-001", "unit-test", links=[art_lib.Link(target="DDD-001", role="verified_by")]),
        ]
        result = _compute_coverage(arts)
        assert result["chain_total"] == 1
        assert result["chain_verified"] == 1
        assert result["chain_pct"] == 100.0

    def test_spec_without_verification(self):
        arts = [
            _make_art("DDD-001", "detailed-design"),
            _make_art("REQ-001", "requirement"),
        ]
        result = _compute_coverage(arts)
        assert result["chain_total"] == 2
        assert result["chain_verified"] == 0
        assert result["chain_pct"] == 0.0

    def test_mixed_verification(self):
        arts = [
            _make_art("DDD-001", "detailed-design"),
            _make_art("UT-001", "unit-test", links=[art_lib.Link(target="DDD-001", role="verified_by")]),
            _make_art("REQ-001", "requirement"),
        ]
        result = _compute_coverage(arts)
        assert result["chain_total"] == 2
        assert result["chain_verified"] == 1
        assert result["chain_pct"] == 50.0


class TestCategoryRowRendering:
    """STORY-066 / DDD-024 §rendering rule: a category row renders only when count > 0."""

    def test_empty_project_renders_no_category_rows(self, tmp_path: Path, capsys):
        _scaffold_project(tmp_path)
        rc = status_cmd.run(tmp_path, {})
        assert rc == 0
        out = capsys.readouterr().out
        for label in ("Specs:", "Work:", "Reviews:", "Research:"):
            assert label not in out, f"{label!r} should not render on a zero-artifact project"

    def test_project_with_one_req_renders_only_specs_row(self, tmp_path: Path, capsys):
        _scaffold_project(tmp_path)
        art_lib.create_artifact(tmp_path, artifact_type="requirement", title="Sample", status="draft")
        rc = status_cmd.run(tmp_path, {})
        assert rc == 0
        out = capsys.readouterr().out
        assert "Specs:" in out
        assert "Work:" not in out
        assert "Reviews:" not in out
        assert "Research:" not in out

    def test_render_order_is_spec_work_review(self, tmp_path: Path, capsys):
        _scaffold_project(tmp_path)
        art_lib.create_artifact(tmp_path, artifact_type="requirement", title="R", status="draft")
        art_lib.create_artifact(tmp_path, artifact_type="story", title="S", status="draft")
        art_lib.create_artifact(tmp_path, artifact_type="review", title="V", status="open")
        rc = status_cmd.run(tmp_path, {})
        assert rc == 0
        out = capsys.readouterr().out
        spec_pos = out.find("Specs:")
        work_pos = out.find("Work:")
        review_pos = out.find("Reviews:")
        assert spec_pos != -1 and work_pos != -1 and review_pos != -1
        assert spec_pos < work_pos < review_pos, (
            "Row order must be spec → work → review per DDD-024"
        )


class TestExecutingPhaseApprovedGuard:
    """Core-signal honesty: the executing-phase suggestion must not claim
    /specflow-execute when zero stories are approved-or-beyond
    (approved/implemented/verified). A stale or manually-rewound phase can
    leave 'executing' set with nothing approved to run."""

    def test_executing_no_approved_stories_routes_to_plan(self, tmp_path):
        suggestion = status_cmd._suggest_action(
            tmp_path, "executing", {"REQ": 1, "ARCH": 1, "STORY": 2},
            approved_stories=0,
        )
        assert "/specflow-execute" not in suggestion
        assert "/specflow-plan" in suggestion

    def test_executing_with_approved_stories_routes_to_execute(self, tmp_path):
        suggestion = status_cmd._suggest_action(
            tmp_path, "executing", {"REQ": 1, "STORY": 2},
            approved_stories=2,
        )
        assert "/specflow-execute" in suggestion

    def test_executing_implemented_counts_as_approved(self, tmp_path):
        """Implemented stories crossed the approval gate — they count as
        approved-plus, so the executing suggestion still routes to execute,
        not back to plan."""
        suggestion = status_cmd._suggest_action(
            tmp_path, "executing", {"REQ": 1, "STORY": 2},
            approved_stories=2,
        )
        assert "/specflow-execute" in suggestion


class TestChainAgreesWithMissingPairs:
    """F-080: one V-pair metric on the dashboard. The 'Chain a/b' fraction is
    derived from find_missing_v_pairs, so b - a == the 'N missing verification
    pairs' count on the same screen — a STORY's verified_by (wrong type) no
    longer counts a REQ as verified."""

    def _arts(self):
        return [
            _make_art("REQ-001", "requirement"),                       # paired by QT
            _make_art("QT-001", "qualification-test",
                      links=[art_lib.Link(target="REQ-001", role="verified_by")]),
            _make_art("REQ-002", "requirement"),                       # only a STORY claims it
            _make_art("STORY-001", "story",
                      links=[art_lib.Link(target="REQ-002", role="verified_by")]),
            _make_art("DDD-001", "detailed-design"),                   # paired by UT
            _make_art("UT-001", "unit-test",
                      links=[art_lib.Link(target="DDD-001", role="verified_by")]),
            _make_art("ARCH-001", "architecture"),                     # unpaired
        ]

    def test_chain_total_minus_verified_equals_missing_pairs(self):
        arts = self._arts()
        cov = _compute_coverage(arts)
        health = status_cmd._count_link_health(arts)
        assert cov["chain_total"] - cov["chain_verified"] == health["missing_pairs"]
        assert cov["chain_verified"] == 2
        assert health["missing_pairs"] == 2

    def test_story_verified_by_does_not_pair_a_req(self):
        arts = [
            _make_art("REQ-002", "requirement"),
            _make_art("STORY-001", "story",
                      links=[art_lib.Link(target="REQ-002", role="verified_by")]),
        ]
        cov = _compute_coverage(arts)
        assert cov["chain_verified"] == 0

    def test_dashboard_numbers_agree_end_to_end(self, tmp_path: Path, capsys):
        import re
        _scaffold_project(tmp_path)
        art_lib.create_artifact(tmp_path, "requirement", title="R1", status="approved", body="b")
        art_lib.create_artifact(tmp_path, "requirement", title="R2", status="approved", body="b")
        art_lib.create_artifact(
            tmp_path, "qualification-test", title="Q1", status="approved", body="b",
            links=[{"target": "REQ-001", "role": "verified_by"}],
        )
        status_cmd.run(tmp_path, {})
        out = capsys.readouterr().out
        missing = int(re.search(r"(\d+) missing verification pairs", out).group(1))
        a, b = map(int, re.search(r"Chain \d+% \((\d+)/(\d+)\)", out).group(1, 2))
        assert b - a == missing == 1


class TestStatusLineFromCounter:
    """F-080: the Status line renders every status present, core lifecycle
    first, so artifacts in open/closed/accepted/… are no longer hidden."""

    def test_render_order_core_then_extras_sorted(self):
        by_status = {"open": 3, "draft": 1, "accepted": 2, "verified": 4, "closed": 1}
        assert status_cmd._status_render_order(by_status)[:7] == status_cmd._CORE_STATUS_ORDER
        assert status_cmd._status_render_order(by_status)[7:] == ["accepted", "closed", "open"]

    def test_dashboard_shows_non_core_statuses(self, tmp_path: Path, capsys):
        _scaffold_project(tmp_path)
        art_lib.create_artifact(tmp_path, "requirement", title="R1", status="approved", body="b")
        art_lib.create_artifact(tmp_path, "defect", title="D1", status="open", body="b")
        status_cmd.run(tmp_path, {})
        out = capsys.readouterr().out
        status_line = next(ln for ln in out.splitlines() if ln.strip().startswith("Status:"))
        assert "1 approved" in status_line and "1 open" in status_line


class TestSuggestActionExecutableStories:
    """F-002 (status half): zero executable (approved) stories never yields
    'use /specflow-execute', whatever the implemented/verified mix."""

    def test_executing_done_backlog_routes_to_review_then_ship(self, tmp_path):
        s = status_cmd._suggest_action(
            tmp_path, "executing", {"STORY": 176},
            approved_stories=172, executable_stories=0, stories_done=True,
        )
        assert "/specflow-execute" not in s
        assert "/specflow-artifact-review" in s and "/specflow-ship" in s

    def test_executing_pending_backlog_routes_to_plan_reconcile(self, tmp_path):
        s = status_cmd._suggest_action(
            tmp_path, "executing", {"STORY": 3},
            approved_stories=1, executable_stories=0, stories_done=False,
        )
        assert "/specflow-execute" not in s
        assert "/specflow-plan" in s and "reconcile" in s

    def test_planning_pending_backlog_never_says_execute(self, tmp_path):
        """Planning, implemented + draft mix (0 approved): brief says
        'finish /specflow-plan'; status must not say execute."""
        s = status_cmd._suggest_action(
            tmp_path, "planning", {"REQ": 1, "ARCH": 1, "STORY": 8},
            approved_stories=5, executable_stories=0, stories_done=False,
        )
        assert "/specflow-execute" not in s
        assert "/specflow-plan" in s

    def test_planning_with_executable_stories_says_execute(self, tmp_path):
        s = status_cmd._suggest_action(
            tmp_path, "planning", {"REQ": 1, "ARCH": 1, "STORY": 8},
            approved_stories=5, executable_stories=2, stories_done=False,
        )
        assert "/specflow-execute" in s

    def test_run_planning_implemented_plus_draft_routes_to_plan(self, tmp_path: Path, capsys):
        """End to end: planning phase, implemented + draft stories, nothing
        approved → the dashboard agrees with brief (plan, not execute)."""
        _scaffold_project(tmp_path)
        config_lib.write_state(tmp_path, {"current": "planning", "history": []})
        art_lib.create_artifact(tmp_path, "requirement", title="R1", status="approved", body="b")
        art_lib.create_artifact(tmp_path, "architecture", title="A1", status="approved", body="b")
        art_lib.create_artifact(tmp_path, "story", title="S1", status="implemented", body="b")
        art_lib.create_artifact(tmp_path, "story", title="S2", status="draft", body="b")
        status_cmd.run(tmp_path, {})
        out = capsys.readouterr().out
        suggestion = next(ln for ln in out.splitlines() if "→" in ln)
        assert "/specflow-execute" not in suggestion
        assert "/specflow-plan" in suggestion

    def test_planning_done_backlog_routes_to_review(self, tmp_path):
        s = status_cmd._suggest_action(
            tmp_path, "planning", {"STORY": 3},
            approved_stories=3, executable_stories=0, stories_done=True,
        )
        assert "/specflow-artifact-review" in s

    def test_run_passes_live_story_progress(self, tmp_path: Path, capsys):
        """End to end on a project whose stories are all verified/implemented
        plus one deprecated: the dashboard must not say execute."""
        _scaffold_project(tmp_path)
        config_lib.write_state(tmp_path, {"current": "executing", "history": []})
        art_lib.create_artifact(tmp_path, "requirement", title="R1", status="approved", body="b")
        art_lib.create_artifact(tmp_path, "story", title="S1", status="verified", body="b")
        art_lib.create_artifact(tmp_path, "story", title="S2", status="implemented", body="b")
        art_lib.create_artifact(tmp_path, "story", title="S3", status="deprecated", body="b")
        status_cmd.run(tmp_path, {})
        out = capsys.readouterr().out
        suggestion = next(ln for ln in out.splitlines() if "→" in ln)
        assert "/specflow-execute" not in suggestion
        assert "/specflow-artifact-review" in suggestion
