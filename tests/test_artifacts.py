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

    def test_warns_on_erased_fingerprint(self, tmp_path: Path, caplog):
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

        assert "fingerprint erased" in caplog.text
        assert art_id in caplog.text
