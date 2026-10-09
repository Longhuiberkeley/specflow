"""DEC-101 / STORY-735: staged ddd-shape accounting + truthful DDD-thread walk.

Two engine changes, one release-gate fix (v1.17.3):

(a) TRUTHFUL WALK — ``_vertical_analysis``'s DDD walk only saw a DDD whose OWN
    frontmatter links targeted a thread member with role refined_by /
    derives_from. It missed the canonical PARENT-HELD shape (an ARCH's own
    links[] carrying ``refined_by → DDD``, mirroring check_coverage's
    parent-held credit) and the legal DDD-held ``specified_by → ARCH`` shape
    (role_targets.py: detailed-design). Regression pinned here: DDD-033 carries
    ``specified_by ARCH-039``, so REQ-052/053 used to print 'ARCH exists but no
    DDD refinement' while a DDD existed — after the fix, NO row.

(b) ROW CLASS — when the REQ's thread has_stories (a STORY ``implements`` any
    thread member), the 'no DDD refinement' row is stamped
    ``concern="ddd-shape"`` (registered accounting). Predicate: a REQ whose
    V-model thread has an implementing STORY owes no DDD refinement. When
    has_stories is FALSE the row stays concern-less and escalates — gate
    equivalence with the pre-DEC-101 audit for genuine V-model holes. The
    concern-less no-ARCH / no-STORY rows are untouched, and ``lens:general``
    (their shared rule id) is NEVER accounting.

Fixtures mirror tests/test_project_audit.py (in-memory ``_art`` for the walk /
row-class unit tests; a disk project + ``audit_cmd.run`` for the end-to-end
dry-run exit-0 test).
"""

from __future__ import annotations

from pathlib import Path

from specflow.commands import artifact_lint
from specflow.commands import project_audit as audit_cmd
from specflow.core.policy import klass_for
from specflow.lib import artifacts as art_lib


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


def _ddd_rows(findings: list[dict[str, str]]) -> list[dict[str, str]]:
    return [f for f in findings if "no DDD refinement" in f["message"]]


# ── (b) row class: has_stories TRUE → accounting ddd-shape ───────────────────


class TestDddShapeAccounting:
    @staticmethod
    def _thread_no_ddd() -> list[art_lib.Artifact]:
        req = _art("REQ-001", "requirement", status="approved")
        arch = _art(
            "ARCH-001", "architecture", status="approved",
            links=[art_lib.Link(target="REQ-001", role="derives_from")],
        )
        story = _art(
            "STORY-001", "story", status="implemented",
            links=[art_lib.Link(target="REQ-001", role="implements")],
        )
        return [req, arch, story]

    def test_ddd_shape_registered_accounting(self):
        assert "ddd-shape" in audit_cmd._ACCOUNTING_CONCERNS
        # Distinct from (not a reuse of) the coverage-shape registration.
        assert "coverage-shape" in audit_cmd._ACCOUNTING_CONCERNS
        # lens:general is the shared rule id of the escalating no-ARCH /
        # no-STORY rows — registering it would blind the gate. NEVER.
        assert "lens:general" not in audit_cmd._ACCOUNTING_CONCERNS
        assert klass_for("audit/lens:general") == "escalating"
        assert klass_for("audit/ddd-shape") == "accounting"

    def test_row_carries_ddd_shape_concern_when_story_implements(self):
        findings = audit_cmd._vertical_analysis(self._thread_no_ddd())
        rows = _ddd_rows(findings)
        assert rows, "expected the 'no DDD refinement' row"
        assert rows[0].get("concern") == "ddd-shape"

    def test_count_warns_classes_ddd_shape_accounting(self):
        findings = audit_cmd._vertical_analysis(self._thread_no_ddd())
        rows = _ddd_rows(findings)
        escalating, accounting = audit_cmd._count_warns(rows)
        assert escalating == 0
        assert accounting == 1

    def test_story_via_arch_target_also_counts(self):
        # has_stories means a STORY `implements` ANY thread member — here the
        # STORY targets the ARCH, not the REQ, and the row is still accounting.
        req = _art("REQ-001", "requirement", status="approved")
        arch = _art(
            "ARCH-001", "architecture", status="approved",
            links=[art_lib.Link(target="REQ-001", role="derives_from")],
        )
        story = _art(
            "STORY-001", "story", status="implemented",
            links=[art_lib.Link(target="ARCH-001", role="implements")],
        )
        rows = _ddd_rows(audit_cmd._vertical_analysis([req, arch, story]))
        assert rows and rows[0].get("concern") == "ddd-shape"


