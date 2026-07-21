"""Tests for project-audit CHL grouping (specflow.commands.project_audit).

Focus: the warn/error-findings → CHL batching (B2) that replaced one empty-body
CHL per finding. The grouping is a pure function (``_group_findings_to_chls``)
so it can be exercised directly without running the full audit pipeline.
"""

from __future__ import annotations

from specflow.commands import project_audit as audit_cmd


def _f(axis: str, severity: str, message: str, **extra) -> dict:
    d = {"axis": axis, "severity": severity, "message": message}
    d.update(extra)
    return d


class TestGroupFindingsToChls:
    def test_one_chl_per_category_with_table_body(self):
        # B2: N findings of one (axis, category) collapse to ONE CHL finding
        # whose body is an N-row table; severity = max of the group.
        findings = [
            _f("horizontal", "warn", "no acceptance criteria", type="story"),
            _f("horizontal", "warn", "no links/provenance", type="story"),
            _f("horizontal", "error", "schema issue", type="story"),
        ]
        grouped = audit_cmd._group_findings_to_chls(findings)
        assert len(grouped) == 1
        g = grouped[0]
        assert g.title == "Audit horizontal/story findings"  # stable, count-free
        assert g.severity == "error"                          # max of group
        assert g.body.count("| story |") == 3                 # one row per finding
        assert "**3 finding(s)**" in g.body
        assert g.technique == "audit-horizontal"

    def test_separate_categories_get_separate_chls(self):
        findings = [
            _f("horizontal", "warn", "a", type="story"),
            _f("horizontal", "warn", "b", type="experiment"),
            _f("cross-cutting", "warn", "c", concern="completeness"),
        ]
        grouped = audit_cmd._group_findings_to_chls(findings)
        assert {g.title for g in grouped} == {
            "Audit horizontal/story findings",
            "Audit horizontal/experiment findings",
            "Audit cross-cutting/completeness findings",
        }

    def test_vertical_title_has_no_stutter(self):
        # B2: vertical findings have no sub-category — the title must not read
        # "vertical/vertical".
        findings = [_f("vertical", "warn", "REQ-001: no ARCH refinement in V-model thread")]
        grouped = audit_cmd._group_findings_to_chls(findings)
        assert len(grouped) == 1
        assert grouped[0].title == "Audit vertical findings"
        assert "vertical/vertical" not in grouped[0].title

    def test_stable_title_across_counts_enables_dedup(self):
        # B2 dedup claim: the same category at different finding counts yields
        # the SAME title, so create_chl_artifacts' title-dedup suppresses the
        # repeat instead of minting a new CHL whenever a group's size changes.
        two = audit_cmd._group_findings_to_chls([
            _f("horizontal", "warn", "a", type="story"),
            _f("horizontal", "warn", "b", type="story"),
        ])
        three = audit_cmd._group_findings_to_chls([
            _f("horizontal", "warn", "a", type="story"),
            _f("horizontal", "warn", "b", type="story"),
            _f("horizontal", "warn", "c", type="story"),
        ])
        assert two[0].title == three[0].title == "Audit horizontal/story findings"
        # The count lives in the body, not the title.
        assert "**2 finding(s)**" in two[0].body
        assert "**3 finding(s)**" in three[0].body

    def test_cross_cutting_scope_uses_concern(self):
        # _artifact_scope falls back to `concern` for cross-cutting findings
        # (they carry no artifact type).
        grouped = audit_cmd._group_findings_to_chls(
            [_f("cross-cutting", "warn", "65 schema issue(s)", concern="consistency")]
        )
        assert "| consistency | warn |" in grouped[0].body
