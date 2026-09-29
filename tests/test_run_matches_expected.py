"""STORY-699 / REQ-058 AC1 — one expected-exit helper, four readers agree.

A recorded verify run counts as PASSING exactly when its exit code equals the
declared ``verify_exit_code`` (default 0). Before STORY-699 the four readers
(brief, evidence, risk tier, project audit) each re-derived that rule and
disagreed:

- brief dropped a failing run when ``verify_exit_code`` was unset (it only
  flagged divergence when a code was *declared*);
- evidence hard-coded ``"0"`` as the pass code, so a contract declaring
  ``verify_exit_code: 2`` that exited 2 was shown as a failure (and one that
  exited 0 was shown as a pass).

This module pins the shared helper and then drives every reader over the same
matrix (unset / zero / non-zero declared codes, int and string spellings) so a
reader that re-derives the rule on its own is caught. DEF-004 is exposed here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specflow.commands import brief as brief_cmd
from specflow.commands import project_audit as audit_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import evidence as evidence_lib
from specflow.lib import risk as risk_lib


# (declared verify_exit_code or _UNSET, recorded verify_run_exit_code, expected pass?)
_UNSET = object()
MATRIX = [
    pytest.param(_UNSET, 0, True, id="unset-exit0-pass"),
    pytest.param(_UNSET, 1, False, id="unset-exit1-fail"),
    pytest.param(_UNSET, 2, False, id="unset-exit2-fail"),
    pytest.param(0, 0, True, id="zero-exit0-pass"),
    pytest.param(0, 1, False, id="zero-exit1-fail"),
    pytest.param(2, 2, True, id="two-exit2-pass"),
    pytest.param(2, 0, False, id="two-exit0-fail"),
    pytest.param(2, 1, False, id="two-exit1-fail"),
    pytest.param("2", 2, True, id="str2-exit2-pass"),
    pytest.param(2, "2", True, id="two-strexit2-pass"),
    pytest.param("0", "1", False, id="str0-strexit1-fail"),
]


def _fm(declared, recorded, *, run_at: str | None = "2026-09-30T00:00:00Z") -> dict:
    fm: dict = {"verify_command": "pytest -q"}
    if declared is not _UNSET:
        fm["verify_exit_code"] = declared
    if recorded is not None:
        fm["verify_run_exit_code"] = recorded
    if run_at is not None:
        fm["verify_run_at"] = run_at
    return fm


def _art(art_id: str, art_type: str, status: str, extra: dict | None = None,
         links: list[art_lib.Link] | None = None, body: str = "") -> art_lib.Artifact:
    fm = {"id": art_id, "title": art_id, "type": art_type, "status": status}
    fm.update(extra or {})
    return art_lib.Artifact(
        path=Path(f"_specflow/{art_id}.md"), frontmatter=fm, body=body,
        links=list(links or []),
    )


# ── the helper ────────────────────────────────────────────────────


class TestHelper:
    @pytest.mark.parametrize("declared,recorded,expected", MATRIX)
    def test_matrix(self, declared, recorded, expected):
        from specflow.lib.verification import run_matches_expected

        assert run_matches_expected(_fm(declared, recorded)) is expected

    def test_no_run_recorded_is_none(self):
        from specflow.lib.verification import run_matches_expected

        assert run_matches_expected({"verify_command": "pytest"}) is None
        assert run_matches_expected({}) is None
        assert run_matches_expected({"verify_exit_code": 2}) is None

    def test_blank_declared_code_defaults_to_zero(self):
        from specflow.lib.verification import run_matches_expected

        assert run_matches_expected(
            {"verify_exit_code": None, "verify_run_exit_code": 0}) is True
        assert run_matches_expected(
            {"verify_exit_code": "", "verify_run_exit_code": 1}) is False

    def test_whitespace_tolerant_string_codes(self):
        from specflow.lib.verification import run_matches_expected

        assert run_matches_expected(
            {"verify_exit_code": " 2 ", "verify_run_exit_code": "2"}) is True

    def test_none_mapping_is_none(self):
        from specflow.lib.verification import run_matches_expected

        assert run_matches_expected(None) is None


# ── reader 1: brief (next-skill verify advisory) ──────────────────


class TestBriefReader:
    @pytest.mark.parametrize("declared,recorded,expected", MATRIX)
    def test_brief_agrees(self, declared, recorded, expected):
        arts = [_art("UT-001", "unit-test", "implemented", _fm(declared, recorded))]
        out = brief_cmd._next_skill_recommendation("executing", arts, [], [])
        flagged = "UT-001" in out and "specflow verify" in out
        assert flagged is (not expected), out

    def test_brief_flags_never_run(self):
        arts = [_art("UT-001", "unit-test", "implemented", _fm(_UNSET, None, run_at=None))]
        out = brief_cmd._next_skill_recommendation("executing", arts, [], [])
        assert "UT-001" in out


# ── reader 2: evidence report (test-results section) ─────────────


class TestEvidenceReader:
    @pytest.mark.parametrize("declared,recorded,expected", MATRIX)
    def test_evidence_agrees(self, declared, recorded, expected):
        arts = [_art("UT-001", "unit-test", "verified", _fm(declared, recorded))]
        lines = evidence_lib._test_results_section(arts)
        row = next(ln for ln in lines if ln.startswith("| UT-001 "))
        assert f"verify_run exit={recorded}" in row
        failed = "see audit" in row
        assert failed is (not expected), row

    def test_evidence_no_run_no_annotation(self):
        arts = [_art("UT-001", "unit-test", "verified", {"verify_command": "pytest"})]
        lines = evidence_lib._test_results_section(arts)
        row = next(ln for ln in lines if ln.startswith("| UT-001 "))
        assert "verify_run" not in row


# ── reader 3: risk tier (verification_evidence) ──────────────────


class TestRiskReader:
    @pytest.mark.parametrize("declared,recorded,expected", MATRIX)
    def test_risk_agrees(self, declared, recorded, expected):
        arts = [
            _art("STORY-001", "story", "implemented"),
            _art("UT-001", "unit-test", "implemented", _fm(declared, recorded),
                 links=[art_lib.Link(target="STORY-001", role="verified_by")]),
        ]
        ev = risk_lib.verification_evidence(["STORY-001"], arts)
        assert ev == ("ran (1 green)" if expected else "not-run"), ev

    def test_risk_run_exit_without_run_at_is_not_green(self):
        arts = [
            _art("STORY-001", "story", "implemented"),
            _art("UT-001", "unit-test", "implemented", _fm(0, 0, run_at=None),
                 links=[art_lib.Link(target="STORY-001", role="verified_by")]),
        ]
        assert risk_lib.verification_evidence(["STORY-001"], arts) == "not-run"


# ── reader 4: project audit (verification + ac-coverage lenses) ──


class TestProjectAuditReader:
    @pytest.mark.parametrize("declared,recorded,expected", MATRIX)
    def test_verification_lens_agrees(self, declared, recorded, expected):
        arts = [_art("UT-001", "unit-test", "implemented", _fm(declared, recorded))]
        findings = audit_cmd._verification_lens(arts)
        failed = any(
            f["severity"] == "warn" and "UT-001" in f["message"]
            and "failed" in f["message"]
            for f in findings
        )
        assert failed is (not expected), findings

    @pytest.mark.parametrize("declared,recorded,expected", MATRIX)
    def test_ac_coverage_lens_agrees(self, declared, recorded, expected):
        req_body = "## Acceptance Criteria\n\n1. One.\n2. Two.\n3. Three.\n"
        arts = [
            _art("REQ-001", "requirement", "implemented", body=req_body),
            _art("QT-001", "qualification-test", "implemented", _fm(declared, recorded),
                 links=[art_lib.Link(target="REQ-001", role="verified_by")]),
        ]
        findings = audit_cmd._ac_coverage_lens(arts)
        msg = next(f["message"] for f in findings if "REQ-001" in f["message"])
        assert ("(1 green)" if expected else "(0 green)") in msg, msg


def test_all_readers_route_through_the_shared_helper():
    """Structural guard: each reader module calls run_matches_expected, so the
    rule lives in one place and a future reader cannot silently re-derive it."""
    import inspect

    for mod in (brief_cmd, audit_cmd, evidence_lib, risk_lib):
        assert "run_matches_expected" in inspect.getsource(mod), mod.__name__