# ── (b) gate equivalence: concern-less rows still escalate ───────────────────


class TestConcernlessRowsStillEscalate:
    def test_no_story_keeps_ddd_row_escalating(self):
        # has_stories FALSE → the row keeps NO concern and escalates: nobody
        # may later 'simplify' by stamping ddd-shape unconditionally.
        req = _art("REQ-001", "requirement", status="approved")
        arch = _art(
            "ARCH-001", "architecture", status="approved",
            links=[art_lib.Link(target="REQ-001", role="derives_from")],
        )
        findings = audit_cmd._vertical_analysis([req, arch])
        rows = _ddd_rows(findings)
        assert rows and "concern" not in rows[0]
        escalating, accounting = audit_cmd._count_warns(rows)
        assert escalating == 1 and accounting == 0

    def test_no_arch_and_no_story_rows_have_no_concern(self):
        req = _art("REQ-001", "requirement", status="approved")
        findings = audit_cmd._vertical_analysis([req])
        no_arch = [f for f in findings if "no ARCH" in f["message"]]
        no_story = [f for f in findings if "no STORY" in f["message"]]
        assert no_arch and no_story
        assert "concern" not in no_arch[0]
        assert "concern" not in no_story[0]
        escalating, _ = audit_cmd._count_warns(no_arch + no_story)
        assert escalating == 2  # both still drive exit-2


# ── (a) truthful walk: all three legal DDD shapes are seen ───────────────────


class TestTruthfulDddWalk:
    def test_ddd_held_derives_from_still_seen(self):
        # The pre-existing shape (DDD's own link → thread member) is unchanged.
        req = _art("REQ-001", "requirement", status="approved")
        arch = _art(
            "ARCH-001", "architecture", status="approved",
            links=[art_lib.Link(target="REQ-001", role="derives_from")],
        )
        ddd = _art(
            "DDD-001", "detailed-design", status="approved",
            links=[art_lib.Link(target="ARCH-001", role="derives_from")],
        )
        assert not _ddd_rows(audit_cmd._vertical_analysis([req, arch, ddd]))

    def test_parent_held_arch_refined_by_ddd_no_row(self):
        # Canonical PARENT-HELD shape: the ARCH's own links[] carry
        # refined_by → DDD; the DDD itself links nothing. Mirrors
        # check_coverage's parent-held credit (artifact_lint.py, STORY-679).
        req = _art("REQ-001", "requirement", status="approved")
        arch = _art(
            "ARCH-001", "architecture", status="approved",
            links=[
                art_lib.Link(target="REQ-001", role="derives_from"),
                art_lib.Link(target="DDD-001", role="refined_by"),
            ],
        )
        ddd = _art("DDD-001", "detailed-design", status="approved", links=[])
        assert not _ddd_rows(audit_cmd._vertical_analysis([req, arch, ddd]))

    def test_ddd_specified_by_arch_no_row(self):
        # Regression (DDD-033 specified_by ARCH-039 → REQ-052/053 printed a
        # false row): the legal DDD-held specified_by shape must credit.
        req = _art("REQ-001", "requirement", status="approved")
        arch = _art(
            "ARCH-001", "architecture", status="approved",
            links=[art_lib.Link(target="REQ-001", role="derives_from")],
        )
        ddd = _art(
            "DDD-001", "detailed-design", status="approved",
            links=[art_lib.Link(target="ARCH-001", role="specified_by")],
        )
        assert not _ddd_rows(audit_cmd._vertical_analysis([req, arch, ddd]))

    def test_dangling_parent_held_refined_by_does_not_credit(self):
        # Mirror check_coverage: a refined_by target that does not resolve is
        # not a DDD. A dangling link must not silence the no-DDD row.
        req = _art("REQ-001", "requirement", status="approved")
        arch = _art(
            "ARCH-001", "architecture", status="approved",
            links=[
                art_lib.Link(target="REQ-001", role="derives_from"),
                art_lib.Link(target="DDD-999", role="refined_by"),
            ],
        )
        assert _ddd_rows(audit_cmd._vertical_analysis([req, arch]))

    def test_unrelated_ddd_does_not_credit(self):
        # A DDD pointing at some OTHER ARCH must not silence this REQ's row.
        req = _art("REQ-001", "requirement", status="approved")
        arch = _art(
            "ARCH-001", "architecture", status="approved",
            links=[art_lib.Link(target="REQ-001", role="derives_from")],
        )
        other_arch = _art("ARCH-002", "architecture", status="approved", links=[])
        ddd = _art(
            "DDD-001", "detailed-design", status="approved",
            links=[art_lib.Link(target="ARCH-002", role="specified_by")],
        )
        rows = _ddd_rows(audit_cmd._vertical_analysis([req, arch, other_arch, ddd]))
        assert rows  # still reported


