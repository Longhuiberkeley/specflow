"""Tests for REQ acceptance-criteria emptiness and NFR measurable-threshold gates.

Design (frozen, accounting-not-policing philosophy):
  - Empty Acceptance Criteria section (header present, zero items below it)
    is an ERROR — same severity as a missing section entirely.
  - A non-functional REQ (frontmatter `non_functional_category` set) whose
    acceptance criteria contain no measurable threshold (no digit) is a
    WARNING only — this is a deterministic digit-presence check, never a
    semantic judgement, so it can never block.
"""

from __future__ import annotations

from pathlib import Path

from specflow.commands.artifact_lint import _check_acceptance
from specflow.lib import artifacts as art_lib
from specflow.lib import lint as lint_lib


def _make_req(req_id: str, body: str, extra_fm: dict | None = None) -> art_lib.Artifact:
    fm: dict = {
        "id": req_id, "title": f"Test {req_id}",
        "type": "requirement", "status": "approved",
    }
    if extra_fm:
        fm.update(extra_fm)
    return art_lib.Artifact(
        path=Path(f"_specflow/specs/requirements/{req_id}.md"),
        frontmatter=fm,
        body=body,
        links=[],
    )


# ── count_acceptance_criteria_items ─────────────────────────────────────────

class TestCountAcceptanceCriteriaItems:
    def test_empty_section_counts_zero(self):
        req = _make_req("REQ-100", "# Test\n\n## Acceptance Criteria\n\n## Notes\n\nSomething else.")
        assert lint_lib.count_acceptance_criteria_items(req) == 0

    def test_empty_section_at_end_of_body_counts_zero(self):
        req = _make_req("REQ-100", "# Test\n\n## Acceptance Criteria\n\n")
        assert lint_lib.count_acceptance_criteria_items(req) == 0

    def test_list_items_counted(self):
        req = _make_req(
            "REQ-100",
            "# Test\n\n## Acceptance Criteria\n\n- Given X, when Y, then Z\n- Given A, when B, then C\n",
        )
        assert lint_lib.count_acceptance_criteria_items(req) == 2

    def test_numbered_items_counted(self):
        req = _make_req(
            "REQ-100",
            "# Test\n\n## Acceptance Criteria\n\n1. Given X\n2. Given Y\n",
        )
        assert lint_lib.count_acceptance_criteria_items(req) == 2

    def test_no_header_falls_back_to_given_pattern(self):
        req = _make_req("REQ-100", "# Test\n\n1. Given a user is logged in")
        assert lint_lib.count_acceptance_criteria_items(req) == 1

    def test_no_header_no_given_pattern_counts_zero(self):
        req = _make_req("REQ-100", "# Test\n\nThe system shall work.")
        assert lint_lib.count_acceptance_criteria_items(req) == 0


# ── _check_acceptance: empty-section error ──────────────────────────────────

class TestEmptyAcceptanceSection:
    def test_header_only_is_blocking_error(self):
        arts = [
            _make_req("REQ-100", "# Test\n\n## Acceptance Criteria\n\n## Notes\n\nfoo"),
        ]
        result = _check_acceptance(arts)
        assert result["blocking_count"] >= 1
        assert "empty Acceptance Criteria section" in result["detail"]

    def test_populated_section_passes(self):
        arts = [
            _make_req(
                "REQ-100",
                "# Test\n\n## Acceptance Criteria\n\n1. Given X, when Y, then Z\n",
            ),
        ]
        result = _check_acceptance(arts)
        assert result["blocking_count"] == 0

    def test_missing_header_still_blocking(self):
        arts = [
            _make_req("REQ-100", "# Test\n\nThe system shall work."),
        ]
        result = _check_acceptance(arts)
        assert result["blocking_count"] >= 1
        assert "no acceptance criteria found" in result["detail"]


# ── _check_acceptance: NFR measurable-threshold warning ─────────────────────

class TestNfrMeasurableThreshold:
    def test_nfr_with_digit_in_ac_has_no_warning(self):
        arts = [
            _make_req(
                "REQ-200",
                "# Test\n\n## Acceptance Criteria\n\n1. Given load, response time is under 200ms\n",
                extra_fm={"non_functional_category": "performance"},
            ),
        ]
        result = _check_acceptance(arts)
        assert result["blocking_count"] == 0
        assert result["warning_count"] == 0

    def test_nfr_without_digit_in_ac_warns(self):
        arts = [
            _make_req(
                "REQ-200",
                "# Test\n\n## Acceptance Criteria\n\n1. Given load, the system should be fast\n",
                extra_fm={"non_functional_category": "performance"},
            ),
        ]
        result = _check_acceptance(arts)
        assert result["blocking_count"] == 0
        assert result["warning_count"] >= 1
        assert "NFR (performance) has no measurable threshold" in result["detail"]
        assert "CKL-REV-REQ-02" in result["detail"]

    def test_non_nfr_req_without_digit_has_no_nfr_warning(self):
        arts = [
            _make_req(
                "REQ-200",
                "# Test\n\n## Acceptance Criteria\n\n1. Given a user is logged in, they see the dashboard\n",
            ),
        ]
        result = _check_acceptance(arts)
        assert result["blocking_count"] == 0
        assert result["warning_count"] == 0

    def test_nfr_warning_never_blocks(self):
        # Even with zero digits, the NFR gate is a warning — never blocking.
        arts = [
            _make_req(
                "REQ-200",
                "# Test\n\n## Acceptance Criteria\n\n1. Should behave reliably under load\n",
                extra_fm={"non_functional_category": "reliability"},
            ),
        ]
        result = _check_acceptance(arts)
        assert result["blocking_count"] == 0
        assert result["warning_count"] >= 1

    def test_nfr_with_empty_section_only_reports_blocking_not_nfr_warning(self):
        # Empty-section error already fires; the NFR digit check should not
        # pile on a redundant warning for a section that doesn't exist.
        arts = [
            _make_req(
                "REQ-200",
                "# Test\n\n## Acceptance Criteria\n\n## Notes\n\nfoo",
                extra_fm={"non_functional_category": "performance"},
            ),
        ]
        result = _check_acceptance(arts)
        assert result["blocking_count"] >= 1
        assert result["warning_count"] == 0


def test_nfr_category_functional_is_exempt_from_threshold_warning():
    """`non_functional_category: functional` is triage bookkeeping, not an NFR —
    the measurable-threshold warning must not fire on it."""
    req = _make_req(
        "REQ-901",
        "# Test\n\n## Acceptance Criteria\n\n- behaves correctly\n",
        extra_fm={"non_functional_category": "functional"},
    )
    result = _check_acceptance([req])
    assert "REQ-901" not in result["detail"]
