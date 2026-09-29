"""Coverage semantics (STORY-679, STORY-680).

STORY-679: ``check_coverage`` credits the canonical ``REQ refined_by ARCH``
shape (role_targets.py, v1.14.2) alongside the legacy ``ARCH derives_from
REQ``, and credits a STORY's own outgoing ``verified_by`` to a test. A REQ
covered ONLY via the legacy derives_from shape gets one accounting-class INFO
line (never a warning, never blocking, never an exit-2 driver).

STORY-680: ``find_missing_v_pairs`` requires the verifier to be the PAIRED
test type for the spec level (V_MODEL_PAIRS), counts the spec's own outgoing
``verified_by`` to that paired type, and returns the paired test prefix.
"""

from __future__ import annotations

from pathlib import Path

from specflow.commands import artifact_lint as lint_cmd
from specflow.commands import project_audit as audit_cmd
from specflow.lib import artifacts as art_lib


def _art(art_id: str, art_type: str, status: str = "draft",
         links: list[tuple[str, str]] | None = None) -> art_lib.Artifact:
    return art_lib.Artifact(
        path=Path(f"{art_id}.md"),
        frontmatter={"id": art_id, "title": art_id, "type": art_type, "status": status},
        body="",
        links=[art_lib.Link(target=t, role=r) for t, r in (links or [])],
    )


def _tests_for(story_id: str) -> list[art_lib.Artifact]:
    return [
        _art("UT-001", "unit-test", links=[(story_id, "verified_by")]),
        _art("IT-001", "integration-test", links=[(story_id, "verified_by")]),
        _art("QT-001", "qualification-test", links=[(story_id, "verified_by")]),
    ]


# ── STORY-679 ────────────────────────────────────────────────────────────────

class TestCoverageCanonicalArchShape:
    def test_req_refined_by_arch_only_is_covered(self):
        # AC1: the canonical REQ refined_by ARCH shape credits the REQ.
        arts = [
            _art("REQ-001", "requirement", "approved", [("ARCH-001", "refined_by")]),
            _art("ARCH-001", "architecture"),
            _art("STORY-001", "story", "approved", [("REQ-001", "implements")]),
            *_tests_for("STORY-001"),
        ]
        result = lint_cmd.check_coverage(arts)
        assert "no ARCH derives_from" not in result["detail"]
        assert result["structural_warning_count"] == 0
        assert result["warning_count"] == 0
        assert result["accounting_count"] == 0

    def test_refined_by_non_arch_target_does_not_credit(self):
        # Only an ARCH target counts as architectural coverage.
        arts = [
            _art("REQ-001", "requirement", "approved", [("DDD-001", "refined_by")]),
            _art("DDD-001", "detailed-design"),
        ]
        result = lint_cmd.check_coverage(arts)
        assert "[REQ-001] no ARCH derives_from" in result["detail"]

    def test_derives_from_only_emits_accounting_info_not_warning(self):
        # AC3: legacy-only coverage → one accounting INFO line, never a warn.
        arts = [
            _art("REQ-001", "requirement", "approved"),
            _art("ARCH-001", "architecture", links=[("REQ-001", "derives_from")]),
            _art("STORY-001", "story", "approved", [("REQ-001", "implements")]),
            *_tests_for("STORY-001"),
        ]
        result = lint_cmd.check_coverage(arts)
        assert result["warning_count"] == 0
        assert result["blocking_count"] == 0
        assert result["accounting_count"] == 1
        assert "REQ-001" in result["accounting_detail"]
        assert "ℹ" in result["accounting_detail"]
        assert "⚠" not in result["accounting_detail"]
        # Rendered in the check detail as an info line (escalation-proof).
        assert result["accounting_detail"] in result["detail"]
        assert lint_cmd._warning_detail_lines(result) == []

    def test_both_shapes_emit_no_accounting_line(self):
        arts = [
            _art("REQ-001", "requirement", "approved", [("ARCH-001", "refined_by")]),
            _art("ARCH-001", "architecture", links=[("REQ-001", "derives_from")]),
        ]
        result = lint_cmd.check_coverage(arts)
        assert result["accounting_count"] == 0
        assert result["accounting_detail"] == ""

    def test_accounting_line_collapses_many_reqs(self):
        arts = []
        for i in range(1, 8):
            arts.append(_art(f"REQ-00{i}", "requirement", "approved"))
            arts.append(_art(f"ARCH-00{i}", "architecture", links=[(f"REQ-00{i}", "derives_from")]))
        result = lint_cmd.check_coverage(arts)
        assert result["accounting_count"] == 7
        assert result["accounting_detail"].count("ℹ") == 1
        assert "(+2 more)" in result["accounting_detail"]


