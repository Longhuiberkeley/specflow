"""Tests for rebuild_index fingerprint-repair and fileless-quarantine safety.

Covers the v1.13 deferred item closed at the root: rebuild recomputes empty
fingerprints from the body (correct-by-definition) and quarantines fileless
index entries instead of dropping them into the void.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.commands import artifact_lint as lint_cmd
from specflow.lib import artifacts as art_lib

_STD_FLOW = {"draft": [], "approved": ["draft"], "implemented": ["approved"], "verified": ["implemented"]}


def _scaffold(tmp: Path) -> Path:
    """Minimal project with a requirement schema so create_artifact works."""
    root = tmp / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)

    schema = {
        "type": "requirement",
        "prefix": "REQ",
        "allowed_status": dict(_STD_FLOW),
        "allowed_link_roles": ["implements", "verifies"],
    }
    (schema_dir / "requirement.yaml").write_text(yaml.dump(schema), encoding="utf-8")

    config = {
        "project": {"name": "test-project", "created": "2026-01-01"},
        "artifact_types": ["requirement"],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "executing", "history": []}), encoding="utf-8"
    )

    (root / "_specflow" / "specs" / "requirements").mkdir(parents=True, exist_ok=True)
    return root


def _req_index(root: Path) -> Path:
    return root / "_specflow" / "specs" / "requirements" / "_index.yaml"


def _strip_frontmatter_fingerprint(md_path: Path) -> str:
    """Remove the fingerprint line from an artifact's frontmatter in place."""
    original_fp = ""
    content = md_path.read_text(encoding="utf-8")
    for line in content.splitlines():
        if line.startswith("fingerprint:"):
            original_fp = line.split(":", 1)[1].strip()
            content = content.replace(line + "\n", "")
            break
    md_path.write_text(content, encoding="utf-8")
    return original_fp


def _set_frontmatter_fingerprint(md_path: Path, value: str) -> None:
    """Overwrite the fingerprint in an artifact's frontmatter in place."""
    art = art_lib.parse_artifact(md_path)
    assert art is not None
    art.frontmatter["fingerprint"] = value
    art_lib._rewrite_frontmatter(md_path, art.frontmatter, art.body)


class TestRebuildRepairsEmptyFingerprint:
    def test_empty_fingerprint_recomputed_from_body(self, tmp_path: Path):
        root = _scaffold(tmp_path)
        result = art_lib.create_artifact(root, "requirement", title="Has Body", body="real body content")
        assert result["ok"]
        art_id = result["id"]
        md_path = Path(result["path"])

        # The recomputed value is, by definition, the hash of the parsed body
        # (what drift/suspect detection uses as ground truth).
        parsed = art_lib.parse_artifact(md_path)
        assert parsed is not None
        expected = art_lib.compute_fingerprint(parsed.body)

        # Simulate the pre-fix state: fingerprint present in the index but
        # EMPTY in the .md frontmatter (the ~38-artifact drift shape).
        _strip_frontmatter_fingerprint(md_path)

        out = art_lib.rebuild_index(root)

        index = art_lib._read_index(_req_index(root))
        assert index["artifacts"][art_id]["fingerprint"] == expected
        assert out["repaired"] == 1

    def test_repair_is_idempotent_and_writes_frontmatter(self, tmp_path: Path):
        root = _scaffold(tmp_path)
        result = art_lib.create_artifact(root, "requirement", title="Idem", body="content")
        art_id = result["id"]
        md_path = Path(result["path"])
        _strip_frontmatter_fingerprint(md_path)

        first = art_lib.rebuild_index(root)
        assert first["repaired"] == 1

        # The repair persisted the fingerprint back into the .md frontmatter ...
        art = art_lib.parse_artifact(md_path)
        assert art is not None
        assert art.fingerprint == art_lib.compute_fingerprint(art.body)

        # ... so a second rebuild finds nothing to repair (idempotent).
        second = art_lib.rebuild_index(root)
        assert second["repaired"] == 0


