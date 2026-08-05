"""Tests for the workflow-tag structural rules (CHL-344 sub-finding #4, A6).

Two surfaces turn the `backfilled` tag from description into assertion:

  - artifact_lint._check_backfilled_links — every artifact tagged `backfilled`
    MUST have ≥1 link in EITHER direction (outbound, or inbound as a link
    target — the adoption-pack anchor ARCH is upstream-less by construction
    yet anchors a chain); a backfilled record describing nothing asserts
    nothing. WARNING-only, never blocking (artifact-lint warns never feed the
    project-audit exit gate).
  - project_audit._backfilled_exemption_lens — ONE deterministic INFO line
    counting backfilled STORYs (approved/implemented/verified) that sit
    OUTSIDE check_coverage's REQ-anchored test-link expectations (the adoption
    shape: derives_from → anchor ARCH with no parent REQ). The implicit
    exemption becomes explicit, counted, reviewable. INFO deliberately;
    omitted when zero (nfr out-of-vocab precedent).

Deliberate omissions pinned here: NO 'deferred' rule — the tag does not exist
anywhere (go.py's 'deferred' is a wave-lock result key; REQ-DEFERRED-* is a
draft-ID slug), and minting a tag for zero consumers violates the D-18 frozen
vocabulary. The chain-coverage tallies (check_coverage's story_chain_coverage
/ approved_story_total / approved_story_covered) are UNTOUCHED — the tests
below pin the emergent exemption's semantics so future drift is caught.
"""

from __future__ import annotations

from pathlib import Path

from specflow.commands import artifact_lint
from specflow.commands import project_audit as audit_cmd
from specflow.lib import artifacts as art_lib


def _art(
    aid: str,
    type_name: str,
    status: str = "implemented",
    tags: list[str] | None = None,
    links: list[art_lib.Link] | None = None,
    body: str = "",
    **frontmatter,
) -> art_lib.Artifact:
    fm = {"id": aid, "type": type_name, "status": status}
    if tags is not None:
        fm["tags"] = tags
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


# ── Link guard (artifact-lint backfilled-links check) ───────────────────────


class TestBackfilledLinkGuard:
    def test_backfilled_artifact_with_no_links_warns(self):
        arts = [_art("STORY-900", "story", tags=["backfilled"])]
        result = artifact_lint._check_backfilled_links(arts)
        assert result["blocking_count"] == 0   # warn-only, never an error
        assert result["warning_count"] == 1
        assert "STORY-900" in result["detail"]
        assert "asserts nothing" in result["detail"]

    def test_backfilled_artifact_with_links_passes(self):
        arts = [_art(
            "STORY-900", "story", tags=["backfilled"],
            links=[art_lib.Link(target="ARCH-001", role="derives_from")],
        )]
        result = artifact_lint._check_backfilled_links(arts)
        assert result["blocking_count"] == 0
        assert result["warning_count"] == 0
        assert "1 backfilled artifact(s)" in result["detail"]

    def test_untagged_artifact_with_no_links_ignored(self):
        # The guard keys on the tag, not on linklessness in general (the
        # links/provenance checks own that surface for other types).
        arts = [_art("STORY-900", "story")]
        result = artifact_lint._check_backfilled_links(arts)
        assert result["warning_count"] == 0

    def test_backfilled_anchor_arch_with_inbound_link_only_passes(self):
        # Direction carve-out: the adoption-pack anchor ARCH is upstream-less
        # BY CONSTRUCTION (skeleton = no parent REQ), but a STORY derives_from
        # it — it anchors a chain, so it asserts something. Warning on it
        # would cry-wolf for every adoption-pack consumer (same mistake the
        # BP/DEC foundational-provenance exemption fixed).
        arts = [
            _art("ARCH-900", "architecture", tags=["backfilled"]),
            _art("STORY-900", "story", tags=["backfilled"],
                 links=[art_lib.Link(target="ARCH-900", role="derives_from")]),
        ]
        result = artifact_lint._check_backfilled_links(arts)
        assert result["warning_count"] == 0

    def test_truly_disconnected_backfilled_artifact_warns(self):
        # No outbound AND no inbound: that is the adoption noise the guard
        # exists to catch.
        arts = [
            _art("ARCH-900", "architecture", tags=["backfilled"]),
            _art("STORY-900", "story", tags=["backfilled"],
                 links=[art_lib.Link(target="ARCH-900", role="derives_from")]),
            _art("STORY-901", "story", tags=["backfilled"]),
        ]
        result = artifact_lint._check_backfilled_links(arts)
        assert result["warning_count"] == 1
        assert "STORY-901" in result["detail"]

    def test_one_warning_per_offending_artifact_sorted(self):
        arts = [
            _art("STORY-902", "story", tags=["backfilled"]),
            _art("ARCH-900", "architecture", tags=["backfilled"]),
            _art("STORY-901", "story", tags=["backfilled"],
                 links=[art_lib.Link(target="REQ-001", role="implements")]),
        ]
        result = artifact_lint._check_backfilled_links(arts)
        assert result["warning_count"] == 2
        assert result["blocking_count"] == 0
        # Deterministic order regardless of discovery order.
        assert result["detail"].index("ARCH-900") < result["detail"].index("STORY-902")

    def test_warn_can_never_block_artifact_lint(self):
        # The exit gate contract: even a fleet of linkless backfilled records
        # keeps blocking_count at 0, so artifact-lint stays exit-0 (warnings).
        arts = [_art(f"STORY-{i:03d}", "story", tags=["backfilled"]) for i in range(5)]
        result = artifact_lint._check_backfilled_links(arts)
        assert result["warning_count"] == 5
        assert result["blocking_count"] == 0

    def test_registered_in_check_names(self):
        assert "backfilled-links" in artifact_lint.CHECK_NAMES

    def test_null_tags_frontmatter_treated_as_untagged(self):
        art = _art("STORY-900", "story")
        art.frontmatter["tags"] = None  # `tags:` with no value in YAML
        result = artifact_lint._check_backfilled_links([art])
        assert result["warning_count"] == 0