class TestCoverageStoryOutgoingVerifiedBy:
    def test_story_outgoing_verified_by_credits_tests(self):
        # AC2: STORY → test verified_by (legal per role_targets) credits the level.
        arts = [
            _art("REQ-001", "requirement", "approved", [("ARCH-001", "refined_by")]),
            _art("ARCH-001", "architecture"),
            _art("STORY-001", "story", "approved", [
                ("REQ-001", "implements"),
                ("UT-001", "verified_by"),
                ("IT-001", "verified_by"),
                ("QT-001", "verified_by"),
            ]),
            _art("UT-001", "unit-test"),
            _art("IT-001", "integration-test"),
            _art("QT-001", "qualification-test"),
        ]
        result = lint_cmd.check_coverage(arts)
        assert result["verification_warning_count"] == 0
        assert result["approved_story_covered"] == 1
        assert result["approved_story_total"] == 1

    def test_story_outgoing_verified_by_to_non_test_does_not_credit(self):
        arts = [
            _art("REQ-001", "requirement", "approved", [("ARCH-001", "refined_by")]),
            _art("ARCH-001", "architecture"),
            _art("STORY-001", "story", "approved", [
                ("REQ-001", "implements"),
                ("DEC-001", "verified_by"),
            ]),
            _art("DEC-001", "decision"),
        ]
        result = lint_cmd.check_coverage(arts)
        assert result["verification_warning_count"] == 3


class TestCoverageAccountingNeverEscalatesAudit:
    def test_project_audit_routes_accounting_line_as_info(self, tmp_path):
        arts = [
            _art("REQ-001", "requirement", "approved"),
            _art("ARCH-001", "architecture", links=[("REQ-001", "derives_from")]),
            _art("STORY-001", "story", "approved", [("REQ-001", "implements")]),
            *_tests_for("STORY-001"),
        ]
        results = audit_cmd._cross_cutting_analysis(arts, tmp_path, drift_pair=[])
        shape = results.get("coverage-shape", [])
        assert len(shape) == 1
        assert shape[0]["severity"] == "info"
        assert "coverage-shape" in audit_cmd._ACCOUNTING_CONCERNS
        esc, _acct = audit_cmd._count_warns(shape)
        assert esc == 0


# ── STORY-680 ────────────────────────────────────────────────────────────────

class TestVPairRequiresPairedTestType:
    def test_non_test_verifier_is_missing(self):
        # AC1: a verified_by from a non-test artifact does not pair the spec.
        arts = [
            _art("REQ-001", "requirement"),
            _art("STORY-001", "story", links=[("REQ-001", "verified_by")]),
        ]
        missing = art_lib.find_missing_v_pairs(arts)
        assert [(a.id, p) for a, p in missing] == [("REQ-001", "QT")]

    def test_wrong_level_test_is_missing(self):
        # A UT verifying a REQ is not the REQ's paired QT.
        arts = [
            _art("REQ-001", "requirement"),
            _art("UT-001", "unit-test", links=[("REQ-001", "verified_by")]),
        ]
        missing = art_lib.find_missing_v_pairs(arts)
        assert [(a.id, p) for a, p in missing] == [("REQ-001", "QT")]

    def test_paired_test_incoming_verified_by_pairs(self):
        arts = [
            _art("ARCH-001", "architecture"),
            _art("IT-001", "integration-test", links=[("ARCH-001", "verified_by")]),
        ]
        assert art_lib.find_missing_v_pairs(arts) == []

    def test_spec_outgoing_verified_by_to_paired_type_pairs(self):
        # AC2: the spec's own outgoing verified_by to the paired type counts.
        arts = [
            _art("DDD-001", "detailed-design", links=[("UT-001", "verified_by")]),
            _art("UT-001", "unit-test"),
        ]
        assert art_lib.find_missing_v_pairs(arts) == []

    def test_spec_outgoing_verified_by_to_wrong_type_is_missing(self):
        arts = [
            _art("DDD-001", "detailed-design", links=[("QT-001", "verified_by")]),
            _art("QT-001", "qualification-test"),
        ]
        missing = art_lib.find_missing_v_pairs(arts)
        assert [(a.id, p) for a, p in missing] == [("DDD-001", "UT")]

    def test_returns_paired_test_prefix(self):
        # AC3: tuple carries the paired TEST prefix, matching the docstring.
        arts = [
            _art("REQ-001", "requirement"),
            _art("ARCH-001", "architecture"),
            _art("DDD-001", "detailed-design"),
        ]
        got = {a.id: p for a, p in art_lib.find_missing_v_pairs(arts)}
        assert got == {"REQ-001": "QT", "ARCH-001": "IT", "DDD-001": "UT"}

    def test_links_check_renders_test_prefix(self, tmp_path):
        arts = [_art("REQ-001", "requirement")]
        result = lint_cmd._check_links(arts, tmp_path)
        assert "REQ-001 (no QT verification)" in result["detail"]


