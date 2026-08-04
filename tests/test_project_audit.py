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


# (e) ac-coverage lens: zero-tests REQ → warn; mismatch → info.


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

    def test_count_mismatch_emits_info(self):
        req = self._req_with_acs("REQ-001", 3)  # 3 ACs
        qt = _art(
            "QT-001", "qualification-test", status="verified",
            links=[art_lib.Link(target="REQ-001", role="verified_by")],
        )
        findings = audit_cmd._ac_coverage_lens([req, qt])
        assert any(f["severity"] == "info" and "review" in f["message"] for f in findings)
        assert not any(f["severity"] == "warn" for f in findings)

    def test_ac_coverage_warns_are_accounting(self):
        req = self._req_with_acs("REQ-001", 2)
        findings = audit_cmd._ac_coverage_lens([req])
        warns = [f for f in findings if f["severity"] == "warn"]
        assert warns
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
                        lambda arts, r: cross_cutting or {})
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
                            lambda arts, r: {"baseline-drift": infos})
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

    def test_stamped_fields_pass_schema_lint(self, tmp_path):
        # The audit schema enumerates the stamp fields as optional, and the
        # global known-meta whitelist covers pre-existing on-disk schemas — so
        # a stamped AUD never draws an "Unknown field" finding.
        from specflow.lib import lint as lint_lib

        stamped = _art("AUD-001", "audit", status="open",
                       summary_errors=0, summary_warns=2, summary_info=5,
                       chain_coverage_pct=61)
        schema = {"required_fields": ["id", "title", "type", "status", "created"],
                  "optional_fields": [], "allowed_status": {"open": [], "closed": ["open"]}}
        issues = lint_lib.validate_artifact_schema(stamped, schema)
        assert not any("Unknown field" in i["message"] for i in issues)
