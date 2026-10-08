"""`specflow rebuild-index --type` resolves aliases and rejects unknown types.

Before this guard an unknown or prefix-spelled type (``--type REQ``, ``--type
bogus``) fell through ``TYPE_TO_DIR.get`` and printed "✓ Rebuilt index ... 0
artifact(s)" with exit 0 (F-069).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.commands import rebuild_index as rebuild_cmd
from specflow.lib import artifacts as art_lib

_STD_FLOW = {"draft": [], "approved": ["draft"], "implemented": ["approved"], "verified": ["implemented"]}


def _scaffold(tmp: Path) -> Path:
    root = tmp / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (schema_dir / "requirement.yaml").write_text(
        yaml.dump({"type": "requirement", "prefix": "REQ", "allowed_status": dict(_STD_FLOW),
                   "allowed_link_roles": ["implements"]}),
        encoding="utf-8",
    )
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump({"project": {"name": "t", "created": "2026-01-01"},
                   "artifact_types": ["requirement"], "active_packs": []}),
        encoding="utf-8",
    )
    (root / "_specflow" / "specs" / "requirements").mkdir(parents=True, exist_ok=True)
    return root


class TestRebuildIndexTypeGuard:
    def test_unknown_type_is_rejected_nonzero(self, tmp_path: Path, capsys):
        root = _scaffold(tmp_path)
        rc = rebuild_cmd.run(root, {"type": "bogus"})
        out = capsys.readouterr().out
        assert rc == 1
        assert "Unknown artifact type 'bogus'" in out
        assert "requirement" in out  # valid-type list is shown
        assert "✓" not in out

    def test_near_miss_gets_suggestion(self, tmp_path: Path, capsys):
        root = _scaffold(tmp_path)
        rc = rebuild_cmd.run(root, {"type": "requirment"})
        out = capsys.readouterr().out
        assert rc == 1
        assert "Did you mean: requirement" in out

    def test_prefix_spelling_resolves_and_rebuilds(self, tmp_path: Path, capsys):
        root = _scaffold(tmp_path)
        created = art_lib.create_artifact(root=root, artifact_type="requirement", title="R")
        assert created["ok"]
        index = root / "_specflow" / "specs" / "requirements" / "_index.yaml"
        index.unlink()

        rc = rebuild_cmd.run(root, {"type": "REQ"})
        out = capsys.readouterr().out
        assert rc == 0
        assert "type=requirement" in out
        assert "1 artifact(s)" in out
        assert index.exists()
        rebuilt = yaml.safe_load(index.read_text(encoding="utf-8"))
        assert created["id"] in rebuilt["artifacts"]

    def test_canonical_type_unchanged(self, tmp_path: Path, capsys):
        root = _scaffold(tmp_path)
        rc = rebuild_cmd.run(root, {"type": "requirement"})
        assert rc == 0
        assert "type=requirement" in capsys.readouterr().out

    def test_capitalised_canonical_name_is_accepted(self, tmp_path: Path, capsys):
        # normalize_type is case-sensitive for canonical names; the command
        # falls back to the lowercased spelling before rejecting.
        root = _scaffold(tmp_path)
        rc = rebuild_cmd.run(root, {"type": "Requirement"})
        out = capsys.readouterr().out
        assert rc == 0, out
        assert "type=requirement" in out