# ── end-to-end (QT-113): dry-run shows the row accounting, exit 0 ────────────


class TestDryRunEndToEnd:
    @staticmethod
    def _fixture(root: Path) -> None:
        # REQ (implemented) + ARCH + implemented STORY, deliberately NO DDD.
        # The single structural-looking row ('no DDD refinement') is stamped
        # ddd-shape → accounting → the gate exits CLEAN.
        _write_art(root, "_specflow/specs/requirements/REQ-001.md",
                   "---\nid: REQ-001\ntitle: T\ntype: requirement\nstatus: implemented\n"
                   "non_functional_category: functional\n"
                   "tags: []\nsuspect: false\nlinks: []\nfingerprint: x\n---\n\n# T\n\n"
                   "## Acceptance Criteria\n- AC one\n")
        _write_art(root, "_specflow/specs/architecture/ARCH-001.md",
                   "---\nid: ARCH-001\ntitle: A\ntype: architecture\nstatus: approved\n"
                   "tags: []\nsuspect: false\n"
                   "links:\n  - {target: REQ-001, role: derives_from}\n"
                   "fingerprint: x\n---\n\n# A\n\n## Component\narch component detail.\n")
        _write_art(root, "_specflow/work/stories/STORY-001.md",
                   "---\nid: STORY-001\ntitle: S\ntype: story\nstatus: implemented\n"
                   "tags: []\nsuspect: false\n"
                   "links:\n  - {target: REQ-001, role: implements}\n"
                   "fingerprint: x\n---\n\n# S\n\n## Acceptance Criteria\n- it works\n")

    def test_dry_run_ddd_shape_row_accounting_exit_zero(
        self, tmp_path, monkeypatch, capsys
    ):
        root = tmp_path / "project"
        self._fixture(root)
        # Silence the schema lens (no schema dir in the fixture) and AUD/CHL
        # side effects — precedent: test_project_audit.py::TestExitCodeParity.
        monkeypatch.setattr(artifact_lint, "check_schema",
                            lambda arts, sd: {"blocking_count": 0, "warning_count": 0})
        monkeypatch.setattr(audit_cmd.art_lib, "create_artifact", lambda *a, **k: {"ok": False})
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts", lambda *a, **k: [])

        rc = audit_cmd.run(root, {"dry_run": True})
        out = capsys.readouterr().out
        assert "no DDD refinement" in out       # the row is printed (truthful)
        assert "accounting" in out.lower()      # and surfaced as non-escalating
        assert rc == 0, f"expected CLEAN (exit 0), got {rc}\n{out}"

    def test_same_fixture_without_story_would_escalate(
        self, tmp_path, monkeypatch, capsys
    ):
        # Gate equivalence: drop the STORY and the concern-less rows escalate
        # (exit 2) — the carve-out is exactly as wide as the DEC predicate.
        root = tmp_path / "project"
        self._fixture(root)
        (root / "_specflow" / "work" / "stories" / "STORY-001.md").unlink()
        monkeypatch.setattr(artifact_lint, "check_schema",
                            lambda arts, sd: {"blocking_count": 0, "warning_count": 0})
        monkeypatch.setattr(audit_cmd.art_lib, "create_artifact", lambda *a, **k: {"ok": False})
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts", lambda *a, **k: [])

        rc = audit_cmd.run(root, {"dry_run": True})
        capsys.readouterr()
        assert rc == 2, f"expected WARNINGS (exit 2), got {rc}"