# ── Counted exemption bucket (project-audit lens) ────────────────────────────


def _adoption_shape() -> list[art_lib.Artifact]:
    """The adoption shape: a backfilled STORY linking derives_from to an anchor
    ARCH that has NO parent REQ (what `detect orphan-code --adopt` creates)."""
    return [
        _art("ARCH-900", "architecture", status="approved", tags=["backfilled"]),
        _art(
            "STORY-900", "story", status="approved", tags=["backfilled"],
            links=[art_lib.Link(target="ARCH-900", role="derives_from")],
        ),
    ]


def _story622_shape() -> list[art_lib.Artifact]:
    """STORY-622 shape: backfilled but REQ-anchored and fully test-linked."""
    return [
        _art("REQ-037", "requirement", status="implemented"),
        _art("ARCH-026", "architecture", status="approved",
             links=[art_lib.Link(target="REQ-037", role="derives_from")]),
        _art(
            "STORY-622", "story", status="verified", tags=["backfilled"],
            links=[
                art_lib.Link(target="REQ-037", role="implements"),
                art_lib.Link(target="ARCH-026", role="derives_from"),
                art_lib.Link(target="UT-033", role="verified_by"),
            ],
        ),
        _art("UT-033", "unit-test", status="implemented",
             links=[art_lib.Link(target="STORY-622", role="verified_by")]),
        _art("IT-029", "integration-test", status="verified",
             links=[art_lib.Link(target="STORY-622", role="verified_by")]),
        _art("QT-037", "qualification-test", status="verified",
             links=[art_lib.Link(target="STORY-622", role="verified_by")]),
    ]


