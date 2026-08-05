"""Tests for project-audit CHL grouping (specflow.commands.project_audit).

Focus: the warn/error-findings → CHL batching (B2) that replaced one empty-body
CHL per finding. The grouping is a pure function (``_group_findings_to_chls``)
so it can be exercised directly without running the full audit pipeline.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from specflow.commands import artifact_lint
from specflow.commands import project_audit as audit_cmd
from specflow.lib import ac_quality
from specflow.lib import artifacts as art_lib
from specflow.lib import evidence


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
            lambda arts, r, **kw: {"docs-staleness": [
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
            lambda arts, r, **kw: {"completeness": [
                {"severity": "warn", "message": "2 coverage gap(s)"},
            ]},
        )
        monkeypatch.setattr(audit_cmd.art_lib, "create_artifact", lambda *a, **k: {"ok": False})
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts", lambda *a, **k: [])

        rc = audit_cmd.run(root, {"quick": False})
        assert rc == 2


# ── RC1: foundational-doctrine provenance exemption (de-noise) ───────────────


class TestFoundationalProvenanceExemption:
    """RC1 cry-wolf kill: the horizontal "N/N <type> artifacts have no
    links/provenance" headline must NOT fire for best-practice/decision — they
    are foundational doctrine, upstream-less by design. Genuine orphan-provenance
    detection for every other type stays intact (BP-005/006: de-noise)."""

    @staticmethod
    def _art(aid: str, type_name: str) -> art_lib.Artifact:
        return art_lib.Artifact(
            path=Path(f"{aid}.md"),
            frontmatter={"id": aid, "type": type_name, "status": "approved"},
            body="", links=[],
        )

    def test_best_practice_and_decision_not_flagged(self):
        # 4 unlinked BPs + 4 unlinked DECs: above the warn threshold
        # (orphan_count > len//2 and len > 2), but exempt as foundational.
        arts = [self._art(f"BP-00{i}", "best-practice") for i in range(1, 5)]
        arts += [self._art(f"DEC-00{i}", "decision") for i in range(1, 5)]
        h = audit_cmd._horizontal_analysis(arts)
        for t in ("best-practice", "decision"):
            msgs = [it["message"] for it in h.get(t, [])]
            assert not any("no links/provenance" in m for m in msgs), \
                f"{t} should be exempt from orphan-provenance headline"

    def test_non_exempt_type_still_warns(self):
        # A non-exempt type (requirement) with no provenance still warns — the
        # exemption is scoped to foundational doctrine, not a blanket silence.
        arts = [self._art(f"REQ-00{i}", "requirement") for i in range(1, 5)]
        h = audit_cmd._horizontal_analysis(arts)
        req_items = h.get("requirement", [])
        assert any("no links/provenance" in it["message"] for it in req_items)
        assert any(it["severity"] == "warn" for it in req_items)


# ── --dry-run: identical findings/exit code, zero filesystem side effects ─────


class TestDryRun:
    """``project-audit --dry-run`` skips all four write blocks (snapshot dir,
    AUD artifact, CHL artifact, cache + index) while printing the identical
    Findings/Result lines and returning the identical exit code. After a dry
    run the project tree is byte-for-byte unchanged."""

    @staticmethod
    def _fixture(root: Path) -> None:
        (root / "_specflow" / "specs" / "requirements").mkdir(parents=True)
        # One approved REQ with no ARCH/STORY → vertical warns → exit 2, and a
        # realistic exercise of discover_artifacts + the analysis pipeline.
        (root / "_specflow" / "specs" / "requirements" / "REQ-001.md").write_text(
            "---\nid: REQ-001\ntitle: T\ntype: requirement\nstatus: approved\n"
            "tags: []\nsuspect: false\nlinks: []\nfingerprint: x\n---\n\n# T\n",
            encoding="utf-8",
        )

    @staticmethod
    def _files(root: Path) -> list[str]:
        return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())

    def test_dry_run_creates_no_files(self, tmp_path, capsys):
        root = tmp_path / "project"
        self._fixture(root)
        before = self._files(root)

        rc = audit_cmd.run(root, {"dry_run": True, "quick": True})
        capsys.readouterr()  # drain stdout
        after = self._files(root)

        assert before == after, f"dry-run wrote files: {set(after) - set(before)}"
        # Explicitly: none of the four write targets exist.
        assert not (root / ".specflow").exists()               # snapshot dir + cache
        assert not (root / "_specflow" / "specs" / "audits").exists()       # AUD
        assert not (root / "_specflow" / "specs" / "challenges").exists()   # CHL
        # A dry run still surfaces warns (exit 2), proving findings ran.
        assert rc == 2

    def test_dry_run_exit_code_matches_writing_run(self, tmp_path, capsys):
        # Exit code is a pure function of in-memory findings (_count_warns), so
        # dry and writing runs on the same fixture must agree.
        root = tmp_path / "project"
        self._fixture(root)

        rc_dry = audit_cmd.run(root, {"dry_run": True, "quick": True})
        capsys.readouterr()
        rc_write = audit_cmd.run(root, {"dry_run": False, "quick": True})
        capsys.readouterr()

        assert rc_dry == rc_write
        # Sanity: the writing run DID write its snapshot (the dry run is what
        # suppressed it). AUD/CHL artifact creation is a separate write that
        # silently no-ops on a minimal fixture, so the snapshot dir is the
        # reliable witness that the writing path actually executed.
        assert (root / ".specflow" / "audits").exists()


# ── v1.13 verification arc: accounting demotion of cry-wolf test warns ───────
#
# Shared helpers for the new lenses' tests. Builds in-memory Artifact objects so
# the pure lens helpers (_verification_lens, _ac_coverage_lens, check_coverage,
# _vertical_analysis, _test_results_section) can be exercised without a disk
# fixture.


def _art(
    aid: str,
    type_name: str,
    status: str = "implemented",
    body: str = "",
    links: list[art_lib.Link] | None = None,
    **frontmatter,
) -> art_lib.Artifact:
    fm = {"id": aid, "type": type_name, "status": status}
    fm.update(frontmatter)
    return art_lib.Artifact(
        path=Path(f"{aid}.md"),
        frontmatter=fm,
        body=body,
        links=links or [],
    )


def _write_art(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


class TestVerificationAcCoverageRegistered:
    """Both new concerns must be registered accounting (BP-005/006)."""

    def test_verification_registered(self):
        assert "verification" in audit_cmd._ACCOUNTING_CONCERNS

    def test_ac_coverage_registered(self):
        assert "ac-coverage" in audit_cmd._ACCOUNTING_CONCERNS

    def test_docs_staleness_still_registered(self):
        # Regression guard: the pre-existing carve-out is untouched.
        assert "docs-staleness" in audit_cmd._ACCOUNTING_CONCERNS


# (c) vertical "no test verification" carries concern="verification".


class TestVerticalVerificationConcern:
    def test_no_test_verification_gets_verification_concern(self):
        req = _art("REQ-001", "requirement", status="approved")
        story = _art(
            "STORY-001", "story", status="implemented",
            links=[art_lib.Link(target="REQ-001", role="implements")],
        )
        findings = audit_cmd._vertical_analysis([req, story])
        no_test = [f for f in findings if "no test verification" in f["message"]]
        assert no_test, "expected a no-test-verification finding"
        assert no_test[0].get("concern") == "verification"

    def test_no_arch_vertical_has_no_concern_and_keeps_escalating(self):
        # Real V-model gaps (no ARCH / no STORY) carry NO concern → escalate.
        req = _art("REQ-001", "requirement", status="approved")
        findings = audit_cmd._vertical_analysis([req])
        no_arch = [f for f in findings if "no ARCH" in f["message"]]
        assert no_arch
        assert "concern" not in no_arch[0]
        escalating, _ = audit_cmd._count_warns(no_arch)
        assert escalating == 1


# (b) completeness split: missing-ARCH escalates; test-verification does not.


class TestCompletenessSplit:
    def test_check_coverage_separates_structural_and_verification(self):
        # REQ-A: approved, no ARCH/STORY → STRUCTURAL gaps.
        req_a = _art("REQ-001", "requirement", status="approved")
        # REQ-B: approved, ARCH + implemented STORY, no tests → VERIFICATION gap.
        req_b = _art("REQ-002", "requirement", status="approved")
        arch = _art(
            "ARCH-002", "architecture", status="approved",
            links=[art_lib.Link(target="REQ-002", role="derives_from")],
        )
        story = _art(
            "STORY-002", "story", status="implemented",
            links=[art_lib.Link(target="REQ-002", role="implements")],
        )
        r = artifact_lint.check_coverage([req_a, req_b, arch, story])
        assert r["structural_warning_count"] >= 1
        assert r["verification_warning_count"] >= 1
        # Combined keys preserved for the artifact-lint CLI.
        assert r["warning_count"] == r["structural_warning_count"] + r["verification_warning_count"]

    def test_structural_gap_escalates_test_verification_does_not(self):
        # After routing in project_audit: structural → concern="completeness"
        # (escalating); test-verification → concern="verification" (accounting).
        findings = [
            {"severity": "warn", "concern": "completeness",
             "message": "structural coverage gap (no ARCH)"},
            {"severity": "warn", "concern": "verification",
             "message": "test-verification coverage gap (no UT)"},
        ]
        escalating, accounting = audit_cmd._count_warns(findings)
        assert escalating == 1   # the missing-ARCH gap
        assert accounting == 1   # the test-linkage gap


# (d) verification lens buckets: not-adopted→info; declared-not-run / failed /
# drifted → warn; clean → info.


class TestVerificationLensBuckets:
    def test_not_adopted_is_info_never_warn(self):
        # A project with zero verify_command anywhere → ONE info, never a warn.
        arts = [_art("STORY-001", "story", status="implemented")]  # no verify_command
        findings = audit_cmd._verification_lens(arts)
        assert any(f["severity"] == "info" and "not adopted" in f["message"] for f in findings)
        assert not any(f["severity"] == "warn" for f in findings)

    def test_declared_never_run_warns(self):
        arts = [_art("STORY-001", "story", status="implemented", verify_command="pytest")]
        findings = audit_cmd._verification_lens(arts)
        assert any(f["severity"] == "warn" and "never run" in f["message"] for f in findings)

    def test_failed_run_warns(self):
        arts = [_art(
            "STORY-001", "story", status="implemented", verify_command="pytest",
            verify_run_at="2026-01-01T00:00:00Z", verify_run_exit_code=1, verify_exit_code=0,
        )]
        findings = audit_cmd._verification_lens(arts)
        failed = [f for f in findings if f["severity"] == "warn" and "failed" in f["message"]]
        assert failed and "exit 1" in failed[0]["message"]

    def test_command_drift_warns(self):
        arts = [_art(
            "STORY-001", "story", status="implemented", verify_command="pytest",
            verify_run_at="2026-01-01T00:00:00Z",
            verify_run_exit_code=0, verify_exit_code=0,
            # A stored hash that cannot match the current command.
            verify_run_command_hash="sha256:deadbeefdead",
        )]
        findings = audit_cmd._verification_lens(arts)
        assert any(f["severity"] == "warn" and "drifted" in f["message"] for f in findings)

    def test_clean_emits_info_no_warn(self):
        cmd = "pytest -x"
        current_hash = "sha256:" + hashlib.sha256(cmd.encode()).hexdigest()[:12]
        arts = [_art(
            "STORY-001", "story", status="implemented", verify_command=cmd,
            verify_run_at="2026-01-01T00:00:00Z",
            verify_run_exit_code=0, verify_exit_code=0,
            verify_run_command_hash=current_hash,
        )]
        findings = audit_cmd._verification_lens(arts)
        assert any(f["severity"] == "info" and "green" in f["message"] for f in findings)
        assert not any(f["severity"] == "warn" for f in findings)

    def test_lens_findings_are_accounting(self):
        # Every warn this lens can emit is concern="verification" → accounting.
        arts = [_art("STORY-001", "story", status="implemented", verify_command="pytest")]
        findings = audit_cmd._verification_lens(arts)
        warns = [f for f in findings if f["severity"] == "warn"]
        assert warns
        for w in warns:
            assert w.get("concern") == "verification"
        escalating, accounting = audit_cmd._count_warns(warns)
        assert escalating == 0 and accounting == len(warns)


# (e) ac-coverage lens: one problem class, one severity (A2, CHL-344) —
# zero-tests REQ → warn; count-mismatch → warn. Both degrees are accounting
# (concern in _ACCOUNTING_CONCERNS) and never escalate the exit code.


class TestAcCoverageLens:
    @staticmethod
    def _req_with_acs(aid: str, n: int) -> art_lib.Artifact:
        items = "\n".join(f"- AC {i}" for i in range(1, n + 1))
        return _art(
            aid, "requirement", status="implemented",
            body=f"## Acceptance Criteria\n{items}\n",
        )

    def test_zero_linked_tests_warns(self):
        req = self._req_with_acs("REQ-001", 3)
        findings = audit_cmd._ac_coverage_lens([req])
        warn = [f for f in findings if f["severity"] == "warn" and "no linked tests" in f["message"]]
        assert warn and "3 AC item(s)" in warn[0]["message"]

    def test_count_mismatch_emits_warn(self):
        # A2 (CHL-344): one problem class, one severity — the mismatch degree
        # is WARN like the zero-test degree (it used to be info, which let the
        # debt regenerate after the warn layer was triaged). Degree information
        # survives in the message text ("(N green) — review coverage").
        req = self._req_with_acs("REQ-001", 3)  # 3 ACs
        qt = _art(
            "QT-001", "qualification-test", status="verified",
            links=[art_lib.Link(target="REQ-001", role="verified_by")],
            verify_run_exit_code=0,  # green run → the degree text carries it
        )
        findings = audit_cmd._ac_coverage_lens([req, qt])
        warn = [f for f in findings if f["severity"] == "warn" and "review" in f["message"]]
        assert warn
        assert "1 linked test(s) < 3 AC item(s)" in warn[0]["message"]
        assert "(1 green)" in warn[0]["message"]
        assert not any(f["severity"] == "info" for f in findings)

    def test_ac_coverage_warns_are_accounting(self):
        # BOTH degrees (zero-test and mismatch) land in the accounting bucket:
        # concern="ac-coverage" is registered in _ACCOUNTING_CONCERNS, so
        # neither degree can escalate.
        req_a = self._req_with_acs("REQ-001", 2)  # zero linked tests → warn
        req_b = self._req_with_acs("REQ-002", 3)  # mismatch → warn
        qt = _art(
            "QT-001", "qualification-test", status="verified",
            links=[art_lib.Link(target="REQ-002", role="verified_by")],
        )
        findings = audit_cmd._ac_coverage_lens([req_a, req_b, qt])
        warns = [f for f in findings if f["severity"] == "warn"]
        assert len(warns) == 2  # one per degree, both warn
        for w in warns:
            assert w.get("concern") == "ac-coverage"
        escalating, accounting = audit_cmd._count_warns(warns)
        assert escalating == 0 and accounting == len(warns)


# (a) EXIT-CODE PARITY: accounting warns never drive exit-2.


class TestExitCodeParity:
    """A fixture project full of verification + AC-coverage gaps (but NO
    structural gaps) exits CLEAN: every warn it produces is accounting. The
    exit code is identical to the same project with those warns stripped —
    proving the lenses add signal without changing the exit gate. Disabling the
    carve-out makes the same warns escalate (the 'before' state), confirming
    the carve-out is the sole mechanism."""

    @staticmethod
    def _gap_fixture(root: Path) -> None:
        # REQ (implemented) + ARCH + DDD + implemented STORY that declares a
        # verify_command but was never run. Triggers, all accounting:
        #   - vertical "STORY no test verification"        (concern=verification)
        #   - completeness test-verification split          (concern=verification)
        #   - verification lens "declared, never run"       (concern=verification)
        #   - ac-coverage "ACs but no linked tests"         (concern=ac-coverage)
        # No structural gaps: ARCH, DDD, STORY all present.
        _write_art(root, "_specflow/specs/requirements/REQ-001.md",
                   "---\nid: REQ-001\ntitle: T\ntype: requirement\nstatus: implemented\n"
                   "non_functional_category: functional\n"
                   "tags: []\nsuspect: false\nlinks: []\nfingerprint: x\n---\n\n# T\n\n"
                   "## Acceptance Criteria\n- AC one\n- AC two\n- AC three\n")
        _write_art(root, "_specflow/specs/architecture/ARCH-001.md",
                   "---\nid: ARCH-001\ntitle: A\ntype: architecture\nstatus: approved\n"
                   "tags: []\nsuspect: false\n"
                   "links:\n  - {target: REQ-001, role: derives_from}\n"
                   "fingerprint: x\n---\n\n# A\n\n## Component\narch component detail.\n")
        _write_art(root, "_specflow/specs/detailed-design/DDD-001.md",
                   "---\nid: DDD-001\ntitle: D\ntype: detailed-design\nstatus: approved\n"
                   "tags: []\nsuspect: false\n"
                   "links:\n  - {target: ARCH-001, role: derives_from}\n"
                   "fingerprint: x\n---\n\n# D\n\n## Function\nddd function detail.\n")
        _write_art(root, "_specflow/work/stories/STORY-001.md",
                   "---\nid: STORY-001\ntitle: S\ntype: story\nstatus: implemented\n"
                   "verify_command: \"pytest -x\"\n"
                   "tags: []\nsuspect: false\n"
                   "links:\n  - {target: REQ-001, role: implements}\n"
                   "fingerprint: x\n---\n\n# S\n\n## Acceptance Criteria\n- it works\n")

    @staticmethod
    def _assemble_findings(arts, root):
        h = audit_cmd._horizontal_analysis(arts)
        v = audit_cmd._vertical_analysis(arts)
        cc = audit_cmd._cross_cutting_analysis(arts, root)
        raw = []
        for tname, items in h.items():
            for it in items:
                it["axis"] = "horizontal"; it["type"] = tname; raw.append(it)
        for it in v:
            it["axis"] = "vertical"; raw.append(it)
        for con, items in cc.items():
            for it in items:
                it["axis"] = "cross-cutting"; it["concern"] = con; raw.append(it)
        return raw

    def test_gap_fixture_exits_clean_accounting_warns_present(self, tmp_path, monkeypatch, capsys):
        root = tmp_path / "project"
        self._gap_fixture(root)
        # Silence the schema lens (no schema dir in the fixture) and AUD/CHL
        # side effects — the new lenses themselves must run real.
        monkeypatch.setattr(artifact_lint, "check_schema",
                            lambda arts, sd: {"blocking_count": 0, "warning_count": 0})
        monkeypatch.setattr(audit_cmd.art_lib, "create_artifact", lambda *a, **k: {"ok": False})
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts", lambda *a, **k: [])

        rc = audit_cmd.run(root, {"quick": False})
        out = capsys.readouterr().out
        assert rc == 0, f"expected CLEAN (exit 0), got {rc}\n{out}"
        assert "accounting" in out.lower()  # the summary surfaces the carve-out

    def test_parity_accounting_warns_do_not_change_exit_code(self, tmp_path, monkeypatch):
        root = tmp_path / "project"
        self._gap_fixture(root)
        # Silence the schema lens (no schema dir in the fixture) so the only
        # warns are the accounting ones the new lenses emit.
        monkeypatch.setattr(artifact_lint, "check_schema",
                            lambda arts, sd: {"blocking_count": 0, "warning_count": 0})
        arts = art_lib.discover_artifacts(root)
        findings = self._assemble_findings(arts, root)

        escalating, accounting = audit_cmd._count_warns(findings)
        assert escalating == 0          # no structural gaps on this fixture
        assert accounting > 0           # the verification/ac-coverage lenses fired

        # Parity: with accounting warns STRIPPED, the escalating count is
        # identical (the lenses add signal, not exit pressure).
        non_accounting = [
            f for f in findings
            if not (f.get("severity") == "warn"
                    and f.get("concern") in audit_cmd._ACCOUNTING_CONCERNS)
        ]
        esc_stripped, _ = audit_cmd._count_warns(non_accounting)
        assert esc_stripped == escalating

        # The carve-out is the SOLE mechanism: disable it and the same warns
        # escalate (this is the "before the lenses existed" exit pressure).
        monkeypatch.setattr(audit_cmd, "_ACCOUNTING_CONCERNS", frozenset())
        esc_disabled, _ = audit_cmd._count_warns(findings)
        assert esc_disabled == accounting + escalating


# (f) evidence _test_results_section annotates verify_run_exit_code.


class TestEvidenceVerifyRunAnnotation:
    def test_annotation_present_when_verify_run_exit_set(self):
        arts = [
            _art("QT-001", "qualification-test", status="verified", verify_run_exit_code=0),
            _art("QT-002", "qualification-test", status="verified", verify_run_exit_code=1),
        ]
        text = "\n".join(evidence._test_results_section(arts))
        assert "verify_run exit=0" in text           # green run, no 'see audit'
        assert "verify_run exit=1 — see audit" in text  # failed run flagged

    def test_annotation_absent_when_field_missing(self):
        arts = [_art("QT-001", "qualification-test", status="verified")]
        text = "\n".join(evidence._test_results_section(arts))
        assert "verify_run" not in text
        assert "| verified |" in text  # bare status, no annotation


# ── Audit report honesty: chain coverage + trend deltas (CHL-341, CHL-344#2) ─
#
# The audit report header gains two informational lines that must be honest:
#   - **Chain coverage**: N% (c/t approved STORYs fully covered by UT+IT+QT)
#   - **Trend vs AUD-0XX**: errors/warns/info/chain-coverage deltas vs the
#     prior audit's stamped summary fields.
# Both are pure rendering over the loaded artifact list: they never affect the
# exit code, render on cache hits and --dry-run alike, and degrade to honest
# fallbacks (n/a / "first audit") instead of inventing numbers.


def _story_fixture(root: Path, n_covered: int, n_uncovered: int = 0) -> None:
    """REQ-001 + ARCH-001 + N fully-verified STORYs + M unverified STORYs."""
    _write_art(root, "_specflow/specs/requirements/REQ-001.md",
               "---\nid: REQ-001\ntitle: T\ntype: requirement\nstatus: approved\n"
               "tags: []\nsuspect: false\nlinks: []\nfingerprint: x\n---\n\n# T\n")
    _write_art(root, "_specflow/specs/architecture/ARCH-001.md",
               "---\nid: ARCH-001\ntitle: A\ntype: architecture\nstatus: approved\n"
               "tags: []\nsuspect: false\n"
               "links:\n  - {target: REQ-001, role: derives_from}\n"
               "fingerprint: x\n---\n\n# A\n")
    n = 0
    for _ in range(n_covered):
        n += 1
        sid = f"STORY-{n:03d}"
        _write_art(root, f"_specflow/work/stories/{sid}.md",
                   f"---\nid: {sid}\ntitle: S\ntype: story\nstatus: implemented\n"
                   "tags: []\nsuspect: false\n"
                   f"links:\n  - {{target: REQ-001, role: implements}}\n"
                   "fingerprint: x\n---\n\n# S\n")
        for prefix, ttype, dirn in (
            ("UT", "unit-test", "specs/unit-tests"),
            ("IT", "integration-test", "specs/integration-tests"),
            ("QT", "qualification-test", "specs/qualification-tests"),
        ):
            tid = f"{prefix}-{n:03d}"
            _write_art(root, f"_specflow/{dirn}/{tid}.md",
                       f"---\nid: {tid}\ntitle: V\ntype: {ttype}\nstatus: verified\n"
                       "tags: []\nsuspect: false\n"
                       f"links:\n  - {{target: {sid}, role: verified_by}}\n"
                       "fingerprint: x\n---\n\n# V\n")
    for _ in range(n_uncovered):
        n += 1
        sid = f"STORY-{n:03d}"
        _write_art(root, f"_specflow/work/stories/{sid}.md",
                   f"---\nid: {sid}\ntitle: S\ntype: story\nstatus: implemented\n"
                   "tags: []\nsuspect: false\n"
                   f"links:\n  - {{target: REQ-001, role: implements}}\n"
                   "fingerprint: x\n---\n\n# S\n")


def _aud_file(root: Path, aid: str, extra_fm: str = "") -> None:
    """A prior AUD artifact file; extra_fm carries the stamped summary fields."""
    _write_art(root, f"_specflow/specs/audits/{aid}.md",
               f"---\nid: {aid}\ntitle: Prior Audit\ntype: audit\nstatus: open\n"
               f"created: 2026-08-01\ntags: []\nsuspect: false\nlinks: []\n"
               f"fingerprint: x\n{extra_fm}---\n\n# Prior Audit\n")


def _run_quiet_audit(root: Path, monkeypatch, cross_cutting=None) -> int:
    """Run the audit with the three analysis axes silenced to deterministic
    values so only the header metrics vary; AUD/CHL side effects suppressed."""
    monkeypatch.setattr(audit_cmd, "_horizontal_analysis", lambda arts: {})
    monkeypatch.setattr(audit_cmd, "_vertical_analysis", lambda arts: [])
    monkeypatch.setattr(audit_cmd, "_cross_cutting_analysis",
                        lambda arts, r, **kw: cross_cutting or {})
    monkeypatch.setattr(audit_cmd.art_lib, "create_artifact", lambda *a, **k: {"ok": False})
    monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts", lambda *a, **k: [])
    return audit_cmd.run(root, {"quick": False})


def _latest_report(root: Path) -> str:
    reports = sorted((root / ".specflow" / "audits").glob("*/report.md"))
    assert reports, "expected an audit report to be written"
    return reports[-1].read_text(encoding="utf-8")


class TestChainCoverageHeader:
    def test_chain_coverage_line_renders_mixed_numbers(self, tmp_path, monkeypatch):
        # 1 fully-verified STORY + 1 unverified STORY → 50% (1/2).
        root = tmp_path / "project"
        _story_fixture(root, n_covered=1, n_uncovered=1)
        rc = _run_quiet_audit(root, monkeypatch)
        report = _latest_report(root)
        assert "- **Chain coverage**: 50% (1/2 approved STORYs fully covered by UT+IT+QT)" in report
        assert rc == 0  # informational metric — adds no exit pressure

    def test_chain_coverage_full(self, tmp_path, monkeypatch):
        root = tmp_path / "project"
        _story_fixture(root, n_covered=3)
        _run_quiet_audit(root, monkeypatch)
        assert "- **Chain coverage**: 100% (3/3 approved STORYs fully covered by UT+IT+QT)" \
            in _latest_report(root)

    def test_chain_coverage_na_without_approved_stories(self, tmp_path, monkeypatch):
        # No STORYs at all → honest n/a, never a fabricated 0% or 100%.
        root = tmp_path / "project"
        (root / "_specflow" / "specs" / "requirements").mkdir(parents=True)
        (root / "_specflow" / "specs" / "requirements" / "REQ-001.md").write_text(
            "---\nid: REQ-001\ntitle: T\ntype: requirement\nstatus: approved\n"
            "tags: []\nsuspect: false\nlinks: []\nfingerprint: x\n---\n\n# T\n",
            encoding="utf-8",
        )
        _run_quiet_audit(root, monkeypatch)
        assert "- **Chain coverage**: n/a (no approved STORYs)" in _latest_report(root)

    def test_chain_coverage_matches_check_coverage_tally(self):
        # The header metric reuses artifact_lint.check_coverage's own walk —
        # covered/total agree with the lint's verification warnings 1:1.
        req = _art("REQ-001", "requirement", status="approved")
        covered = _art("STORY-001", "story", status="implemented",
                       links=[art_lib.Link(target="REQ-001", role="implements")])
        uncovered = _art("STORY-002", "story", status="implemented",
                         links=[art_lib.Link(target="REQ-001", role="implements")])
        tests = [
            _art("UT-001", "unit-test", status="verified",
                 links=[art_lib.Link(target="STORY-001", role="verified_by")]),
            _art("IT-001", "integration-test", status="verified",
                 links=[art_lib.Link(target="STORY-001", role="verified_by")]),
            _art("QT-001", "qualification-test", status="verified",
                 links=[art_lib.Link(target="STORY-001", role="verified_by")]),
        ]
        r = artifact_lint.check_coverage([req, covered, uncovered] + tests)
        assert (r["approved_story_covered"], r["approved_story_total"]) == (1, 2)
        assert audit_cmd._chain_coverage_stats([req, covered, uncovered] + tests) == (1, 2)


class TestTrendDeltas:
    def test_trend_renders_deltas_against_stamped_prior(self, tmp_path, monkeypatch):
        root = tmp_path / "project"
        _story_fixture(root, n_covered=1)
        _aud_file(root, "AUD-001",
                  extra_fm="summary_errors: 0\nsummary_warns: 29\nsummary_info: 19\n"
                           "chain_coverage_pct: 61\n")
        # Current run: 0 errors, 0 warns, 12 infos; chain coverage 100% (1/1).
        infos = [{"severity": "info", "message": f"baseline info {i}"} for i in range(12)]
        rc = _run_quiet_audit(root, monkeypatch, cross_cutting={"baseline-drift": infos})
        report = _latest_report(root)
        assert ("- **Trend vs AUD-001**: errors 0→0 (Δ0), warns 29→0 (Δ−29), "
                "info 19→12 (Δ−7), chain coverage 61%→100% (Δ+39 pp)") in report
        assert rc == 0

    def test_trend_renders_warn_split_when_both_sides_carry_it(self, tmp_path, monkeypatch):
        # A1: both the prior stamp and the current run carry the
        # escalating/accounting split → the warns bullet is extended.
        root = tmp_path / "project"
        _story_fixture(root, n_covered=1)
        _aud_file(root, "AUD-001",
                  extra_fm="summary_errors: 0\nsummary_warns: 25\nsummary_info: 10\n"
                           "chain_coverage_pct: 100\n"
                           "summary_warns_escalating: 10\n"
                           "summary_warns_accounting: 15\n")
        # Current run: 1 accounting warn (ac-coverage), 0 structural warns.
        warns = [{"severity": "warn", "message": "ac coverage gap"}]
        rc = _run_quiet_audit(root, monkeypatch, cross_cutting={"ac-coverage": warns})
        report = _latest_report(root)
        assert ("- **Trend vs AUD-001**: errors 0→0 (Δ0), warns 25→1 (Δ−24) "
                "(escalating 10→0, accounting 15→1), info 10→0 (Δ−10), "
                "chain coverage 100%→100% (Δ0 pp)") in report
        assert rc == 0  # accounting warns never drive the exit code

    def test_trend_legacy_totals_when_prior_lacks_split(self, tmp_path, monkeypatch):
        # A pre-A1 prior (4-field stamp only, e.g. AUD-073..080): the trend
        # line stays on legacy totals — no split suffix, no crash, no
        # invented split numbers, and NOT the "predates summary stamping"
        # fallback (the prior is still a full trend baseline).
        root = tmp_path / "project"
        _story_fixture(root, n_covered=1)
        _aud_file(root, "AUD-001",
                  extra_fm="summary_errors: 0\nsummary_warns: 25\nsummary_info: 10\n"
                           "chain_coverage_pct: 100\n")
        warns = [{"severity": "warn", "message": "ac coverage gap"}]
        _run_quiet_audit(root, monkeypatch, cross_cutting={"ac-coverage": warns})
        trend = next(l for l in _latest_report(root).splitlines()
                     if l.startswith("- **Trend vs AUD-001**:"))
        assert trend == ("- **Trend vs AUD-001**: errors 0→0 (Δ0), "
                         "warns 25→1 (Δ−24), info 10→0 (Δ−10), "
                         "chain coverage 100%→100% (Δ0 pp)")

    def test_trend_fallback_when_prior_predates_stamping(self, tmp_path, monkeypatch):
        root = tmp_path / "project"
        _story_fixture(root, n_covered=1)
        _aud_file(root, "AUD-001")  # no summary_* fields
        _run_quiet_audit(root, monkeypatch)
        assert ("- **Trend vs AUD-001**: n/a (prior audit predates summary stamping)"
                in _latest_report(root))

    def test_trend_first_audit_wording(self, tmp_path, monkeypatch):
        root = tmp_path / "project"
        _story_fixture(root, n_covered=1)
        _run_quiet_audit(root, monkeypatch)
        assert "- **Trend**: first audit — no prior baseline" in _latest_report(root)

    def test_dry_run_renders_nothing_to_disk_but_trend_is_readonly(self, tmp_path, monkeypatch, capsys):
        # --dry-run writes nothing (no report, no AUD) yet the trend/coverage
        # lines are pure rendering from already-loaded data — the same inputs a
        # writing run sees. Exit parity with the writing run is the invariant.
        root = tmp_path / "project"
        _story_fixture(root, n_covered=1)
        _aud_file(root, "AUD-001",
                  extra_fm="summary_errors: 0\nsummary_warns: 1\nsummary_info: 2\n"
                           "chain_coverage_pct: 50\n")
        before = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
        rc_dry = audit_cmd.run(root, {"dry_run": True, "quick": True})
        capsys.readouterr()
        after = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
        assert before == after  # no report, no AUD, no cache writes
        rc_write = audit_cmd.run(root, {"dry_run": False, "quick": True})
        capsys.readouterr()
        assert rc_dry == rc_write


class TestPriorAuditSelection:
    def test_created_date_is_primary_order(self):
        # The newest-created audit is the prior baseline, regardless of suffix.
        a1 = _art("AUD-001", "audit", status="open", created="2026-08-04")
        a2 = _art("AUD-002", "audit", status="open", created="2026-01-01")
        assert audit_cmd._select_prior_audit([a1, a2]).id == "AUD-001"

    def test_same_day_numeric_suffix_breaks_tie(self):
        # Same-day audits are created in suffix order → higher suffix wins.
        a1 = _art("AUD-072", "audit", status="open", created="2026-08-04")
        a2 = _art("AUD-073", "audit", status="open", created="2026-08-04")
        assert audit_cmd._select_prior_audit([a1, a2]).id == "AUD-073"

    def test_old_hash_draft_does_not_shadow_newer_numbered(self):
        # Live regression: old draft-ID audits (AUD-PROJECTA-* era) must not
        # outrank newer numbered ones and pin the trend line to n/a forever.
        d1 = _art("AUD-PROJECTA-f7ce", "audit", status="open", created="2026-04-22")
        a1 = _art("AUD-073", "audit", status="open", created="2026-08-05")
        assert audit_cmd._select_prior_audit([d1, a1]).id == "AUD-073"

    def test_same_day_hash_draft_sorts_after_numeric(self):
        # A draft created the same day as the last numbered audit is newer.
        a1 = _art("AUD-009", "audit", status="open", created="2026-07-15")
        d1 = _art("AUD-audit-draft-a7b9", "audit", status="open", created="2026-07-01")
        d2 = _art("AUD-audit-draft-b8c0", "audit", status="open", created="2026-07-15")
        assert audit_cmd._select_prior_audit([a1, d1, d2]).id == "AUD-audit-draft-b8c0"

    def test_no_aud_returns_none(self):
        assert audit_cmd._select_prior_audit([_art("REQ-001", "requirement")]) is None

    def test_unparseable_stamp_fields_treated_as_missing(self):
        a = _art("AUD-001", "audit", status="open", summary_errors="garbage",
                 summary_warns=1, summary_info=1, chain_coverage_pct=1)
        assert audit_cmd._prior_audit_summary(a) is None
        # → the trend line degrades to the "predates stamping" fallback.
        line = audit_cmd._trend_bullet(0, 0, 0, 100, a)
        assert line == "- **Trend vs AUD-001**: n/a (prior audit predates summary stamping)"

    def test_four_field_stamp_still_resolves_after_a1(self):
        # Regression (A1, CHL-344): an AUD-073..080-shaped prior with ONLY
        # the four baseline stamp fields must still resolve as a full trend
        # baseline — the split fields are EXTRA, not a new membership
        # requirement, so _prior_audit_summary behavior is unchanged.
        a = _art("AUD-073", "audit", status="open",
                 summary_errors=0, summary_warns=29, summary_info=19,
                 chain_coverage_pct=61)
        assert audit_cmd._prior_audit_summary(a) == {
            "summary_errors": 0, "summary_warns": 29,
            "summary_info": 19, "chain_coverage_pct": 61,
        }
        assert audit_cmd._prior_warn_split(a) is None
        # …and the trend renders legacy totals even when the CURRENT run
        # carries a split — never the "predates" fallback, never a suffix.
        line = audit_cmd._trend_bullet(0, 0, 0, 100, a, cur_warn_split=(0, 0))
        assert line.startswith("- **Trend vs AUD-073**: errors 0→0 (Δ0), "
                               "warns 29→0 (Δ−29)")
        assert "predates" not in line
        assert "escalating" not in line

    def test_prior_warn_split_needs_both_fields(self):
        # The split is consumed opportunistically: BOTH extra fields must be
        # present and parseable, else legacy total rendering (no invented
        # numbers).
        full = _art("AUD-001", "audit", status="open",
                    summary_warns_escalating=3, summary_warns_accounting=5)
        assert audit_cmd._prior_warn_split(full) == (3, 5)
        half = _art("AUD-002", "audit", status="open", summary_warns_escalating=3)
        assert audit_cmd._prior_warn_split(half) is None
        bad = _art("AUD-003", "audit", status="open",
                   summary_warns_escalating="garbage", summary_warns_accounting=5)
        assert audit_cmd._prior_warn_split(bad) is None


class TestAudSummaryStamping:
    def test_new_aud_stamps_machine_readable_summary(self, tmp_path, monkeypatch, capsys):
        import specflow as _pkg

        root = tmp_path / "project"
        _story_fixture(root, n_covered=1, n_uncovered=3)  # chain coverage 25%
        # The real create_artifact needs the audit schema on disk.
        schema_dir = root / ".specflow" / "schema"
        schema_dir.mkdir(parents=True)
        tmpl = Path(_pkg.__file__).parent / "templates" / "schemas" / "audit.yaml"
        (schema_dir / "audit.yaml").write_text(tmpl.read_text(encoding="utf-8"), encoding="utf-8")

        infos = [{"severity": "info", "message": f"info {i}"} for i in range(3)]
        monkeypatch.setattr(audit_cmd, "_horizontal_analysis", lambda arts: {})
        monkeypatch.setattr(audit_cmd, "_vertical_analysis", lambda arts: [])
        monkeypatch.setattr(audit_cmd, "_cross_cutting_analysis",
                            lambda arts, r, **kw: {"baseline-drift": infos})
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts", lambda *a, **k: [])

        rc = audit_cmd.run(root, {"quick": False})
        capsys.readouterr()
        assert rc == 0

        aud_files = sorted((root / "_specflow" / "specs" / "audits").glob("AUD-*.md"))
        assert aud_files, "expected an AUD artifact to be created"
        text = aud_files[-1].read_text(encoding="utf-8")
        fm = yaml.safe_load(text[3:text.find("---", 3)])
        assert fm["summary_errors"] == 0
        assert fm["summary_warns"] == 0
        assert fm["summary_info"] == 3
        assert fm["chain_coverage_pct"] == 25
        # A1: the warn split is ALWAYS stamped alongside the baseline stamp —
        # a clean run stamps the trivial 0/0 split.
        assert fm["summary_warns_escalating"] == 0
        assert fm["summary_warns_accounting"] == 0

    def test_new_aud_stamps_warn_split_fields(self, tmp_path, monkeypatch, capsys):
        # A1 (CHL-344): warns split by _ACCOUNTING_CONCERNS membership —
        # a vertical (structural) warn escalates, an ac-coverage warn is
        # accounting. Totals stay consistent: escalating + accounting == warns.
        import specflow as _pkg

        root = tmp_path / "project"
        _story_fixture(root, n_covered=1)
        schema_dir = root / ".specflow" / "schema"
        schema_dir.mkdir(parents=True)
        tmpl = Path(_pkg.__file__).parent / "templates" / "schemas" / "audit.yaml"
        (schema_dir / "audit.yaml").write_text(tmpl.read_text(encoding="utf-8"), encoding="utf-8")

        monkeypatch.setattr(audit_cmd, "_horizontal_analysis", lambda arts: {})
        monkeypatch.setattr(audit_cmd, "_vertical_analysis",
                            lambda arts: [{"severity": "warn", "message": "structural gap"}])
        monkeypatch.setattr(audit_cmd, "_cross_cutting_analysis",
                            lambda arts, r, **kw: {
                                "ac-coverage": [{"severity": "warn", "message": "ac gap"}]})
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts", lambda *a, **k: [])

        rc = audit_cmd.run(root, {"quick": False})
        capsys.readouterr()
        assert rc == 2  # the structural warn escalates; accounting does not add

        aud_files = sorted((root / "_specflow" / "specs" / "audits").glob("AUD-*.md"))
        assert aud_files, "expected an AUD artifact to be created"
        text = aud_files[-1].read_text(encoding="utf-8")
        fm = yaml.safe_load(text[3:text.find("---", 3)])
        assert fm["summary_warns"] == 2
        assert fm["summary_warns_escalating"] == 1
        assert fm["summary_warns_accounting"] == 1

    def test_ac_coverage_warns_only_exit_clean_stamped_accounting(self, tmp_path, monkeypatch, capsys):
        # A2 (CHL-344): after severity unification the ac-coverage lens emits
        # warns on BOTH degrees. With ONLY ac-coverage warns present the run
        # must still exit CLEAN (0) — accounting warns print + stamp but never
        # drive exit-2 — and the stamp split must carry the whole movement in
        # the accounting bucket (escalating stays 0). This is the unit-level
        # guarantee that the live "escalating 0→0, accounting 0→N" trend line
        # is honest.
        import specflow as _pkg

        root = tmp_path / "project"
        _story_fixture(root, n_covered=1)
        schema_dir = root / ".specflow" / "schema"
        schema_dir.mkdir(parents=True)
        tmpl = Path(_pkg.__file__).parent / "templates" / "schemas" / "audit.yaml"
        (schema_dir / "audit.yaml").write_text(tmpl.read_text(encoding="utf-8"), encoding="utf-8")

        monkeypatch.setattr(audit_cmd, "_horizontal_analysis", lambda arts: {})
        monkeypatch.setattr(audit_cmd, "_vertical_analysis", lambda arts: [])
        monkeypatch.setattr(audit_cmd, "_cross_cutting_analysis",
                            lambda arts, r, **kw: {
                                "ac-coverage": [
                                    {"severity": "warn",
                                     "message": "REQ-001: 3 AC item(s) but no linked tests"},
                                    {"severity": "warn",
                                     "message": "REQ-002: 1 linked test(s) < 3 AC item(s) (0 green) — review coverage"},
                                ]})
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts", lambda *a, **k: [])

        rc = audit_cmd.run(root, {"quick": False})
        out = capsys.readouterr().out
        assert rc == 0, f"ac-coverage warns alone must exit CLEAN, got {rc}\n{out}"

        aud_files = sorted((root / "_specflow" / "specs" / "audits").glob("AUD-*.md"))
        assert aud_files, "expected an AUD artifact to be created"
        text = aud_files[-1].read_text(encoding="utf-8")
        fm = yaml.safe_load(text[3:text.find("---", 3)])
        assert fm["summary_warns"] == 2
        assert fm["summary_warns_escalating"] == 0
        assert fm["summary_warns_accounting"] == 2
        assert fm["summary_info"] == 0

    def test_stamped_fields_pass_schema_lint(self, tmp_path):
        # The audit schema enumerates the stamp fields as optional, and the
        # global known-meta whitelist covers pre-existing on-disk schemas — so
        # a stamped AUD never draws an "Unknown field" finding (incl. the A1
        # warn-split fields).
        from specflow.lib import lint as lint_lib

        stamped = _art("AUD-001", "audit", status="open",
                       summary_errors=0, summary_warns=2, summary_info=5,
                       chain_coverage_pct=61,
                       summary_warns_escalating=1, summary_warns_accounting=1)
        schema = {"required_fields": ["id", "title", "type", "status", "created"],
                  "optional_fields": [], "allowed_status": {"open": [], "closed": ["open"]}}
        issues = lint_lib.validate_artifact_schema(stamped, schema)
        assert not any("Unknown field" in i["message"] for i in issues)


# ── Baseline naming policy: drift selection + --baseline anchor ──────────────
# CHL-NONSEMVE-c16b: (b) drift selection prefers semver-parseable release
# baselines and falls back to the raw tail only when fewer than two names
# parse; the --baseline flag is wired as an explicit drift anchor
# (<baseline> → newest release), with warn + auto-fallback on an unknown
# name (accounting-not-policing). Create-time name enforcement lives in
# tests/test_baselines.py.


def _snap_entry(status: str = "approved", fp: str = "sha256:aaa") -> dict:
    return {"status": status, "fingerprint": fp, "title": "T", "type": "requirement"}


def _baseline_file(root: Path, name: str, arts: dict) -> None:
    d = root / ".specflow" / "baselines"
    d.mkdir(parents=True, exist_ok=True)
    data = {
        "name": name,
        "created_at": "2026-08-05T00:00:00Z",
        "git_ref": "",
        "artifacts": arts,
    }
    (d / f"{name}.yaml").write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8"
    )


class TestDriftSelectionAndBaselineAnchor:
    @staticmethod
    def _req(root: Path) -> None:
        # One real artifact so discover_artifacts is non-empty; carries an NFR
        # category so the nfr-coverage lens stays at info.
        _write_art(root, "_specflow/specs/requirements/REQ-001.md",
                   "---\nid: REQ-001\ntitle: T\ntype: requirement\nstatus: approved\n"
                   "non_functional_category: performance\n"
                   "tags: []\nsuspect: false\nlinks: []\nfingerprint: x\n---\n\n# T\n")

    @staticmethod
    def _quiet(monkeypatch) -> None:
        """Silence every lens except the real cross-cutting baseline drift."""
        monkeypatch.setattr(audit_cmd, "_horizontal_analysis", lambda arts: {})
        monkeypatch.setattr(audit_cmd, "_vertical_analysis", lambda arts: [])
        monkeypatch.setattr(audit_cmd.art_lib, "create_artifact", lambda *a, **k: {"ok": False})
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts", lambda *a, **k: [])
        monkeypatch.setattr(audit_cmd.standards_lib, "check_compliance", lambda r: {"ok": False})
        monkeypatch.setattr(audit_cmd.artifact_lint, "check_schema",
                            lambda arts, schema_dir: {"blocking_count": 0, "warning_count": 0})
        monkeypatch.setattr(audit_cmd.artifact_lint, "check_coverage",
                            lambda arts: {"structural_warning_count": 0,
                                          "verification_warning_count": 0,
                                          "approved_story_covered": 0,
                                          "approved_story_total": 0})

    def test_mixed_names_drift_compares_releases_not_freeform(self, tmp_path, monkeypatch, capsys):
        # The CHL scenario end to end: with [v1.0.0, v1.1.0, snapshot] on disk
        # the auto pair must be v1.0.0 → v1.1.0 (select_release_pair), NOT the
        # raw tail v1.1.0 → snapshot. The REQ-002 removal finding exists only
        # in the release pair, so its presence proves which pair was diffed.
        root = tmp_path / "project"
        self._req(root)
        _baseline_file(root, "v1.0.0", {"REQ-001": _snap_entry(), "REQ-002": _snap_entry(status="draft")})
        _baseline_file(root, "v1.1.0", {"REQ-001": _snap_entry()})
        _baseline_file(root, "snapshot", {"REQ-001": _snap_entry()})
        self._quiet(monkeypatch)

        rc = audit_cmd.run(root, {"quick": False, "dry_run": True})
        capsys.readouterr()
        assert rc == 2  # the removed-artifact drift warn escalates (dry run too)
        rc2 = audit_cmd.run(root, {"quick": False})
        capsys.readouterr()
        assert rc2 == rc  # exit-code parity between dry and writing runs
        report = _latest_report(root)
        assert "REQ-002: removed since last baseline" in report
        assert "**Baseline drift: compared v1.0.0 → v1.1.0**" in report

    def test_pure_freeform_falls_back_to_raw_tail(self, tmp_path, monkeypatch, capsys):
        # Fewer than two semver names → raw-tail behavior is preserved exactly.
        root = tmp_path / "project"
        self._req(root)
        _baseline_file(root, "alpha", {"REQ-001": _snap_entry()})
        _baseline_file(root, "beta", {})  # REQ-001 removed between the two
        self._quiet(monkeypatch)

        rc = audit_cmd.run(root, {"quick": False})
        capsys.readouterr()
        assert rc == 2
        report = _latest_report(root)
        assert "REQ-001: removed since last baseline" in report
        assert "**Baseline drift: compared alpha → beta**" in report

    def test_known_baseline_anchors_drift(self, tmp_path, monkeypatch, capsys):
        # v1.0.0 → v2.0.0 spans a removal the auto pair (v1.1.0 → v2.0.0) does
        # not see: anchored run escalates, unanchored run is clean.
        root = tmp_path / "project"
        self._req(root)
        _baseline_file(root, "v1.0.0", {"REQ-001": _snap_entry(), "REQ-002": _snap_entry(status="draft")})
        _baseline_file(root, "v1.1.0", {"REQ-001": _snap_entry()})
        _baseline_file(root, "v2.0.0", {"REQ-001": _snap_entry()})
        self._quiet(monkeypatch)

        rc_auto = audit_cmd.run(root, {"quick": False})
        capsys.readouterr()
        assert rc_auto == 0  # auto pair sees no drift

        rc_anchored = audit_cmd.run(root, {"quick": False, "baseline": "v1.0.0"})
        capsys.readouterr()
        assert rc_anchored == 2  # anchor widens the window to the removal
        reports = sorted((root / ".specflow" / "audits").glob("*/report.md"))
        anchored_report = reports[-1].read_text(encoding="utf-8")
        assert "REQ-002: removed since last baseline" in anchored_report
        assert "**Baseline drift: compared v1.0.0 → v2.0.0 (--baseline anchor)**" in anchored_report

        # The anchored run must NOT poison the fingerprint cache: the next
        # unanchored run still sees the auto-pair findings (clean), not the
        # cached anchored findings.
        rc_after = audit_cmd.run(root, {"quick": False})
        capsys.readouterr()
        assert rc_after == 0

    def test_unknown_baseline_warns_and_falls_back(self, tmp_path, monkeypatch, capsys):
        # Accounting-not-policing: a typo in --baseline warns loudly, then the
        # audit proceeds with the auto pair and the identical exit code.
        root = tmp_path / "project"
        self._req(root)
        _baseline_file(root, "v1.0.0", {"REQ-001": _snap_entry(), "REQ-002": _snap_entry(status="draft")})
        _baseline_file(root, "v1.1.0", {"REQ-001": _snap_entry()})
        _baseline_file(root, "v2.0.0", {"REQ-001": _snap_entry()})
        self._quiet(monkeypatch)

        rc_auto = audit_cmd.run(root, {"quick": False})
        capsys.readouterr()

        rc_unknown = audit_cmd.run(root, {"quick": False, "baseline": "nope"})
        out = capsys.readouterr().out
        assert rc_unknown == rc_auto  # fallback keeps the auto-pair outcome
        assert "--baseline 'nope' not found" in out
        assert "falling back to the auto pair" in out

    def test_dry_run_with_anchor_writes_nothing_and_matches_exit_code(self, tmp_path, monkeypatch, capsys):
        # Dry-run parity holds on BOTH anchor paths (known and unknown): the
        # exit code is a pure function of findings, and no files are written.
        root = tmp_path / "project"
        self._req(root)
        _baseline_file(root, "v1.0.0", {"REQ-001": _snap_entry(), "REQ-002": _snap_entry(status="draft")})
        _baseline_file(root, "v1.1.0", {"REQ-001": _snap_entry()})
        _baseline_file(root, "v2.0.0", {"REQ-001": _snap_entry()})
        self._quiet(monkeypatch)

        def _files() -> list[str]:
            return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())

        # Known anchor: dry run escalates identically to the writing run, and
        # leaves the tree untouched.
        before = _files()
        rc_dry = audit_cmd.run(root, {"quick": False, "dry_run": True, "baseline": "v1.0.0"})
        capsys.readouterr()
        assert rc_dry == 2
        assert _files() == before
        rc_write = audit_cmd.run(root, {"quick": False, "baseline": "v1.0.0"})
        capsys.readouterr()
        assert rc_write == rc_dry

        # Unknown anchor: the fallback (auto pair) is clean here, so both dry
        # and writing runs exit 0 — parity on the warn-and-fallback path too —
        # and the dry run again writes nothing.
        before2 = _files()
        rc_dry2 = audit_cmd.run(root, {"quick": False, "dry_run": True, "baseline": "nope"})
        out = capsys.readouterr().out
        assert rc_dry2 == 0
        assert "--baseline 'nope' not found" in out
        assert _files() == before2
        rc_write2 = audit_cmd.run(root, {"quick": False, "baseline": "nope"})
        capsys.readouterr()
        assert rc_write2 == rc_dry2


# ── CHL-344 A0: lossless findings cache + generation key ────────────────────


class TestLosslessCache:
    """A0 (CHL-344): the findings cache is lossless and generation-keyed.

    Pre-A0 the cache stored ``all_findings_raw[:20]`` only, so a cache-hit run
    replayed a truncated set while the AUD stamp had already recorded the full
    totals (AUD-075 stamped summary_info=187; a cached dry-run printed 20).
    The fingerprint also keyed on artifact content only, so lens-code changes
    could not invalidate replays. Both are fixed here: full-set round-trip,
    generation-bump recompute, dry-run parity preserved.
    """

    N_HORIZ_REQ = 15
    N_HORIZ_STORY = 5
    N_VERT = 3
    N_CC_INFO = 2
    N_CC_WARN = 2
    TOTAL = N_HORIZ_REQ + N_HORIZ_STORY + N_VERT + N_CC_INFO + N_CC_WARN  # 27 > 20

    @staticmethod
    def _req(root: Path) -> None:
        (root / "_specflow" / "specs" / "requirements").mkdir(parents=True)
        (root / "_specflow" / "specs" / "requirements" / "REQ-001.md").write_text(
            "---\nid: REQ-001\ntitle: T\ntype: requirement\nstatus: approved\n"
            "tags: []\nsuspect: false\nlinks: []\nfingerprint: x\n---\n\n# T\n",
            encoding="utf-8",
        )

    @classmethod
    def _stub_axes(cls, monkeypatch) -> None:
        """Deterministic 27 findings (>20): all info except 2 docs-staleness
        warns (accounting), so exit 0 and no CHL creation. Factories rebuild
        the structures per call because run() mutates findings in place."""

        def _horiz() -> dict:
            return {
                "requirement": [
                    {"severity": "info", "message": f"req info {i}"}
                    for i in range(cls.N_HORIZ_REQ)
                ],
                "story": [
                    {"severity": "info", "message": f"story info {i}"}
                    for i in range(cls.N_HORIZ_STORY)
                ],
            }

        def _vert() -> list:
            return [
                {"severity": "info", "message": f"vert info {i}"}
                for i in range(cls.N_VERT)
            ]

        def _cc() -> dict:
            return {
                "docs-staleness": [
                    {"severity": "warn", "message": f"stale doc {i}"}
                    for i in range(cls.N_CC_WARN)
                ],
                "consistency": [
                    {"severity": "info", "message": f"cc info {i}"}
                    for i in range(cls.N_CC_INFO)
                ],
            }

        monkeypatch.setattr(audit_cmd, "_horizontal_analysis", lambda arts: _horiz())
        monkeypatch.setattr(audit_cmd, "_vertical_analysis", lambda arts: _vert())
        monkeypatch.setattr(
            audit_cmd, "_cross_cutting_analysis", lambda arts, r, **kw: _cc()
        )
        # Avoid AUD/CHL artifact side effects in the minimal fixture.
        monkeypatch.setattr(audit_cmd.art_lib, "create_artifact", lambda *a, **k: {"ok": False})
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts", lambda *a, **k: [])

    @staticmethod
    def _findings_line(out: str) -> str:
        return next(l for l in out.splitlines() if "Findings:" in l)

    def test_over_20_findings_round_trip(self, tmp_path, monkeypatch, capsys):
        # (a) A fresh run caches ALL findings (pre-A0: only the first 20), and
        # a cache-hit run replays the identical full set with identical summary
        # counts (the Findings line mirrors the AUD stamp fields).
        root = tmp_path / "project"
        self._req(root)
        self._stub_axes(monkeypatch)

        rc_fresh = audit_cmd.run(root, {"quick": False})
        out_fresh = capsys.readouterr().out
        assert rc_fresh == 0

        cache_dir = root / ".specflow" / "audits" / ".cache"
        cache_files = sorted(cache_dir.glob("*.md"))
        assert len(cache_files) == 1
        cached = audit_cmd._load_cached_findings(cache_dir, cache_files[0].stem)
        assert len(cached) == self.TOTAL  # pre-A0 this was capped at 20
        assert {f.get("axis") for f in cached} == {"horizontal", "vertical", "cross-cutting"}
        expected_msgs = {f"req info {i}" for i in range(self.N_HORIZ_REQ)}
        expected_msgs |= {f"story info {i}" for i in range(self.N_HORIZ_STORY)}
        expected_msgs |= {f"vert info {i}" for i in range(self.N_VERT)}
        expected_msgs |= {f"cc info {i}" for i in range(self.N_CC_INFO)}
        expected_msgs |= {f"stale doc {i}" for i in range(self.N_CC_WARN)}
        assert {f["message"] for f in cached} == expected_msgs

        line_fresh = self._findings_line(out_fresh)
        assert "0 error(s)" in line_fresh
        assert "2 warning(s)" in line_fresh
        assert "25 info" in line_fresh  # 27 total − 2 accounting warns

        # Cache-hit run: identical full set → identical counts and exit code,
        # and the hit itself does not rewrite the cache.
        rc_cached = audit_cmd.run(root, {"quick": False})
        out_cached = capsys.readouterr().out
        assert rc_cached == rc_fresh
        assert "reusing previous findings" in out_cached
        assert self._findings_line(out_cached) == line_fresh
        assert sorted(cache_dir.glob("*.md")) == cache_files

    def test_generation_bump_forces_recompute(self, tmp_path, monkeypatch, capsys):
        # (b) Bumping _CACHE_GENERATION changes every fingerprint, so the
        # existing cache file can never match: the next run recomputes fresh
        # and writes a cache file under the new-generation key.
        root = tmp_path / "project"
        self._req(root)
        self._stub_axes(monkeypatch)

        rc1 = audit_cmd.run(root, {"quick": False})
        capsys.readouterr()
        assert rc1 == 0
        cache_dir = root / ".specflow" / "audits" / ".cache"
        gen1_files = sorted(cache_dir.glob("*.md"))
        assert len(gen1_files) == 1

        monkeypatch.setattr(
            audit_cmd, "_CACHE_GENERATION", audit_cmd._CACHE_GENERATION + 1
        )
        rc2 = audit_cmd.run(root, {"quick": False})
        out2 = capsys.readouterr().out
        assert rc2 == rc1
        assert "reusing previous findings" not in out2   # no replay
        assert "Running horizontal analysis" in out2     # fresh compute
        gen2_files = sorted(cache_dir.glob("*.md"))
        assert len(gen2_files) == 2                      # new-gen key written
        assert gen1_files[0] in gen2_files               # old file left intact

    def test_dry_run_with_populated_cache_reads_and_writes_nothing(
        self, tmp_path, monkeypatch, capsys
    ):
        # (c) With a populated cache, --dry-run still reads the full cached set
        # (identical Findings line and exit code as the writing run) while
        # writing nothing at all — parity preserved on the replay path too.
        root = tmp_path / "project"
        self._req(root)
        self._stub_axes(monkeypatch)

        rc_write = audit_cmd.run(root, {"quick": False})   # populates the cache
        out_write = capsys.readouterr().out
        cache_dir = root / ".specflow" / "audits" / ".cache"
        assert len(list(cache_dir.glob("*.md"))) == 1

        def _files() -> list[str]:
            return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())

        before = _files()
        rc_dry = audit_cmd.run(root, {"quick": False, "dry_run": True})
        out_dry = capsys.readouterr().out
        assert _files() == before                          # wrote nothing
        assert rc_dry == rc_write                          # exit-code parity
        assert "reusing previous findings" in out_dry      # read the cache
        assert self._findings_line(out_dry) == self._findings_line(out_write)


# ── CHL-344 A3: per-AC observability rows in the report body ────────────────
#
# The ~N unclassified/aspirational AC rows surface in the REPORT BODY (a new
# "## AC observability detail" section), NOT the findings list — as INFO
# findings they would inflate summary_info trends, replay through the cache,
# and never mint CHLs. The findings list, Summary counts, and AUD stamp are
# byte-identical with and without the section. The full all-class table
# (observable included) lives in subagent-cross-cutting.md. The section is a
# pure read over the loaded artifact list (chain-coverage precedent), so it
# renders identically on fresh runs, cache hits, and --dry-run, and is
# suppressed under --quick alongside the cross-cutting analysis.


def _ac_obs_req(root: Path, aid: str, items: list[str]) -> None:
    """One approved REQ whose AC section carries the given items in order."""
    acs = "\n".join(f"- {it}" for it in items)
    _write_art(root, f"_specflow/specs/requirements/{aid}.md",
               f"---\nid: {aid}\ntitle: T\ntype: requirement\nstatus: approved\n"
               "tags: []\nsuspect: false\nlinks: []\nfingerprint: x\n---\n\n# T\n\n"
               f"## Acceptance Criteria\n{acs}\n")


def _ac_obs_fixture(root: Path) -> None:
    """REQ-001 mixes all three classes; REQ-002 is fully observable.

    REQ-001: "returns exit code 0" → observable, "the relay energizes" →
    unclassified (cry-wolf guard: a domain observable), "responds quickly" →
    aspirational. REQ-002: "creates a file" → observable. So the report
    appendix must carry exactly the two REQ-001 rows (observable excluded) and
    omit REQ-002 entirely, while the subagent table carries all four items.
    """
    _ac_obs_req(root, "REQ-001", [
        "returns exit code 0",       # observable
        "the relay energizes",       # unclassified (domain observable)
        "responds quickly",          # aspirational
    ])
    _ac_obs_req(root, "REQ-002", [
        "creates a file",            # observable
    ])


def _ac_obs_section(report: str) -> str:
    """The '## AC observability detail' block, from its heading to the next
    '## ' heading (exclusive). Empty string when the section is absent."""
    marker = "## AC observability detail"
    start = report.find(marker)
    if start == -1:
        return ""
    nxt = report.find("\n## ", start + len(marker))
    return report[start:] if nxt == -1 else report[start:nxt + 1]


def _ac_obs_table(report: str) -> str:
    """The full per-AC table block in subagent-cross-cutting.md, or ''."""
    marker = "## ac-observability — full per-AC table"
    start = report.find(marker)
    if start == -1:
        return ""
    nxt = report.find("\n## ", start + len(marker))
    return report[start:] if nxt == -1 else report[start:nxt + 1]


class TestAcObservabilityDetailSection:
    """A3 (CHL-344): per-AC rows in the report body; full table in the
    cross-cutting subagent file; findings/Summary/stamp untouched."""

    @staticmethod
    def _quiet(monkeypatch, cc=None) -> None:
        """Silence the three axes to deterministic values (the section is a
        pure read over artifacts, independent of the axes) and suppress
        AUD/CHL side effects so only the report/subagent files vary."""
        monkeypatch.setattr(audit_cmd, "_horizontal_analysis", lambda arts: {})
        monkeypatch.setattr(audit_cmd, "_vertical_analysis", lambda arts: [])
        monkeypatch.setattr(audit_cmd, "_cross_cutting_analysis",
                            lambda arts, r, **kw: cc or {})
        monkeypatch.setattr(audit_cmd.art_lib, "create_artifact",
                            lambda *a, **k: {"ok": False})
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts",
                            lambda *a, **k: [])

    # (a) section present on the normal (writing) run, correct rows + markers.
    def test_section_present_with_correct_rows(self, tmp_path, monkeypatch, capsys):
        root = tmp_path / "project"
        _ac_obs_fixture(root)
        self._quiet(monkeypatch)
        rc = audit_cmd.run(root, {"quick": False})
        capsys.readouterr()
        assert rc == 0
        report = _latest_report(root)
        section = _ac_obs_section(report)
        assert section, "expected the AC observability detail section"
        # Noise bound: observable excluded, fully-observable REQ-002 omitted.
        assert "### REQ-001" in section
        assert "REQ-002" not in section
        assert "[unclassified] the relay energizes" in section
        assert "[aspirational] responds quickly" in section
        assert "returns exit code 0" not in section
        assert "creates a file" not in section
        # The intro carries the honest counts (2 actionable of 4 total).
        assert "2 of 4 AC item(s)" in section
        # REQ IDs are sorted; item order is stable (document order).
        assert section.index("REQ-001") < section.index("the relay energizes")

    # (b) section present on the cache-hit path (pure read over artifacts).
    def test_section_present_on_cache_hit(self, tmp_path, monkeypatch, capsys):
        root = tmp_path / "project"
        _ac_obs_fixture(root)
        # One cross-cutting info so the cache stores a NON-EMPTY findings set
        # (an empty list is falsy and never registers as a hit).
        self._quiet(monkeypatch, cc={"baseline-drift": [
            {"severity": "info", "message": "baseline info"}]})

        rc_fresh = audit_cmd.run(root, {"quick": False})
        capsys.readouterr()
        assert rc_fresh == 0
        fresh_section = _ac_obs_section(_latest_report(root))
        assert fresh_section

        rc_cached = audit_cmd.run(root, {"quick": False})
        out_cached = capsys.readouterr().out
        assert rc_cached == rc_fresh
        assert "reusing previous findings" in out_cached   # a genuine hit
        cached_section = _ac_obs_section(_latest_report(root))
        assert cached_section, "section must render on the cache-hit path too"
        assert cached_section == fresh_section

    # (c) section present in the in-memory report under --dry-run, which still
    # writes nothing (parity: pure rendering from already-loaded data).
    def test_section_renders_in_dry_run_report_without_writing(
        self, tmp_path, monkeypatch, capsys
    ):
        root = tmp_path / "project"
        _ac_obs_fixture(root)
        self._quiet(monkeypatch)

        captured: dict = {}
        real_render = audit_cmd._render_report

        def _spy(ts, *a, **kw):
            report = real_render(ts, *a, **kw)
            captured["report"] = report
            return report

        monkeypatch.setattr(audit_cmd, "_render_report", _spy)

        def _files() -> list[str]:
            return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())

        before = _files()
        rc = audit_cmd.run(root, {"quick": False, "dry_run": True})
        capsys.readouterr()
        assert rc == 0
        assert _files() == before                       # wrote nothing
        assert "report" in captured                     # rendered in memory
        section = _ac_obs_section(captured["report"])
        assert section, "section must render in the dry-run in-memory report"
        assert "[aspirational] responds quickly" in section

    # (d) section ABSENT under --quick (cross-cutting is skipped there), in
    # both the report body and the cross-cutting subagent file.
    def test_section_absent_under_quick(self, tmp_path, monkeypatch, capsys):
        root = tmp_path / "project"
        _ac_obs_fixture(root)
        self._quiet(monkeypatch)
        rc = audit_cmd.run(root, {"quick": True})
        capsys.readouterr()
        assert rc == 0
        report = _latest_report(root)
        assert "## AC observability detail" not in report
        snaps = sorted((root / ".specflow" / "audits").glob("*/subagent-cross-cutting.md"))
        assert snaps, "expected a cross-cutting subagent file"
        assert "## ac-observability — full per-AC table" not in snaps[-1].read_text(
            encoding="utf-8")

    # (e) findings list + Summary counts byte-identical with/without the
    # section — the section adds NO findings and touches NO counts. Render the
    # SAME findings twice (ac_observability set vs None); removing the section
    # from the with-render must reproduce the without-render byte-for-byte.
    def test_findings_and_summary_unchanged_by_section(self):
        arts = [
            _art("REQ-001", "requirement", status="approved",
                 body="## Acceptance Criteria\n"
                      "- returns exit code 0\n"
                      "- the relay energizes\n"
                      "- responds quickly\n"),
        ]
        agg = ac_quality.classify_reqs_observability(arts)
        assert agg["aspirational"] + agg["unclassified"] == 2  # fixture sanity

        horizontal = {"requirement": [{"severity": "info", "message": "a horiz info"}]}
        vertical = [{"severity": "warn", "message": "a vertical warn"}]
        cc = {"consistency": [
            {"severity": "warn", "message": "a structural warn"},
            {"severity": "info", "message": "an info"},
        ]}
        kwargs = dict(horizontal=horizontal, vertical=vertical, cross_cutting=cc,
                      cached_count=0, total_artifacts=1, scope_info=[],
                      chain_coverage=None, prior_audit=None)
        with_sec = audit_cmd._render_report("TS", ac_observability=agg, **kwargs)
        without = audit_cmd._render_report("TS", ac_observability=None, **kwargs)

        section = _ac_obs_section(with_sec)
        assert section, "with-render must carry the section"
        assert "## AC observability detail" not in without
        # The ONLY difference between the two renders is the section block.
        assert with_sec.replace(section, "") == without
        # Summary counts derive ONLY from findings and are identical in both.
        for r in (with_sec, without):
            assert "| Error    | 0 |" in r
            assert "| Warning  | 2 |" in r   # vertical + consistency warns
            assert "| Info     | 2 |" in r   # horiz info + consistency info

    # (f) full all-class table (observable included) in subagent-cross-cutting.
    def test_full_table_in_cross_cutting_subagent(self, tmp_path, monkeypatch, capsys):
        root = tmp_path / "project"
        _ac_obs_fixture(root)
        self._quiet(monkeypatch)
        rc = audit_cmd.run(root, {"quick": False})
        capsys.readouterr()
        assert rc == 0
        snaps = sorted((root / ".specflow" / "audits").glob("*/subagent-cross-cutting.md"))
        assert snaps, "expected a cross-cutting subagent file"
        sub = snaps[-1].read_text(encoding="utf-8")
        table = _ac_obs_table(sub)
        assert table, "expected the full per-AC table in subagent-cross-cutting.md"
        # Observable INCLUDED here (the noise bound applies only to report.md).
        assert "[observable] returns exit code 0" in table
        assert "[observable] creates a file" in table
        assert "[unclassified] the relay energizes" in table
        assert "[aspirational] responds quickly" in table
        # Both REQs appear (no noise-bound omission in the full table).
        assert "### REQ-001" in table
        assert "### REQ-002" in table

    # (g) determinism regression: byte-identical section across a fresh run and
    # a cache-hit run. Non-deterministic ordering would register as false drift
    # in future audits, so the two renders must agree exactly.
    def test_byte_identical_render_fresh_vs_cache_hit(self, tmp_path, monkeypatch, capsys):
        root = tmp_path / "project"
        _ac_obs_fixture(root)
        self._quiet(monkeypatch, cc={"baseline-drift": [
            {"severity": "info", "message": "baseline info"}]})

        assert audit_cmd.run(root, {"quick": False}) == 0
        capsys.readouterr()
        fresh_section = _ac_obs_section(_latest_report(root))

        # A cache-hit run renders the section byte-identically.
        out_cached = ""
        assert audit_cmd.run(root, {"quick": False}) == 0
        out_cached = capsys.readouterr().out
        assert "reusing previous findings" in out_cached
        cached_section = _ac_obs_section(_latest_report(root))

        assert fresh_section == cached_section
        assert fresh_section.encode("utf-8") == cached_section.encode("utf-8")

    # (h) determinism regression at the pure-function level: repeated renders of
    # the same aggregate are byte-identical (guards dict/set ordering leaks),
    # and REQ IDs render sorted even when the artifact list is unsorted.
    def test_render_is_a_pure_function_of_the_aggregate(self):
        arts = [
            # Listed out of ID order on purpose: the renderer must sort by ID.
            _art("REQ-002", "requirement", status="approved",
                 body="## Acceptance Criteria\n- works correctly\n"),
            _art("REQ-001", "requirement", status="approved",
                 body="## Acceptance Criteria\n"
                      "- returns exit code 0\n"
                      "- the relay energizes\n"
                      "- responds quickly\n"),
        ]
        agg = ac_quality.classify_reqs_observability(arts)
        lines_a = audit_cmd._ac_observability_detail_lines(agg)
        lines_b = audit_cmd._ac_observability_detail_lines(agg)
        assert lines_a == lines_b
        rendered = "\n".join(lines_a)
        assert "## AC observability detail" in rendered
        # Sorted REQ IDs even though the input list was reversed.
        assert rendered.index("### REQ-001") < rendered.index("### REQ-002")
        # None aggregate (--quick) → no section.
        assert audit_cmd._ac_observability_detail_lines(None) == []

    # (i) graceful silence: no REQs with ACs → no section (never an empty box).
    def test_section_absent_when_no_reqs_have_acs(self, tmp_path, monkeypatch, capsys):
        root = tmp_path / "project"
        _write_art(root, "_specflow/specs/requirements/REQ-001.md",
                   "---\nid: REQ-001\ntitle: T\ntype: requirement\nstatus: approved\n"
                   "tags: []\nsuspect: false\nlinks: []\nfingerprint: x\n---\n\n# T\n")
        self._quiet(monkeypatch)
        assert audit_cmd.run(root, {"quick": False}) == 0
        capsys.readouterr()
        assert "## AC observability detail" not in _latest_report(root)


# ── CHL-344 A4: NFR vocabulary + nfr-coverage accounting parity ─────────────
#
# A4 demotes nfr-coverage to accounting: the >=50%-missing warn is still
# printed and stamped but can never drive exit-2 (pre-A4 it was the ONLY
# REQ-quality warn that could block a release-gate project-audit). The lens
# also reports out-of-vocabulary values as ONE deterministic INFO line — the
# typo NET itself is artifact-lint's warn-only nfr-category check.


class TestNfrCoverageAccounting:
    def test_nfr_coverage_registered_accounting(self):
        assert "nfr-coverage" in audit_cmd._ACCOUNTING_CONCERNS

    def test_nfr_warn_lands_in_accounting_bucket(self):
        findings = [
            _f("cross-cutting", "warn",
               "20/39 REQs have no non_functional_category",
               concern="nfr-coverage"),
        ]
        escalating, accounting = audit_cmd._count_warns(findings)
        assert escalating == 0
        assert accounting == 1

    def test_lens_missing_over_half_warns_but_never_escalates(self):
        # >=50% missing keeps its warn severity (truth-telling) — but the
        # concern stamp routes it to the accounting bucket, never exit-2.
        arts = [
            _art("REQ-001", "requirement", status="approved"),
            _art("REQ-002", "requirement", status="approved"),
        ]
        findings = audit_cmd._nfr_coverage_lens(arts)
        warns = [f for f in findings if f["severity"] == "warn"]
        assert len(warns) == 1
        assert "2/2 REQs have no non_functional_category" in warns[0]["message"]
        escalating, accounting = audit_cmd._count_warns(findings)
        assert escalating == 0
        assert accounting == 1

    def test_lens_missing_under_half_is_info(self):
        # Regression guard for the pre-existing threshold: <50% stays info.
        arts = [
            _art("REQ-001", "requirement", status="approved",
                 non_functional_category="functional"),
            _art("REQ-002", "requirement", status="approved",
                 non_functional_category="functional"),
            _art("REQ-003", "requirement", status="approved"),
        ]
        findings = audit_cmd._nfr_coverage_lens(arts)
        missing = [f for f in findings
                   if "have no non_functional_category" in f["message"]]
        assert missing and missing[0]["severity"] == "info"

    def test_lens_out_of_vocab_info_line_sorted_and_deterministic(self):
        arts = [
            _art("REQ-001", "requirement", status="approved",
                 non_functional_category="securityy"),   # typo
            _art("REQ-002", "requirement", status="approved",
                 non_functional_category="perfomance"),  # typo
            _art("REQ-003", "requirement", status="approved",
                 non_functional_category="security"),    # in-vocabulary
        ]
        findings_a = audit_cmd._nfr_coverage_lens(arts)
        findings_b = audit_cmd._nfr_coverage_lens(arts)
        assert findings_a == findings_b  # deterministic across runs
        oov = [f for f in findings_a if "Out-of-vocabulary" in f["message"]]
        assert len(oov) == 1             # ONE line, not one per value
        assert oov[0]["severity"] == "info"
        # Sorted values in a single line.
        assert "perfomance, securityy" in oov[0]["message"]

    def test_lens_no_oov_line_when_vocabulary_clean(self):
        arts = [
            _art("REQ-001", "requirement", status="approved",
                 non_functional_category="functional"),
            _art("REQ-002", "requirement", status="approved"),
        ]
        findings = audit_cmd._nfr_coverage_lens(arts)
        assert findings  # missing-category + distribution lines still render
        assert not any("Out-of-vocabulary" in f["message"] for f in findings)

    def test_run_nfr_warn_only_exits_zero_and_stamps_zero_escalating(
        self, tmp_path, monkeypatch, capsys
    ):
        # Run-level: an audit whose ONLY warn is nfr-coverage must exit 0 and
        # stamp summary_warns_escalating == 0 — the release-gate job running
        # project-audit without continue-on-error is never blocked by it.
        root = tmp_path / "project"
        _write_art(root, "_specflow/specs/requirements/REQ-001.md",
                   "---\nid: REQ-001\ntitle: T\ntype: requirement\nstatus: approved\n"
                   "tags: []\nsuspect: false\nlinks: []\nfingerprint: x\n---\n\n# T\n")
        monkeypatch.setattr(audit_cmd, "_horizontal_analysis", lambda arts: {})
        monkeypatch.setattr(audit_cmd, "_vertical_analysis", lambda arts: [])
        monkeypatch.setattr(
            audit_cmd, "_cross_cutting_analysis",
            lambda arts, r, **kw: {"nfr-coverage": [
                {"severity": "warn",
                 "message": "20/39 REQs have no non_functional_category"},
            ]},
        )
        stamps: dict = {}

        def fake_create(*a, **kw):
            stamps.update(kw)
            return {"ok": False}

        monkeypatch.setattr(audit_cmd.art_lib, "create_artifact", fake_create)
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts",
                            lambda *a, **k: [])

        rc = audit_cmd.run(root, {"quick": False})
        out = capsys.readouterr().out
        assert rc == 0, f"expected CLEAN (exit 0), got {rc}\n{out}"
        assert "accounting" in out.lower()
        # The AUD stamp records the split: zero escalating, one accounting.
        assert stamps["summary_warns_escalating"] == 0
        assert stamps["summary_warns_accounting"] == 1
        assert stamps["summary_warns"] == 1
