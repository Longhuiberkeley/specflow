"""Tests for canonical link-role normalization (role_normalize + lint integration)."""

from __future__ import annotations

from pathlib import Path

import pytest

from specflow.lib import role_normalize
from specflow.lib import artifacts as art_lib
from specflow.lib import lint as lint_lib


# ── role_normalize.suggest_canonical ─────────────────────────────────────────

class TestSuggestCanonical:
    def test_synonym_maps_to_canonical(self):
        s = role_normalize.suggest_canonical("validates")
        assert s is not None
        assert s.kind == "synonym"
        assert s.target == "validated_by"
        assert "validated_by" in s.hint

    def test_extends_is_synonym_for_refined_by(self):
        s = role_normalize.suggest_canonical("extends")
        assert s is not None
        assert s.kind == "synonym"
        assert s.target == "refined_by"

    def test_inverse_points_to_canonical_and_trace(self):
        s = role_normalize.suggest_canonical("superseded_by")
        assert s is not None
        assert s.kind == "inverse"
        assert s.target == "supersedes"
        assert "trace" in s.hint

    def test_lifecycle_role_suggests_status(self):
        s = role_normalize.suggest_canonical("cancels")
        assert s is not None
        assert s.kind == "lifecycle"
        assert s.target == "cancelled"
        assert "status: cancelled" in s.hint

    def test_deprecates_is_lifecycle(self):
        s = role_normalize.suggest_canonical("deprecates")
        assert s is not None
        assert s.kind == "lifecycle"
        assert s.target == "deprecated"

    def test_case_and_whitespace_insensitive(self):
        s = role_normalize.suggest_canonical("  SuperSeded_By ")
        assert s is not None
        assert s.target == "supersedes"

    def test_unknown_role_returns_none(self):
        assert role_normalize.suggest_canonical("totally_made_up_role") is None

    def test_empty_role_returns_none(self):
        assert role_normalize.suggest_canonical("") is None
        assert role_normalize.suggest_canonical("   ") is None

    @pytest.mark.parametrize(
        "alias,kind",
        [
            ("mandates", "synonym"),
            ("informed_by", "synonym"),
            ("produces", "inverse"),
            ("refines", "inverse"),
            ("withdraws", "lifecycle"),
            ("obsoletes", "lifecycle"),
        ],
    )
    def test_representative_aliases(self, alias: str, kind: str):
        s = role_normalize.suggest_canonical(alias)
        assert s is not None and s.kind == kind


# ── lint integration: enriched warning ───────────────────────────────────────

class TestLintEnrichedWarning:
    _SCHEMA = {
        "type": "requirement",
        "allowed_status": {"draft": []},
        "allowed_link_roles": ["refined_by", "derives_from", "verified_by"],
    }

    def _lint_role(self, role: str) -> list[dict]:
        art = art_lib.Artifact(
            path=Path("REQ-001.md"),
            frontmatter={"id": "REQ-001", "title": "T", "type": "requirement", "status": "draft"},
            body="body",
            links=[art_lib.Link(target="REQ-002", role=role)],
        )
        return lint_lib.validate_artifact_schema(art, self._SCHEMA)

    def test_known_alias_warns_with_suggestion(self):
        issues = self._lint_role("superseded_by")
        warnings = [i for i in issues if i["severity"] == "warning"]
        assert len(warnings) == 1
        msg = warnings[0]["message"]
        # Recognized aliases (synonym/inverse/lifecycle) are "Non-canonical", not
        # "Unknown" — the tool itself recognizes them, so the old "Unknown" label
        # was self-contradicting.
        assert 'Non-canonical link role "superseded_by"' in msg
        assert "supersedes" in msg and "trace" in msg

    def test_lifecycle_alias_warns_with_status_hint(self):
        issues = self._lint_role("cancels")
        msg = next(i["message"] for i in issues if i["severity"] == "warning")
        assert "status: cancelled" in msg

    def test_unmapped_role_warns_without_suggestion(self):
        issues = self._lint_role("frobnicates")
        warnings = [i for i in issues if i["severity"] == "warning"]
        assert len(warnings) == 1
        assert "—" not in warnings[0]["message"]

    def test_canonical_role_produces_no_warning(self):
        issues = self._lint_role("derives_from")
        assert not [i for i in issues if i["severity"] == "warning"]