class TestBackfilledExemptionLens:
    def test_adoption_shape_counted_as_one_info_line(self):
        findings = audit_cmd._backfilled_exemption_lens(_adoption_shape())
        assert len(findings) == 1
        f = findings[0]
        assert f["severity"] == "info"
        assert f["concern"] == "adoption-exemption"
        assert "1 backfilled chain(s) exempt" in f["message"]
        assert "STORY-900" in f["message"]
        assert "output_files" in f["message"]

    def test_story622_shape_emits_no_line(self):
        # REQ-anchored backfill sits INSIDE the expectations — no exemption.
        assert audit_cmd._backfilled_exemption_lens(_story622_shape()) == []

    def test_multiple_exempt_chains_sorted_and_counted(self):
        arts = _adoption_shape() + [
            _art("ARCH-901", "architecture", status="approved", tags=["backfilled"]),
            _art(
                "STORY-800", "story", status="implemented", tags=["backfilled"],
                links=[art_lib.Link(target="ARCH-901", role="derives_from")],
            ),
        ]
        findings = audit_cmd._backfilled_exemption_lens(arts)
        assert len(findings) == 1
        assert "2 backfilled chain(s) exempt" in findings[0]["message"]
        # Sorted IDs for a stable line.
        msg = findings[0]["message"]
        assert msg.index("STORY-800") < msg.index("STORY-900")

    def test_draft_backfilled_story_not_counted(self):
        # Status filter: only approved/implemented/verified backfilled STORYs
        # can sit in the exemption bucket (drafts carry no expectations yet).
        arts = [
            _art("ARCH-900", "architecture", status="approved"),
            _art(
                "STORY-900", "story", status="draft", tags=["backfilled"],
                links=[art_lib.Link(target="ARCH-900", role="derives_from")],
            ),
        ]
        assert audit_cmd._backfilled_exemption_lens(arts) == []

    def test_anchor_to_draft_req_is_outside_expectations(self):
        # A backfilled STORY implements a DRAFT REQ: check_coverage has no
        # test-link expectation for it either, so the bucket counts it.
        arts = [
            _art("REQ-900", "requirement", status="draft"),
            _art(
                "STORY-900", "story", status="approved", tags=["backfilled"],
                links=[art_lib.Link(target="REQ-900", role="implements")],
            ),
        ]
        findings = audit_cmd._backfilled_exemption_lens(arts)
        assert len(findings) == 1
        assert "STORY-900" in findings[0]["message"]

    def test_non_backfilled_unanchored_story_not_counted(self):
        # The bucket keys on the tag: untagged unanchored STORYs are owned by
        # other lenses (completeness/verification), not by this exemption.
        arts = [
            _art("ARCH-900", "architecture", status="approved"),
            _art(
                "STORY-900", "story", status="approved",
                links=[art_lib.Link(target="ARCH-900", role="derives_from")],
            ),
        ]
        assert audit_cmd._backfilled_exemption_lens(arts) == []

    def test_lens_can_only_emit_info_never_drives_exit(self):
        # The hard invariant: no input can make this lens emit a warn, so it
        # cannot drive exit-2 through any concern.
        findings = audit_cmd._backfilled_exemption_lens(_adoption_shape())
        assert all(f["severity"] == "info" for f in findings)
        escalating, accounting = audit_cmd._count_warns(findings)
        assert escalating == 0 and accounting == 0

    def test_lens_wired_into_cross_cutting_analysis(self):
        # Through the REAL pipeline (lenses degrade gracefully on a bare root):
        # the bucket lands under its own concern key with the INFO finding.
        cc = audit_cmd._cross_cutting_analysis(
            _adoption_shape(), Path("/tmp/specflow-a6-bare-root")
        )
        assert "adoption-exemption" in cc
        exempt = cc["adoption-exemption"]
        assert len(exempt) == 1
        assert exempt[0]["severity"] == "info"
        assert "STORY-900" in exempt[0]["message"]

    def test_wiring_omits_bucket_when_zero(self):
        # STORY-622 shape through the real pipeline: no adoption-exemption key
        # at all (omission-when-zero, the nfr out-of-vocab precedent).
        cc = audit_cmd._cross_cutting_analysis(
            _story622_shape(), Path("/tmp/specflow-a6-bare-root")
        )
        assert "adoption-exemption" not in cc


# ── Chain-coverage tallies are UNCHANGED by A6 ──────────────────────────────


class TestChainCoverageTalliesUnchanged:
    def test_exempt_backfilled_story_stays_outside_the_tally(self):
        # The emergent exemption, pinned: an adoption-shape backfilled STORY
        # enters NEITHER the approved-story tally NOR the verification warns.
        r = artifact_lint.check_coverage(_adoption_shape())
        assert r["approved_story_total"] == 0
        assert r["approved_story_covered"] == 0
        assert r["verification_warning_count"] == 0
        assert r["structural_warning_count"] == 0

    def test_story622_shape_fully_covered_in_tally(self):
        r = artifact_lint.check_coverage(_story622_shape())
        assert r["approved_story_total"] == 1
        assert r["approved_story_covered"] == 1
        assert r["verification_warning_count"] == 0
        # The audit header metric derives from the same walk.
        assert audit_cmd._chain_coverage_stats(_story622_shape()) == (1, 1)

    def test_mixed_fleet_tally_counts_only_req_anchored_stories(self):
        arts = _story622_shape() + _adoption_shape()
        r = artifact_lint.check_coverage(arts)
        assert (r["approved_story_covered"], r["approved_story_total"]) == (1, 1)
        assert audit_cmd._chain_coverage_stats(arts) == (1, 1)


# ── Exit-code parity (run level) ─────────────────────────────────────────────


