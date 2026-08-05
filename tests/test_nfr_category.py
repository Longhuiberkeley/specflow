"""Tests for the NFR category vocabulary (CHL-344 A4).

Covers the three surfaces the frozen vocabulary plugs into:
  - lib/lint.py: NFR_CATEGORIES constant + validate_nfr_category helper.
  - cli.py: `create --nfr-category` argparse choices (create-boundary gate).
  - artifact_lint._check_nfr_category: warn-only typo net for the generic
    freeform `update --set non_functional_category=...` path.

Deliberate omissions pinned here: no .specflow/schema enum key (the ROADMAP
Schema-sync workstream owns schema drift), no REQ frontmatter edits (A5 owns
the data half), and `update --set` stays freeform (the lint check is its net).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specflow.commands.artifact_lint import _check_nfr_category
from specflow.lib import artifacts as art_lib
from specflow.lib import lint as lint_lib


def _make_req(req_id: str, category=None) -> art_lib.Artifact:
    fm: dict = {
        "id": req_id, "title": f"Test {req_id}",
        "type": "requirement", "status": "approved",
    }
    if category is not None:
        fm["non_functional_category"] = category
    return art_lib.Artifact(
        path=Path(f"_specflow/specs/requirements/{req_id}.md"),
        frontmatter=fm,
        body="# Test\n\n## Acceptance Criteria\n\n1. Given X, when Y, then Z\n",
        links=[],
    )


# ── Vocabulary source of truth ───────────────────────────────────────────────


class TestVocabulary:
    def test_frozen_vocabulary_is_exactly_the_eight_values(self):
        assert lint_lib.NFR_CATEGORIES == (
            "functional", "performance", "security", "reliability",
            "usability", "maintainability", "scalability", "compliance",
        )

    def test_all_vocabulary_values_validate_clean(self):
        for cat in lint_lib.NFR_CATEGORIES:
            assert lint_lib.validate_nfr_category(cat) is None, cat

    def test_functional_is_sanctioned_vocabulary_not_a_typo(self):
        # Bookkeeping value: projects mark functional REQs so the NFR
        # measurable-threshold gate can exempt them. It must validate clean.
        assert lint_lib.validate_nfr_category("functional") is None

    def test_unknown_value_returns_error_string(self):
        err = lint_lib.validate_nfr_category("perfomance")
        assert err is not None
        assert "perfomance" in err
        assert "frozen vocabulary" in err

    def test_validation_is_case_insensitive(self):
        # Precedent: _check_acceptance lowercases before comparing to
        # "functional". The typo net is about vocabulary membership, not case.
        assert lint_lib.validate_nfr_category("Performance") is None
        assert lint_lib.validate_nfr_category(" SECURITY ") is None


# ── artifact-lint typo net (_check_nfr_category) ─────────────────────────────


class TestLintNfrCategoryCheck:
    def test_all_vocabulary_values_pass(self):
        arts = [_make_req(f"REQ-{i:03d}", cat)
                for i, cat in enumerate(lint_lib.NFR_CATEGORIES, start=1)]
        result = _check_nfr_category(arts)
        assert result["blocking_count"] == 0
        assert result["warning_count"] == 0

    def test_unknown_value_warns_never_blocks(self):
        arts = [_make_req("REQ-100", "perfomance")]
        result = _check_nfr_category(arts)
        assert result["blocking_count"] == 0   # warn-only, never an error
        assert result["warning_count"] == 1
        assert "REQ-100" in result["detail"]
        assert "perfomance" in result["detail"]

    def test_one_warning_per_offending_req(self):
        arts = [
            _make_req("REQ-100", "fastness"),
            _make_req("REQ-101", "sec"),
            _make_req("REQ-102", "security"),  # clean
        ]
        result = _check_nfr_category(arts)
        assert result["warning_count"] == 2
        assert result["blocking_count"] == 0

    def test_missing_field_passes(self):
        # No category-presence mandate this slice — absence is not an offense.
        arts = [_make_req("REQ-100"), _make_req("REQ-101")]
        result = _check_nfr_category(arts)
        assert result["blocking_count"] == 0
        assert result["warning_count"] == 0

    def test_empty_value_treated_as_missing(self):
        arts = [_make_req("REQ-100", "")]
        result = _check_nfr_category(arts)
        assert result["warning_count"] == 0

    def test_non_req_artifacts_ignored(self):
        art = art_lib.Artifact(
            path=Path("_specflow/specs/architecture/ARCH-001.md"),
            frontmatter={"id": "ARCH-001", "type": "architecture",
                         "status": "approved",
                         "non_functional_category": "totally-bogus"},
            body="# A", links=[],
        )
        result = _check_nfr_category([art])
        assert result["warning_count"] == 0

    def test_registered_in_check_names(self):
        from specflow.commands import artifact_lint as lint_cmd
        assert "nfr-category" in lint_cmd.CHECK_NAMES


# ── Create-boundary choices (cli.py) ─────────────────────────────────────────


class TestCreateBoundaryChoices:
    def test_bogus_nfr_category_rejected_at_cli(self, capsys):
        from specflow import cli
        with pytest.raises(SystemExit) as exc:
            cli.main(["create", "--type", "requirement", "--title", "T",
                      "--nfr-category", "perfomance"])
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "invalid choice" in err

    def test_all_vocabulary_values_accepted_by_parser(self):
        from specflow.cli import build_parser
        parser = build_parser()
        for cat in lint_lib.NFR_CATEGORIES:
            ns = parser.parse_args(
                ["create", "--type", "requirement", "--title", "T",
                 "--nfr-category", cat]
            )
            assert ns.nfr_category == cat

    def test_help_generated_from_constant(self, capsys):
        # The help prose enumerates the frozen vocabulary — generated from
        # NFR_CATEGORIES so it can never drift from the enforced values again.
        from specflow.cli import build_parser
        parser = build_parser()
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["create", "--help"])
        assert exc.value.code == 0
        help_text = capsys.readouterr().out
        for cat in lint_lib.NFR_CATEGORIES:
            assert cat in help_text, cat


# ── Functional exemption regression (kept green) ─────────────────────────────


def test_functional_exemption_in_threshold_gate_still_green():
    """The A4 vocabulary work must not disturb the pre-existing exemption:
    `non_functional_category: functional` gets no NFR measurable-threshold
    warning from _check_acceptance (pinned in test_lint_quality_gates.py)."""
    from specflow.commands.artifact_lint import _check_acceptance

    req = _make_req("REQ-901")
    req.frontmatter["non_functional_category"] = "functional"
    req.body = "# Test\n\n## Acceptance Criteria\n\n- behaves correctly\n"
    result = _check_acceptance([req])
    assert "REQ-901" not in result["detail"]
    # And functional is inside the vocabulary, so the typo net is silent too.
    assert _check_nfr_category([req])["warning_count"] == 0
