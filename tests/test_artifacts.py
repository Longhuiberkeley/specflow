"""Tests for specflow.lib.artifacts — parsing, fingerprinting, link traversal."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from specflow.lib import artifacts as art_lib


def _write_artifact(
    tmp: Path,
    rel_path: str,
    frontmatter: str,
    body: str = "Some body text",
) -> Path:
    path = tmp / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"---\n{frontmatter}\n---\n\n{body}\n"
    path.write_text(content, encoding="utf-8")
    return path


def _scaffold_project(tmp: Path) -> Path:
    root = tmp / "project"
    (root / ".specflow" / "schema").mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    (root / "_specflow" / "specs" / "requirements").mkdir(parents=True, exist_ok=True)
    (root / "_specflow" / "specs" / "architecture").mkdir(parents=True, exist_ok=True)
    (root / "_specflow" / "specs" / "detailed-design").mkdir(parents=True, exist_ok=True)
    (root / "_specflow" / "specs" / "unit-tests").mkdir(parents=True, exist_ok=True)
    (root / "_specflow" / "specs" / "integration-tests").mkdir(parents=True, exist_ok=True)
    (root / "_specflow" / "specs" / "qualification-tests").mkdir(parents=True, exist_ok=True)
    (root / "_specflow" / "work" / "stories").mkdir(parents=True, exist_ok=True)
    return root


class TestComputeFingerprint:
    def test_deterministic(self):
        fp1 = art_lib.compute_fingerprint("hello world")
        fp2 = art_lib.compute_fingerprint("hello world")
        assert fp1 == fp2

    def test_format(self):
        fp = art_lib.compute_fingerprint("test content")
        assert fp.startswith("sha256:")
        assert len(fp) == 19  # "sha256:" + 12 hex chars

    def test_different_content(self):
        fp1 = art_lib.compute_fingerprint("aaa")
        fp2 = art_lib.compute_fingerprint("bbb")
        assert fp1 != fp2

    def test_whitespace_stripped(self):
        fp1 = art_lib.compute_fingerprint("  hello  ")
        fp2 = art_lib.compute_fingerprint("hello")
        assert fp1 == fp2


class TestParseArtifact:
    def test_valid_artifact(self, tmp_path: Path):
        path = _write_artifact(
            tmp_path,
            "_specflow/specs/requirements/REQ-001.md",
            "id: REQ-001\ntitle: Test\ntype: requirement\nstatus: approved",
            "# Test\n\nBody text",
        )
        art = art_lib.parse_artifact(path)
        assert art is not None
        assert art.id == "REQ-001"
        assert art.title == "Test"
        assert art.type == "requirement"
        assert art.status == "approved"

    def test_missing_frontmatter(self, tmp_path: Path):
        path = tmp_path / "bad.md"
        path.write_text("Just some text without frontmatter", encoding="utf-8")
        art = art_lib.parse_artifact(path)
        assert art is None

    def test_links_parsed(self, tmp_path: Path):
        path = _write_artifact(
            tmp_path,
            "_specflow/specs/requirements/REQ-001.md",
            textwrap.dedent("""\
                id: REQ-001
                title: Test
                type: requirement
                status: approved
                links:
                  - target: ARCH-001
                    role: refined_by
                  - target: ISO26262-3.7
                    role: complies_with
            """),
        )
        art = art_lib.parse_artifact(path)
        assert art is not None
        assert len(art.links) == 2
        assert art.links[0].target == "ARCH-001"
        assert art.links[0].role == "refined_by"
        assert art.links[1].target == "ISO26262-3.7"
        assert art.links[1].role == "complies_with"


class TestFindOrphans:
    def test_no_orphans(self):
        a1 = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001"},
            body="",
            links=[art_lib.Link(target="ARCH-001", role="refined_by")],
        )
        a2 = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "ARCH-001"},
            body="",
            links=[art_lib.Link(target="REQ-001", role="derives_from")],
        )
        orphans = art_lib.find_orphans([a1, a2])
        assert len(orphans) == 0

    def test_orphan_detected(self):
        a1 = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001"},
            body="",
            links=[],
        )
        orphans = art_lib.find_orphans([a1])
        assert len(orphans) == 1
        assert orphans[0].id == "REQ-001"

    def test_referenced_but_not_linking(self):
        a1 = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001"},
            body="",
            links=[],
        )
        a2 = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "ARCH-001"},
            body="",
            links=[art_lib.Link(target="REQ-001", role="derives_from")],
        )
        orphans = art_lib.find_orphans([a1, a2])
        assert len(orphans) == 0

    def test_research_provenance_not_orphan(self):
        # EXPT/LOOP/FIND store provenance in frontmatter (loop, competition,
        # source_loop), not links[]. A properly-traced research subgraph must
        # not be miscounted as orphan on autoresearch-heavy projects.
        comp = art_lib.Artifact(
            path=Path("comp.md"),
            frontmatter={"id": "COMP-001", "type": "competition"},
            body="", links=[],
        )
        loop = art_lib.Artifact(
            path=Path("loop.md"),
            frontmatter={"id": "LOOP-001", "type": "loop", "competition": "COMP-001"},
            body="", links=[],
        )
        expt = art_lib.Artifact(
            path=Path("expt.md"),
            frontmatter={"id": "EXPT-001", "type": "experiment", "loop": "LOOP-001"},
            body="", links=[],
        )
        find = art_lib.Artifact(
            path=Path("find.md"),
            frontmatter={
                "id": "FIND-001", "type": "finding",
                "competition": "COMP-001", "source_loop": "LOOP-001",
            },
            body="", links=[],
        )
        orphans = art_lib.find_orphans([comp, loop, expt, find])
        assert orphans == []
        # Provenance is recognized even though none of these have links[].
        assert art_lib.has_provenance(expt)
        assert art_lib.has_provenance(loop)
        assert art_lib.has_provenance(find)
        assert art_lib.has_provenance(comp)  # competition root

    def test_research_artifact_without_provenance_is_orphan(self):
        # An EXPT with neither links nor a loop field is genuinely orphan.
        expt = art_lib.Artifact(
            path=Path("expt.md"),
            frontmatter={"id": "EXPT-009", "type": "experiment"},
            body="", links=[],
        )
        assert not art_lib.has_provenance(expt)
        assert art_lib.find_orphans([expt]) == [expt]

    def test_foundational_types_exempt_from_provenance(self):
        # RC1: best-practice and decision artifacts are foundational doctrine —
        # upstream-less by design (other artifacts derive FROM them) — so an
        # unlinked BP/DEC is not orphan-provenance. has_provenance returns True
        # the same way it does for a competition root. Mirrors the research-type
        # exemption; genuine orphan detection for non-foundational types is
        # exercised in test_project_audit.
        bp = art_lib.Artifact(
            path=Path("bp.md"),
            frontmatter={"id": "BP-001", "type": "best-practice"},
            body="", links=[],
        )
        dec = art_lib.Artifact(
            path=Path("dec.md"),
            frontmatter={"id": "DEC-001", "type": "decision"},
            body="", links=[],
        )
        assert art_lib.has_provenance(bp)
        assert art_lib.has_provenance(dec)


class TestFindMissingVPairs:
    def test_missing_verification(self):
        a1 = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001", "type": "requirement"},
            body="",
            links=[],
        )
        missing = art_lib.find_missing_v_pairs([a1])
        assert len(missing) == 1
        assert missing[0][0].id == "REQ-001"

    def test_has_verification(self):
        a1 = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001", "type": "requirement"},
            body="",
            links=[],
        )
        a2 = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "QT-001", "type": "qualification-test"},
            body="",
            links=[art_lib.Link(target="REQ-001", role="verified_by")],
        )
        missing = art_lib.find_missing_v_pairs([a1, a2])
        assert len(missing) == 0


class TestTraceChain:
    def test_story_implements_shows_upstream(self):
        a1 = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001", "type": "requirement", "title": "Req", "status": "approved"},
            body="",
            links=[],
        )
        a2 = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "STORY-001", "type": "story", "title": "Story", "status": "implemented"},
            body="",
            links=[art_lib.Link(target="REQ-001", role="implements")],
        )
        index = art_lib.build_id_index([a1, a2])
        chain = art_lib.trace_chain("STORY-001", index, direction="upstream")
        assert len(chain["upstream"]) == 1
        assert chain["upstream"][0]["id"] == "REQ-001"
        assert chain["upstream"][0]["role"] == "implements"

    def test_story_guided_by_and_specified_by_upstream(self):
        arch = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "ARCH-001", "type": "architecture", "title": "Arch", "status": "approved"},
            body="",
            links=[],
        )
        ddd = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "DDD-001", "type": "detailed-design", "title": "DDD", "status": "approved"},
            body="",
            links=[],
        )
        story = art_lib.Artifact(
            path=Path("c.md"),
            frontmatter={"id": "STORY-001", "type": "story", "title": "Story", "status": "implemented"},
            body="",
            links=[
                art_lib.Link(target="ARCH-001", role="guided_by"),
                art_lib.Link(target="DDD-001", role="specified_by"),
            ],
        )
        index = art_lib.build_id_index([arch, ddd, story])
        chain = art_lib.trace_chain("STORY-001", index, direction="upstream")
        upstream_ids = {n["id"] for n in chain["upstream"]}
        assert upstream_ids == {"ARCH-001", "DDD-001"}

    def test_test_verified_by_points_upstream_to_story(self):
        story = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "STORY-001", "type": "story", "title": "Story", "status": "implemented"},
            body="",
            links=[],
        )
        ut = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "UT-001", "type": "unit-test", "title": "UT", "status": "verified"},
            body="",
            links=[art_lib.Link(target="STORY-001", role="verified_by")],
        )
        index = art_lib.build_id_index([story, ut])
        chain = art_lib.trace_chain("UT-001", index, direction="upstream")
        assert [n["id"] for n in chain["upstream"]] == ["STORY-001"]

    def test_story_verified_by_test_is_not_upstream(self):
        # A story's own verified_by edge points at its verifier — downstream.
        story = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "STORY-001", "type": "story", "title": "Story", "status": "implemented"},
            body="",
            links=[art_lib.Link(target="UT-001", role="verified_by")],
        )
        ut = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "UT-001", "type": "unit-test", "title": "UT", "status": "verified"},
            body="",
            links=[],
        )
        index = art_lib.build_id_index([story, ut])
        chain = art_lib.trace_chain("STORY-001", index, direction="upstream")
        assert len(chain["upstream"]) == 0
        # The verifier still renders downstream via its own incoming link.
        chain_both = art_lib.trace_chain("STORY-001", index, direction="downstream")
        assert [n["id"] for n in chain_both["downstream"]] == ["UT-001"]

    def test_implements_not_upstream_from_non_story(self):
        # Role alone must not decide direction: a non-story source using
        # implements is not treated as a work→spec edge.
        a1 = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001", "type": "requirement", "title": "Req", "status": "approved"},
            body="",
            links=[art_lib.Link(target="REQ-002", role="implements")],
        )
        a2 = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "REQ-002", "type": "requirement", "title": "Req2", "status": "approved"},
            body="",
            links=[],
        )
        index = art_lib.build_id_index([a1, a2])
        chain = art_lib.trace_chain("REQ-001", index, direction="upstream")
        assert len(chain["upstream"]) == 0

    def test_research_parent_roles_upstream(self):
        comp = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "COMP-001", "type": "competition", "title": "Comp", "status": "active"},
            body="",
            links=[],
        )
        loop = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "LOOP-001", "type": "loop", "title": "Loop", "status": "draft"},
            body="",
            links=[art_lib.Link(target="COMP-001", role="operates_on")],
        )
        expt = art_lib.Artifact(
            path=Path("c.md"),
            frontmatter={"id": "EXPT-001", "type": "experiment", "title": "Expt", "status": "kept"},
            body="",
            links=[art_lib.Link(target="LOOP-001", role="belongs_to")],
        )
        index = art_lib.build_id_index([comp, loop, expt])
        chain = art_lib.trace_chain("EXPT-001", index, direction="upstream")
        upstream_ids = {n["id"] for n in chain["upstream"]}
        # Multi-hop: LOOP-001 directly, COMP-001 via LOOP's operates_on edge.
        assert upstream_ids == {"LOOP-001", "COMP-001"}

    def test_annotation_role_does_not_extend_chain_depth(self):
        req = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001", "type": "requirement", "title": "Req", "status": "approved"},
            body="",
            links=[],
        )
        review = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "REVIEW-001", "type": "review", "title": "Review", "status": "open"},
            body="",
            links=[art_lib.Link(target="REQ-001", role="refers_to")],
        )
        index = art_lib.build_id_index([req, review])
        path = art_lib.compute_chain_depth("REQ-001", index)
        assert path == ["REQ-001"]

    def test_verified_by_edge_extends_chain_depth(self):
        req = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001", "type": "requirement", "title": "Req", "status": "approved"},
            body="",
            links=[],
        )
        story = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "STORY-001", "type": "story", "title": "Story", "status": "implemented"},
            body="",
            links=[art_lib.Link(target="REQ-001", role="implements")],
        )
        ut = art_lib.Artifact(
            path=Path("c.md"),
            frontmatter={"id": "UT-001", "type": "unit-test", "title": "UT", "status": "verified"},
            body="",
            links=[art_lib.Link(target="STORY-001", role="verified_by")],
        )
        index = art_lib.build_id_index([req, story, ut])
        path = art_lib.compute_chain_depth("REQ-001", index)
        assert path == ["REQ-001", "STORY-001", "UT-001"]

    def test_canonical_refined_by_on_req_is_downstream(self):
        # Canonical shape: REQ names the ARCH that refines it — the ARCH is
        # downstream, NOT upstream (v1.14.2 fix; dogfood REQ-005 shape).
        req = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001", "type": "requirement", "title": "Req", "status": "approved"},
            body="",
            links=[art_lib.Link(target="ARCH-001", role="refined_by")],
        )
        arch = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "ARCH-001", "type": "architecture", "title": "Arch", "status": "approved"},
            body="",
            links=[],
        )
        index = art_lib.build_id_index([req, arch])
        chain = art_lib.trace_chain("REQ-001", index, direction="upstream")
        assert len(chain["upstream"]) == 0
        chain = art_lib.trace_chain("REQ-001", index, direction="downstream")
        assert [n["id"] for n in chain["downstream"]] == ["ARCH-001"]
        assert chain["downstream"][0]["role"] == "refined_by"

    def test_legacy_refined_by_on_ddd_stays_upstream(self):
        # Legacy shape: DDD points at the ARCH it refines — upstream
        # (dogfood DDD-001/DDD-016 shape).
        ddd = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "DDD-001", "type": "detailed-design", "title": "DDD", "status": "approved"},
            body="",
            links=[art_lib.Link(target="ARCH-001", role="refined_by")],
        )
        arch = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "ARCH-001", "type": "architecture", "title": "Arch", "status": "approved"},
            body="",
            links=[],
        )
        index = art_lib.build_id_index([ddd, arch])
        chain = art_lib.trace_chain("DDD-001", index, direction="upstream")
        assert [n["id"] for n in chain["upstream"]] == ["ARCH-001"]

    def test_run_implements_req_upstream(self):
        # ops RUN schema allows implements → REQ/ARCH: a deployment must trace
        # to its governing spec (v1.14.2 fix).
        run = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "RUN-001", "type": "run", "title": "Run", "status": "deployed"},
            body="",
            links=[art_lib.Link(target="REQ-001", role="implements")],
        )
        req = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "REQ-001", "type": "requirement", "title": "Req", "status": "approved"},
            body="",
            links=[],
        )
        index = art_lib.build_id_index([run, req])
        chain = art_lib.trace_chain("RUN-001", index, direction="upstream")
        assert [n["id"] for n in chain["upstream"]] == ["REQ-001"]

    def test_spec_owned_verified_by_renders_downstream(self):
        # Spec-side edge: REQ names its qualifying test (dogfood REQ-019 →
        # QT-020 shape) — the verifier renders downstream.
        req = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001", "type": "requirement", "title": "Req", "status": "approved"},
            body="",
            links=[art_lib.Link(target="QT-001", role="verified_by")],
        )
        qt = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "QT-001", "type": "qualification-test", "title": "QT", "status": "verified"},
            body="",
            links=[],
        )
        index = art_lib.build_id_index([req, qt])
        chain = art_lib.trace_chain("REQ-001", index, direction="upstream")
        assert len(chain["upstream"]) == 0
        chain = art_lib.trace_chain("REQ-001", index, direction="downstream")
        assert [n["id"] for n in chain["downstream"]] == ["QT-001"]


    def test_upstream_and_downstream(self):
        a1 = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001", "type": "requirement", "title": "Req", "status": "approved"},
            body="",
            links=[art_lib.Link(target="ISO26262-3.7", role="complies_with")],
        )
        a2 = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "ARCH-001", "type": "architecture", "title": "Arch", "status": "approved"},
            body="",
            links=[art_lib.Link(target="REQ-001", role="derives_from")],
        )
        a3 = art_lib.Artifact(
            path=Path("c.md"),
            frontmatter={"id": "QT-001", "type": "qualification-test", "title": "Test", "status": "verified"},
            body="",
            links=[art_lib.Link(target="REQ-001", role="verified_by")],
        )
        index = art_lib.build_id_index([a1, a2, a3])
        chain = art_lib.trace_chain("REQ-001", index)

        assert len(chain["upstream"]) == 1
        assert chain["upstream"][0]["id"] == "ISO26262-3.7"
        assert chain["upstream"][0]["role"] == "complies_with"
        assert len(chain["downstream"]) == 2
        downstream_ids = [n["id"] for n in chain["downstream"]]
        assert "ARCH-001" in downstream_ids
        assert "QT-001" in downstream_ids

    def test_no_links(self):
        a1 = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001", "type": "requirement", "title": "Req", "status": "draft"},
            body="",
            links=[],
        )
        index = art_lib.build_id_index([a1])
        chain = art_lib.trace_chain("REQ-001", index)
        assert len(chain["upstream"]) == 0
        assert len(chain["downstream"]) == 0

    def test_direction_upstream_only(self):
        a1 = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001", "type": "requirement", "title": "Req", "status": "approved"},
            body="",
            links=[art_lib.Link(target="ISO-1", role="complies_with")],
        )
        a2 = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "ARCH-001", "type": "architecture", "title": "Arch", "status": "draft"},
            body="",
            links=[art_lib.Link(target="REQ-001", role="derives_from")],
        )
        index = art_lib.build_id_index([a1, a2])
        chain = art_lib.trace_chain("REQ-001", index, direction="upstream")
        assert len(chain["upstream"]) == 1
        assert chain["upstream"][0]["id"] == "ISO-1"
        assert len(chain["downstream"]) == 0

    def test_direction_downstream_only(self):
        a1 = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001", "type": "requirement", "title": "Req", "status": "approved"},
            body="",
            links=[art_lib.Link(target="ISO-1", role="complies_with")],
        )
        a2 = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "ARCH-001", "type": "architecture", "title": "Arch", "status": "draft"},
            body="",
            links=[art_lib.Link(target="REQ-001", role="derives_from")],
        )
        index = art_lib.build_id_index([a1, a2])
        chain = art_lib.trace_chain("REQ-001", index, direction="downstream")
        assert len(chain["upstream"]) == 0
        assert len(chain["downstream"]) == 1
        assert chain["downstream"][0]["id"] == "ARCH-001"

    def test_cycle_does_not_loop(self):
        a1 = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001", "type": "requirement", "title": "Req", "status": "approved"},
            body="",
            links=[art_lib.Link(target="REQ-002", role="derives_from")],
        )
        a2 = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "REQ-002", "type": "requirement", "title": "Req2", "status": "approved"},
            body="",
            links=[art_lib.Link(target="REQ-001", role="derives_from")],
        )
        index = art_lib.build_id_index([a1, a2])
        chain = art_lib.trace_chain("REQ-001", index, direction="upstream")
        upstream_ids = [n["id"] for n in chain["upstream"]]
        assert "REQ-002" in upstream_ids
        assert upstream_ids.count("REQ-002") == 1

    def test_multi_hop_upstream(self):
        a1 = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001", "type": "requirement", "title": "Req", "status": "approved"},
            body="",
            links=[art_lib.Link(target="STD-1", role="complies_with")],
        )
        a2 = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "STD-1", "type": "standard", "title": "Std", "status": "approved"},
            body="",
            links=[art_lib.Link(target="STD-0", role="derives_from")],
        )
        index = art_lib.build_id_index([a1, a2])
        chain = art_lib.trace_chain("REQ-001", index, direction="upstream")
        upstream_ids = [n["id"] for n in chain["upstream"]]
        assert "STD-1" in upstream_ids
        assert "STD-0" in upstream_ids

    def test_missing_target_fallback(self):
        a1 = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001", "type": "requirement", "title": "Req", "status": "approved"},
            body="",
            links=[art_lib.Link(target="NONEXISTENT-999", role="complies_with")],
        )
        index = art_lib.build_id_index([a1])
        chain = art_lib.trace_chain("REQ-001", index, direction="upstream")
        assert len(chain["upstream"]) == 1
        assert chain["upstream"][0]["id"] == "NONEXISTENT-999"
        assert chain["upstream"][0]["type"] == "standard"
        assert chain["upstream"][0]["title"] == "NONEXISTENT-999"


class TestComputeChainDepth:
    def test_deep_chain(self):
        a1 = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001", "type": "requirement"},
            body="",
            links=[],
        )
        a2 = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "ARCH-001", "type": "architecture"},
            body="",
            links=[art_lib.Link(target="REQ-001", role="derives_from")],
        )
        a3 = art_lib.Artifact(
            path=Path("c.md"),
            frontmatter={"id": "STORY-001", "type": "story"},
            body="",
            links=[art_lib.Link(target="REQ-001", role="implements")],
        )
        index = art_lib.build_id_index([a1, a2, a3])
        path = art_lib.compute_chain_depth("REQ-001", index)
        assert len(path) == 2

    def test_no_downstream(self):
        a1 = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001", "type": "requirement"},
            body="",
            links=[],
        )
        index = art_lib.build_id_index([a1])
        path = art_lib.compute_chain_depth("REQ-001", index)
        assert path == ["REQ-001"]

    def test_branching_returns_deepest(self):
        a1 = art_lib.Artifact(
            path=Path("a.md"),
            frontmatter={"id": "REQ-001", "type": "requirement"},
            body="",
            links=[],
        )
        a2 = art_lib.Artifact(
            path=Path("b.md"),
            frontmatter={"id": "ARCH-001", "type": "architecture"},
            body="",
            links=[art_lib.Link(target="REQ-001", role="derives_from")],
        )
        a3 = art_lib.Artifact(
            path=Path("c.md"),
            frontmatter={"id": "DDD-001", "type": "detailed-design"},
            body="",
            links=[art_lib.Link(target="ARCH-001", role="derives_from")],
        )
        a4 = art_lib.Artifact(
            path=Path("d.md"),
            frontmatter={"id": "STORY-001", "type": "story"},
            body="",
            links=[art_lib.Link(target="REQ-001", role="implements")],
        )
        index = art_lib.build_id_index([a1, a2, a3, a4])
        path = art_lib.compute_chain_depth("REQ-001", index)
        assert len(path) == 3
        assert path[0] == "REQ-001"
        assert path[-1] == "DDD-001"


class TestIdUtilities:
    def test_get_prefix(self):
        assert art_lib.get_prefix_from_id("REQ-001") == "REQ"
        assert art_lib.get_prefix_from_id("ARCH-001.1") == "ARCH"

    def test_get_base_id(self):
        assert art_lib.get_base_id("REQ-001.1.2") == "REQ-001"
        assert art_lib.get_base_id("REQ-001") == "REQ-001"

    def test_dot_notation_depth(self):
        assert art_lib.check_dot_notation_depth("REQ-001") == 1
        assert art_lib.check_dot_notation_depth("REQ-001.1") == 2
        assert art_lib.check_dot_notation_depth("REQ-001.1.1") == 3


class TestNormalizeType:
    def test_canonical_passthrough(self):
        assert art_lib.normalize_type("requirement") == "requirement"
        assert art_lib.normalize_type("defect") == "defect"

    def test_prefix_case_insensitive(self):
        assert art_lib.normalize_type("REQ") == "requirement"
        assert art_lib.normalize_type("req") == "requirement"
        assert art_lib.normalize_type("Req") == "requirement"
        assert art_lib.normalize_type("DEF") == "defect"

    def test_every_alias_resolves_to_canonical(self):
        for alias, canonical in art_lib.TYPE_ALIASES.items():
            assert art_lib.normalize_type(alias) == canonical, alias

    def test_aliases_are_case_insensitive(self):
        # Aliases route through the prefix check (every core alias's uppercase
        # is a registered prefix), but the function must be case-insensitive
        # regardless of which branch resolves it.
        assert art_lib.normalize_type("DEC") == "decision"
        assert art_lib.normalize_type("Dec") == "decision"
        assert art_lib.normalize_type("BP") == "best-practice"
        assert art_lib.normalize_type("CHL") == "challenge"

    def test_unknown_passthrough_untouched(self):
        # Pack-added and freeform types must pass through unchanged.
        assert art_lib.normalize_type("bogus") == "bogus"
        assert art_lib.normalize_type("some-pack-type") == "some-pack-type"

    def test_alias_dict_values_are_real_core_types(self):
        # Integrity: every alias target is a real core type. (Pack-only targets
        # like experiment/finding/competition/loop/run/monitor and the
        # non-existent "prevention" are deliberately excluded.)
        for canonical in art_lib.TYPE_ALIASES.values():
            assert canonical in art_lib.TYPE_TO_DIR, canonical


class TestInitialStatus:
    def test_single_root_returned(self):
        # defect -> open (the real bug: 'draft' was wrong here)
        defect_schema = {
            "allowed_status": {
                "open": [], "investigating": ["open"],
                "fixing": ["investigating"], "closed": ["fixing"],
            }
        }
        assert art_lib.initial_status(defect_schema) == "open"

    def test_requirement_root_is_draft(self):
        req_schema = {
            "allowed_status": {
                "draft": [], "approved": ["draft"], "implemented": ["approved"],
            }
        }
        assert art_lib.initial_status(req_schema) == "draft"

    def test_multiple_roots_returns_none(self):
        # experiment.yaml: four outcome-roots (kept/discarded/crashed/no_op)
        expt_schema = {
            "allowed_status": {"kept": [], "discarded": [], "crashed": [], "no_op": []}
        }
        assert art_lib.initial_status(expt_schema) is None

    def test_no_roots_returns_none(self):
        # Every status has a predecessor -> no root.
        schema = {"allowed_status": {"b": ["a"], "c": ["b"]}}
        assert art_lib.initial_status(schema) is None

    def test_missing_allowed_status_returns_none(self):
        assert art_lib.initial_status({}) is None

    def test_non_dict_allowed_status_returns_none(self):
        assert art_lib.initial_status({"allowed_status": ["open", "closed"]}) is None


_STD_FLOW = {"draft": [], "approved": ["draft"], "implemented": ["approved"], "verified": ["implemented"]}


def _scaffold_full_project(tmp: Path) -> Path:
    root = tmp / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)

    for art_type, prefix in [("requirement", "REQ"), ("architecture", "ARCH"), ("story", "STORY")]:
        schema = {
            "type": art_type,
            "prefix": prefix,
            "allowed_status": dict(_STD_FLOW),
            "allowed_link_roles": ["implements", "verifies"],
        }
        (schema_dir / f"{art_type}.yaml").write_text(yaml.dump(schema), encoding="utf-8")

    config = {
        "project": {"name": "test-project", "created": "2026-01-01"},
        "artifact_types": ["requirement", "architecture", "story"],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "executing", "history": []}), encoding="utf-8"
    )

    for subdir in [
        "_specflow/specs/requirements", "_specflow/specs/architecture",
        "_specflow/work/stories",
    ]:
        (root / subdir).mkdir(parents=True, exist_ok=True)

    return root


class TestCreateArtifactFingerprint:
    def test_fingerprint_in_frontmatter(self, tmp_path: Path):
        root = _scaffold_full_project(tmp_path)
        result = art_lib.create_artifact(root, "requirement", title="Test Req", body="some body")
        assert result["ok"]

        art = art_lib.parse_artifact(Path(result["path"]))
        assert art is not None
        assert art.fingerprint == result["fingerprint"]
        assert art.fingerprint.startswith("sha256:")

    def test_fingerprint_survives_rebuild(self, tmp_path: Path):
        root = _scaffold_full_project(tmp_path)
        result = art_lib.create_artifact(root, "requirement", title="Test", body="content")
        original_fp = result["fingerprint"]

        art_lib.rebuild_index(root)

        index = art_lib._read_index(root / "_specflow" / "specs" / "requirements" / "_index.yaml")
        assert index["artifacts"][result["id"]]["fingerprint"] == original_fp


class TestUpdateBodyOverride:
    """W1.1 — ``specflow update --body`` replaces the whole body and the
    fingerprint is recomputed from the new body."""

    def _create(self, root: Path, body: str = "original body") -> str:
        result = art_lib.create_artifact(
            root, "requirement", title="T", body=body, status="draft"
        )
        assert result["ok"]
        return result["id"]

    def _read(self, root: Path, art_id: str) -> art_lib.Artifact:
        return art_lib.parse_artifact(art_lib.resolve_link_target(root, art_id))

    def test_body_override_replaces_body(self, tmp_path: Path):
        root = _scaffold_full_project(tmp_path)
        art_id = self._create(root)
        res = art_lib.update_artifact(root=root, artifact_id=art_id, body="brand new body")
        assert res["ok"]
        art = self._read(root, art_id)
        assert art.body == "brand new body"
        assert "original body" not in art.body

    def test_body_override_recomputes_fingerprint(self, tmp_path: Path):
        root = _scaffold_full_project(tmp_path)
        art_id = self._create(root)
        before = self._read(root, art_id).fingerprint
        art_lib.update_artifact(root=root, artifact_id=art_id, body="different content")
        after = self._read(root, art_id)
        assert after.fingerprint != before
        assert after.fingerprint == art_lib.compute_fingerprint("different content")

    def test_update_without_body_preserves_body(self, tmp_path: Path):
        root = _scaffold_full_project(tmp_path)
        art_id = self._create(root, body="keep me")
        res = art_lib.update_artifact(root=root, artifact_id=art_id, priority="high")
        assert res["ok"]
        art = self._read(root, art_id)
        assert "keep me" in art.body


class TestUpdateRejectsUnknownStatus:
    """W1.2 — ``update`` rejects a status not in the type's ``allowed_status``
    (closes the silent raw-write hole) and suggests the nearest valid status."""

    def _create(self, root: Path) -> str:
        result = art_lib.create_artifact(
            root, "requirement", title="T", body="b", status="draft"
        )
        assert result["ok"]
        return result["id"]

    def test_unknown_status_rejected_loudly(self, tmp_path: Path):
        root = _scaffold_full_project(tmp_path)
        art_id = self._create(root)
        res = art_lib.update_artifact(root=root, artifact_id=art_id, status="resolved")
        assert not res["ok"]
        assert "Invalid status" in res["error"]

    def test_unknown_status_not_written(self, tmp_path: Path):
        root = _scaffold_full_project(tmp_path)
        art_id = self._create(root)
        art_lib.update_artifact(root=root, artifact_id=art_id, status="resolved")
        art = art_lib.parse_artifact(art_lib.resolve_link_target(root, art_id))
        assert art.status == "draft"  # unchanged, not silently overwritten

    def test_typo_status_suggests_closest(self, tmp_path: Path):
        root = _scaffold_full_project(tmp_path)
        art_id = self._create(root)
        res = art_lib.update_artifact(root=root, artifact_id=art_id, status="approvd")
        assert not res["ok"]
        assert "approved" in res["error"]

    def test_legal_transition_still_works(self, tmp_path: Path):
        root = _scaffold_full_project(tmp_path)
        art_id = self._create(root)
        res = art_lib.update_artifact(root=root, artifact_id=art_id, status="approved")
        assert res["ok"]


class TestRebuildIndexSafety:
    def test_warns_on_dropped_artifacts(self, tmp_path: Path, caplog):
        import logging
        root = _scaffold_full_project(tmp_path)
        result = art_lib.create_artifact(root, "requirement", title="To Drop", body="body")
        art_id = result["id"]

        md_path = Path(result["path"])
        md_path.unlink()
        assert not md_path.exists()

        with caplog.at_level(logging.WARNING):
            art_lib.rebuild_index(root)

        assert art_id in caplog.text
        assert "dropped" in caplog.text

    def test_warns_and_repairs_empty_fingerprint(self, tmp_path: Path, caplog):
        # When the frontmatter fingerprint is empty but the body is non-empty,
        # rebuild recomputes it (correct-by-definition — the fingerprint IS the
        # body hash) and warns naming the repaired ID. The pre-v1.13 behavior
        # propagated the empty fingerprint and only warned about "erased".
        import logging
        root = _scaffold_full_project(tmp_path)
        result = art_lib.create_artifact(root, "requirement", title="Has FP", body="body")
        art_id = result["id"]
        original_fp = result["fingerprint"]

        md_path = Path(result["path"])
        content = md_path.read_text(encoding="utf-8")
        content = content.replace(f"fingerprint: {original_fp}\n", "")
        md_path.write_text(content, encoding="utf-8")

        with caplog.at_level(logging.WARNING):
            art_lib.rebuild_index(root)

        assert "repaired" in caplog.text
        assert art_id in caplog.text
        index = art_lib._read_index(root / "_specflow" / "specs" / "requirements" / "_index.yaml")
        assert index["artifacts"][art_id]["fingerprint"] == original_fp