class TestRebuildRepairsEmptyBodyHashFingerprint:
    """The empty-body hash signature (_EMPTY_BODY_FINGERPRINT) is a pre-v1.13
    bug's tell-tale: it was stored for some non-empty auto-generated artifacts
    (live case: DEC-059). It can never be a legitimate fingerprint of real
    content, so rebuild recomputes it on sight."""

    def test_empty_body_hash_recomputed_from_nonempty_body(self, tmp_path: Path):
        root = _scaffold(tmp_path)
        result = art_lib.create_artifact(
            root, "requirement", title="Was Buggy", body="non-empty body content"
        )
        assert result["ok"]
        art_id = result["id"]
        md_path = Path(result["path"])

        # The legitimate fingerprint of this non-empty body — what rebuild must
        # converge to and what drift/suspect detection uses as ground truth.
        parsed = art_lib.parse_artifact(md_path)
        assert parsed is not None
        expected = art_lib.compute_fingerprint(parsed.body)

        # The empty-body hash signature is exactly compute_fingerprint(""). Lock
        # the module constant to that value (doctrine), and confirm this body's
        # real hash differs (sanity: the body is non-empty).
        empty_hash = art_lib.compute_fingerprint("")
        assert art_lib._EMPTY_BODY_FINGERPRINT == empty_hash
        assert expected != empty_hash

        # Simulate the pre-v1.13 bug: store the empty-body hash for a non-empty
        # body in the .md frontmatter.
        _set_frontmatter_fingerprint(md_path, empty_hash)

        out = art_lib.rebuild_index(root)

        # Recomputed to the real body hash, in both index ...
        assert out["repaired"] == 1
        index = art_lib._read_index(_req_index(root))
        assert index["artifacts"][art_id]["fingerprint"] == expected
        # ... and persisted into the .md frontmatter.
        repaired = art_lib.parse_artifact(md_path)
        assert repaired is not None
        assert repaired.fingerprint == expected

        # Idempotent: a second rebuild finds nothing to repair.
        again = art_lib.rebuild_index(root)
        assert again["repaired"] == 0


class TestRebuildLeavesOtherWrongFingerprints:
    """Guard: a present-but-wrong fingerprint whose value is NOT the empty-body
    hash must NOT be touched by rebuild — that is suspect detection's job.
    Silently "fixing" it would destroy the drift signal."""

    def test_wrong_but_nonempty_fingerprint_untouched(self, tmp_path: Path):
        root = _scaffold(tmp_path)
        result = art_lib.create_artifact(
            root, "requirement", title="Suspect", body="real content here"
        )
        assert result["ok"]
        art_id = result["id"]
        md_path = Path(result["path"])

        # A wrong-but-non-empty fingerprint that is neither empty/missing nor
        # the empty-body hash. Suspect-detection territory.
        wrong = "sha256:deadbeefdead"
        assert wrong != art_lib.compute_fingerprint("")
        _set_frontmatter_fingerprint(md_path, wrong)

        out = art_lib.rebuild_index(root)

        # Rebuild neither repairs nor rewrites; it propagates the stored value.
        assert out["repaired"] == 0
        art = art_lib.parse_artifact(md_path)
        assert art is not None
        assert art.fingerprint == wrong
        index = art_lib._read_index(_req_index(root))
        assert index["artifacts"][art_id]["fingerprint"] == wrong