class TestExitCodeParity:
    """A fixture project carrying BOTH A6 shapes — a linkless backfilled
    artifact (artifact-lint warn) and an exempt backfilled chain (audit INFO)
    — exits CLEAN: the warn lives on the artifact-lint surface (never feeds
    the audit gate) and the exemption bucket is INFO-only."""

    @staticmethod
    def _fixture(root: Path) -> None:
        _write_art(root, "_specflow/specs/requirements/REQ-001.md",
                   "---\nid: REQ-001\ntitle: T\ntype: requirement\nstatus: approved\n"
                   "non_functional_category: functional\n"
                   "tags: []\nsuspect: false\nlinks: []\nfingerprint: x\n---\n\n# T\n")
        _write_art(root, "_specflow/specs/architecture/ARCH-001.md",
                   "---\nid: ARCH-001\ntitle: A\ntype: architecture\nstatus: approved\n"
                   "tags: []\nsuspect: false\n"
                   "links:\n  - {target: REQ-001, role: derives_from}\n"
                   "fingerprint: x\n---\n\n# A\n")
        _write_art(root, "_specflow/work/stories/STORY-001.md",
                   "---\nid: STORY-001\ntitle: S\ntype: story\nstatus: implemented\n"
                   "tags: []\nsuspect: false\n"
                   "links:\n  - {target: REQ-001, role: implements}\n"
                   "fingerprint: x\n---\n\n# S\n")
        for prefix, ttype, dirn in (
            ("UT", "unit-test", "specs/unit-tests"),
            ("IT", "integration-test", "specs/integration-tests"),
            ("QT", "qualification-test", "specs/qualification-tests"),
        ):
            _write_art(root, f"_specflow/{dirn}/{prefix}-001.md",
                       f"---\nid: {prefix}-001\ntitle: V\ntype: {ttype}\nstatus: verified\n"
                       "tags: []\nsuspect: false\n"
                       "links:\n  - {target: STORY-001, role: verified_by}\n"
                       "fingerprint: x\n---\n\n# V\n")
        # Adoption shape: anchor ARCH with no parent REQ + backfilled STORY.
        _write_art(root, "_specflow/specs/architecture/ARCH-900.md",
                   "---\nid: ARCH-900\ntitle: Adopted\ntype: architecture\nstatus: approved\n"
                   "tags:\n  - backfilled\nsuspect: false\nlinks: []\nfingerprint: x\n---\n\n# A\n")
        _write_art(root, "_specflow/work/stories/STORY-900.md",
                   "---\nid: STORY-900\ntitle: Adopted chain\ntype: story\nstatus: approved\n"
                   "tags:\n  - backfilled\nsuspect: false\n"
                   "links:\n  - {target: ARCH-900, role: derives_from}\n"
                   "fingerprint: x\n---\n\n# S\n")
        # A LINKLESS backfilled artifact — drives the artifact-lint warn.
        _write_art(root, "_specflow/work/stories/STORY-901.md",
                   "---\nid: STORY-901\ntitle: Linkless backfill\ntype: story\nstatus: draft\n"
                   "tags:\n  - backfilled\nsuspect: false\nlinks: []\nfingerprint: x\n---\n\n# S\n")

    def test_linkless_backfilled_artifact_warns_but_never_blocks(self, tmp_path):
        root = tmp_path / "project"
        self._fixture(root)
        arts = art_lib.discover_artifacts(root)
        result = artifact_lint._check_backfilled_links(arts)
        assert result["warning_count"] == 1      # STORY-901 only
        assert "STORY-901" in result["detail"]
        assert result["blocking_count"] == 0     # can never drive artifact-lint exit 1

    def test_exempt_chain_counted_and_audit_exits_clean(self, tmp_path, monkeypatch, capsys):
        root = tmp_path / "project"
        self._fixture(root)
        monkeypatch.setattr(artifact_lint, "check_schema",
                            lambda arts, sd: {"blocking_count": 0, "warning_count": 0})
        monkeypatch.setattr(audit_cmd, "_horizontal_analysis", lambda arts: {})
        monkeypatch.setattr(audit_cmd, "_vertical_analysis", lambda arts: [])
        monkeypatch.setattr(audit_cmd.art_lib, "create_artifact", lambda *a, **k: {"ok": False})
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts", lambda *a, **k: [])

        rc = audit_cmd.run(root, {"quick": False})
        out = capsys.readouterr().out
        assert rc == 0, f"expected CLEAN (exit 0), got {rc}\n{out}"
        # The exemption line is an INFO FINDING: it lands in the report (and
        # the findings cache / AUD body), not in the stdout summary counts.
        reports = sorted((root / ".specflow" / "audits").glob("*/report.md"))
        assert reports, "expected an audit report to be written"
        report = reports[-1].read_text(encoding="utf-8")
        assert "1 backfilled chain(s) exempt" in report
        assert "STORY-900" in report
        assert "### adoption-exemption" in report

    def test_dry_run_parity_with_exempt_bucket(self, tmp_path, monkeypatch):
        root = tmp_path / "project"
        self._fixture(root)
        monkeypatch.setattr(artifact_lint, "check_schema",
                            lambda arts, sd: {"blocking_count": 0, "warning_count": 0})
        monkeypatch.setattr(audit_cmd, "_horizontal_analysis", lambda arts: {})
        monkeypatch.setattr(audit_cmd, "_vertical_analysis", lambda arts: [])
        monkeypatch.setattr(audit_cmd.art_lib, "create_artifact", lambda *a, **k: {"ok": False})
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts", lambda *a, **k: [])

        rc_dry = audit_cmd.run(root, {"quick": False, "dry_run": True})
        rc_full = audit_cmd.run(root, {"quick": False})
        assert rc_dry == rc_full == 0

    def test_story622_shape_fixture_prints_no_exemption_line(self, tmp_path, monkeypatch, capsys):
        # A fully REQ-anchored, fully test-linked backfilled STORY (STORY-622
        # shape) passes clean with NO exemption line — omission when zero.
        root = tmp_path / "project"
        _write_art(root, "_specflow/specs/requirements/REQ-037.md",
                   "---\nid: REQ-037\ntitle: T\ntype: requirement\nstatus: implemented\n"
                   "non_functional_category: functional\n"
                   "tags: []\nsuspect: false\nlinks: []\nfingerprint: x\n---\n\n# T\n")
        _write_art(root, "_specflow/specs/architecture/ARCH-026.md",
                   "---\nid: ARCH-026\ntitle: A\ntype: architecture\nstatus: approved\n"
                   "tags: []\nsuspect: false\n"
                   "links:\n  - {target: REQ-037, role: derives_from}\n"
                   "fingerprint: x\n---\n\n# A\n")
        _write_art(root, "_specflow/work/stories/STORY-622.md",
                   "---\nid: STORY-622\ntitle: S\ntype: story\nstatus: verified\n"
                   "tags:\n  - backfilled\nsuspect: false\n"
                   "links:\n  - {target: REQ-037, role: implements}\n"
                   "  - {target: ARCH-026, role: derives_from}\n"
                   "fingerprint: x\n---\n\n# S\n")
        for prefix, ttype, dirn in (
            ("UT", "unit-test", "specs/unit-tests"),
            ("IT", "integration-test", "specs/integration-tests"),
            ("QT", "qualification-test", "specs/qualification-tests"),
        ):
            _write_art(root, f"_specflow/{dirn}/{prefix}-037.md",
                       f"---\nid: {prefix}-037\ntitle: V\ntype: {ttype}\nstatus: verified\n"
                       "tags: []\nsuspect: false\n"
                       "links:\n  - {target: STORY-622, role: verified_by}\n"
                       "fingerprint: x\n---\n\n# V\n")
        monkeypatch.setattr(artifact_lint, "check_schema",
                            lambda arts, sd: {"blocking_count": 0, "warning_count": 0})
        monkeypatch.setattr(audit_cmd, "_horizontal_analysis", lambda arts: {})
        monkeypatch.setattr(audit_cmd, "_vertical_analysis", lambda arts: [])
        monkeypatch.setattr(audit_cmd.art_lib, "create_artifact", lambda *a, **k: {"ok": False})
        monkeypatch.setattr(audit_cmd.chl_lib, "create_chl_artifacts", lambda *a, **k: [])

        rc = audit_cmd.run(root, {"quick": False})
        assert rc == 0
        capsys.readouterr()
        reports = sorted((root / ".specflow" / "audits").glob("*/report.md"))
        assert reports, "expected an audit report to be written"
        report = reports[-1].read_text(encoding="utf-8")
        assert "backfilled chain(s) exempt" not in report
        assert "adoption-exemption" not in report
        # And the link guard is silent too — STORY-622 carries links.
        arts = art_lib.discover_artifacts(root)
        assert artifact_lint._check_backfilled_links(arts)["warning_count"] == 0
