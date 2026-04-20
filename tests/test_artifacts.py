"""Tests for specflow.lib.artifacts — parsing, fingerprinting, link traversal."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

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