class TestRebuildQuarantinesFileless:
    def test_fileless_entry_quarantined_not_deleted(self, tmp_path: Path):
        root = _scaffold(tmp_path)
        result = art_lib.create_artifact(
            root, "requirement", title="Ghost", body="b", tags=["t1"],
        )
        assert result["ok"]
        art_id = result["id"]
        original_fp = result["fingerprint"]

        # The entry exists in the index; remove its .md to make it fileless.
        md_path = Path(result["path"])
        md_path.unlink()
        assert not md_path.exists()

        art_lib.rebuild_index(root)

        target_dir = root / "_specflow" / "specs" / "requirements"
        quarantine_path = target_dir / "_index.quarantine.yaml"

        # Preserved in quarantine with a timestamp and last-known data.
        assert quarantine_path.exists()
        q = yaml.safe_load(quarantine_path.read_text(encoding="utf-8"))
        assert art_id in q
        entry = q[art_id]
        assert entry["id"] == art_id
        assert entry["title"] == "Ghost"
        assert entry["status"] == "draft"
        assert entry["fingerprint"] == original_fp
        assert entry["tags"] == ["t1"]
        assert entry["quarantined_at"]
        assert entry["quarantined_at"].endswith("Z")

        # Absent from the live index, but NOT deleted — data survives in quarantine.
        index = art_lib._read_index(_req_index(root))
        assert art_id not in index.get("artifacts", {})

    def test_repeated_rebuild_does_not_duplicate_quarantine(self, tmp_path: Path):
        root = _scaffold(tmp_path)
        result = art_lib.create_artifact(root, "requirement", title="Ghost2", body="b2")
        art_id = result["id"]
        Path(result["path"]).unlink()

        art_lib.rebuild_index(root)
        art_lib.rebuild_index(root)

        quarantine_path = root / "_specflow" / "specs" / "requirements" / "_index.quarantine.yaml"
        q = yaml.safe_load(quarantine_path.read_text(encoding="utf-8"))
        # Exactly one entry for the fileless ID — no duplication on re-run.
        assert list(q.keys()).count(art_id) == 1
        assert len(q) == 1


class TestCreateArtifactFingerprint:
    def test_fingerprint_written_to_frontmatter_and_index(self, tmp_path: Path):
        root = _scaffold(tmp_path)
        result = art_lib.create_artifact(root, "requirement", title="New", body="body text")
        assert result["ok"]

        # Frontmatter carries a non-empty fingerprint ...
        art = art_lib.parse_artifact(Path(result["path"]))
        assert art is not None
        assert art.fingerprint.startswith("sha256:")
        assert art.fingerprint == result["fingerprint"]

        # ... and so does the index.
        index = art_lib._read_index(_req_index(root))
        assert index["artifacts"][result["id"]]["fingerprint"] == result["fingerprint"]


class TestNextIdRecompute:
    def test_next_id_recomputed_from_artifacts(self, tmp_path: Path):
        root = _scaffold(tmp_path)
        # Create REQ-001 then REQ-002, then delete REQ-001's .md so the highest
        # remaining number is 2 -> next_id must be 3 after rebuild.
        r1 = art_lib.create_artifact(root, "requirement", title="One", body="b")
        r2 = art_lib.create_artifact(root, "requirement", title="Two", body="b")
        assert r1["id"] == "REQ-001"
        assert r2["id"] == "REQ-002"

        Path(r1["path"]).unlink()

        art_lib.rebuild_index(root)

        index = art_lib._read_index(_req_index(root))
        assert index["next_id"] == 3
        assert "REQ-001" not in index["artifacts"]
        assert "REQ-002" in index["artifacts"]

    def test_draft_id_hash_digits_do_not_advance_next_id(self, tmp_path: Path):
        root = _scaffold(tmp_path)
        created = art_lib.create_artifact(root, "requirement", title="Numeric", body="b")
        assert created["id"] == "REQ-001"

        # Feature-branch draft IDs end with a short hash. Digits in that hash are
        # not allocated numeric IDs and must not influence the sequence.
        art_lib.create_artifact(
            root,
            "requirement",
            title="Draft",
            body="b",
            artifact_id="REQ-DEFERRED-d684",
        )

        art_lib.rebuild_index(root)

        index = art_lib._read_index(_req_index(root))
        assert index["next_id"] == 2
        assert "REQ-DEFERRED-d684" in index["artifacts"]

    def test_artifact_lint_fix_uses_canonical_next_id(self, tmp_path: Path):
        root = _scaffold(tmp_path)
        r1 = art_lib.create_artifact(root, "requirement", title="One", body="b")
        r2 = art_lib.create_artifact(root, "requirement", title="Two", body="b")
        assert r1["id"] == "REQ-001"
        assert r2["id"] == "REQ-002"
        Path(r1["path"]).unlink()

        lint_cmd._auto_fix(root)

        index = art_lib._read_index(_req_index(root))
        assert index["next_id"] == 3
