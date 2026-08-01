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


# ── Accounting-not-policing warn escalation (C12) ────────────────────────────


class TestAccountingWarns:
    """The docs-staleness lens is accounting-not-policing (BP-005/006): its
    warns are printed/reported but never drive the exit-2 code, so a release
    gate running project-audit without continue-on-error is not blocked by
    prose staleness. Structural warns still escalate."""

    def test_docs_staleness_is_registered_accounting(self):
        assert "docs-staleness" in audit_cmd._ACCOUNTING_CONCERNS

    def test_accounting_warn_excluded_from_escalating_count(self):
        findings = [
            _f("cross-cutting", "warn", "README cites superseded DEC-001",
               concern="docs-staleness"),
        ]
        escalating, accounting = audit_cmd._count_warns(findings)
        assert escalating == 0
        assert accounting == 1

    def test_structural_warn_escalates(self):
        findings = [
            _f("cross-cutting", "warn", "2 coverage gap(s)",
               concern="completeness"),
            _f("vertical", "warn", "REQ-001: no ARCH refinement"),
            _f("horizontal", "warn", "no links", type="story"),
        ]
        escalating, accounting = audit_cmd._count_warns(findings)
        assert escalating == 3
        assert accounting == 0

    def test_mixed_findings_split_correctly(self):
        findings = [
            _f("cross-cutting", "warn", "docs stale", concern="docs-staleness"),
            _f("cross-cutting", "warn", "schema issue", concern="consistency"),
            _f("cross-cutting", "error", "hard error", concern="consistency"),
            _f("cross-cutting", "info", "baseline drift", concern="baseline-drift"),
        ]
        escalating, accounting = audit_cmd._count_warns(findings)
        # Only warns are classified; error/info are ignored by _count_warns.
        assert escalating == 1
        assert accounting == 1

    def test_run_docs_staleness_only_exits_zero_but_prints(self, tmp_path, monkeypatch, capsys):
        # Integration: an audit whose ONLY warn is docs-staleness must return
        # exit 0 (CLEAN) yet still print the stale-docs finding.
        root = tmp_path / "project"
        (root / "_specflow" / "specs" / "requirements").mkdir(parents=True)
        # One REQ so discover_artifacts() is non-empty.
        (root / "_specflow" / "specs" / "requirements" / "REQ-001.md").write_text(
            "---\nid: REQ-001\ntitle: T\ntype: requirement\nstatus: approved\n"
            "tags: []\nsuspect: false\nlinks: []\nfingerprint: x\n---\n\n# T\n",
            encoding="utf-8",
        )
        # Control the three analysis axes: no structural findings, one
        # docs-staleness warn.
        monkeypatch.setattr(audit_cmd, "_horizontal_analysis", lambda arts: {})
        monkeypatch.setattr(audit_cmd, "_vertical_analysis", lambda arts: [])
        monkeypatch.setattr(
            audit_cmd, "_cross_cutting_analysis",
            lambda arts, r: {"docs-staleness": [
                {"severity": "warn", "message": "README cites superseded DEC-001"},
            ]},
        )
        # Avoid AUD/CHL artifact side effects in the minimal fixture.
        monkeypatch.setattr(audit_cmd.art_lib, "create_artifact", lambda *a, **k: {"ok": False})
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts", lambda *a, **k: [])

        rc = audit_cmd.run(root, {"quick": False})
        out = capsys.readouterr().out
        assert rc == 0
        # The summary line names the warn as accounting, non-escalating.
        assert "accounting" in out.lower()
        # The finding itself is still written to the report (truthful surfacing).
        reports = sorted((root / ".specflow" / "audits").glob("*/report.md"))
        assert reports, "expected an audit report to be written"
        assert "DEC-001" in reports[-1].read_text(encoding="utf-8")

    def test_run_structural_warn_only_exits_two(self, tmp_path, monkeypatch, capsys):
        # Regression guard: a structural warn (non-accounting) still escalates
        # to exit 2 — the accounting carve-out does not silence real signals.
        root = tmp_path / "project"
        (root / "_specflow" / "specs" / "requirements").mkdir(parents=True)
        (root / "_specflow" / "specs" / "requirements" / "REQ-001.md").write_text(
            "---\nid: REQ-001\ntitle: T\ntype: requirement\nstatus: approved\n"
            "tags: []\nsuspect: false\nlinks: []\nfingerprint: x\n---\n\n# T\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(audit_cmd, "_horizontal_analysis", lambda arts: {})
        monkeypatch.setattr(audit_cmd, "_vertical_analysis", lambda arts: [])
        monkeypatch.setattr(
            audit_cmd, "_cross_cutting_analysis",
            lambda arts, r: {"completeness": [
                {"severity": "warn", "message": "2 coverage gap(s)"},
            ]},
        )
        monkeypatch.setattr(audit_cmd.art_lib, "create_artifact", lambda *a, **k: {"ok": False})
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts", lambda *a, **k: [])

        rc = audit_cmd.run(root, {"quick": False})
        assert rc == 2