# ── CLI qualification (STORY-679 / STORY-680) ───────────────────────────────

def _write(root: Path, rel: str, aid: str, atype: str, status: str,
           links: list[tuple[str, str]] | None = None) -> None:
    p = root / "_specflow" / rel / f"{aid}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    link_yaml = "".join(f"- target: {t}\n  role: {r}\n" for t, r in (links or []))
    p.write_text(
        f"---\nid: {aid}\ntitle: {aid}\ntype: {atype}\nstatus: {status}\n"
        f"tags: []\nsuspect: false\nlinks:{' []' if not links else ''}\n{link_yaml}---\n\n# {aid}\n",
        encoding="utf-8",
    )


def _cli_project(tmp_path: Path, canonical: bool) -> Path:
    root = tmp_path / "proj"
    (root / ".specflow").mkdir(parents=True)
    if canonical:
        _write(root, "specs/requirements", "REQ-001", "requirement", "approved",
               [("ARCH-001", "refined_by")])
        _write(root, "specs/architecture", "ARCH-001", "architecture", "draft")
        _write(root, "work/stories", "STORY-001", "story", "approved", [
            ("REQ-001", "implements"), ("UT-001", "verified_by"),
            ("IT-001", "verified_by"), ("QT-001", "verified_by"),
        ])
        _write(root, "specs/unit-tests", "UT-001", "unit-test", "draft")
        _write(root, "specs/integration-tests", "IT-001", "integration-test", "draft")
        _write(root, "specs/qualification-tests", "QT-001", "qualification-test", "draft")
    else:
        _write(root, "specs/requirements", "REQ-001", "requirement", "approved")
        _write(root, "specs/architecture", "ARCH-001", "architecture", "draft",
               [("REQ-001", "derives_from")])
        _write(root, "work/stories", "STORY-001", "story", "approved",
               [("REQ-001", "implements"), ("REQ-001", "verified_by")])
    return root


class TestCoverageCli:
    def test_canonical_shapes_lint_clean(self, tmp_path, monkeypatch, capsys):
        from specflow import cli

        root = _cli_project(tmp_path, canonical=True)
        monkeypatch.chdir(root)
        rc = cli.main(["artifact-lint", "--type", "coverage"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "no ARCH derives_from" not in out
        assert "linked via 'verified_by'" not in out
        assert "refined only via legacy" not in out

    def test_legacy_shape_prints_accounting_info_and_passes(self, tmp_path, monkeypatch, capsys):
        from specflow import cli

        root = _cli_project(tmp_path, canonical=False)
        monkeypatch.chdir(root)
        rc = cli.main(["artifact-lint", "--type", "coverage"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "ℹ 1 approved REQ(s) refined only via legacy" in out

    def test_links_cli_reports_paired_test_prefix(self, tmp_path, monkeypatch, capsys):
        # STORY-680: REQ-001 is "verified" only by a STORY → still missing its QT.
        from specflow import cli

        root = _cli_project(tmp_path, canonical=False)
        monkeypatch.chdir(root)
        cli.main(["artifact-lint", "--type", "links"])
        out = capsys.readouterr().out
        assert "REQ-001 (no QT verification)" in out
