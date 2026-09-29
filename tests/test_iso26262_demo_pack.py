"""STORY-695 AC2: iso26262-demo is honestly a test fixture.

Its clause ids are placeholders (DEMO-1..DEMO-5) that match neither edition of
ISO 26262, it no longer ships a hazard schema that duplicates the core
optional `hazard` type, and its wording says so.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.commands import pack_validate as pv
from specflow.lib import scaffold as scaffold_lib
from specflow.lib import standards as standards_lib

PACKS_DIR = Path(__file__).parent.parent / "src" / "specflow" / "packs"
PACK = PACKS_DIR / "iso26262-demo"


def test_clauses_renamed_to_demo_ids():
    std = yaml.safe_load((PACK / "standards" / "iso26262-demo.yaml").read_text(encoding="utf-8"))
    assert [c["id"] for c in std["clauses"]] == [f"DEMO-{n}" for n in range(1, 6)]
    assert not any("ISO26262-" in c["id"] for c in std["clauses"])


def test_duplicate_hazard_schema_is_gone():
    assert not (PACK / "schemas" / "hazard.yaml").exists()
    manifest = yaml.safe_load((PACK / "pack.yaml").read_text(encoding="utf-8"))
    assert not manifest.get("adds_artifact_types")
    assert not manifest.get("adds_directories")
    # The optional core type it used to duplicate is still there.
    optional = PACKS_DIR.parent / "templates" / "schemas" / "optional" / "hazard.yaml"
    assert optional.exists()


def test_wording_labels_it_a_fixture():
    manifest = yaml.safe_load((PACK / "pack.yaml").read_text(encoding="utf-8"))
    assert "NOT a compliance pack" in manifest["description"] or "test fixture" in manifest["description"].lower()
    readme = (PACK / "README.md").read_text(encoding="utf-8")
    low = readme.lower()
    assert "test fixture" in low
    assert "not a compliance pack" in low
    assert "DEMO-1" in readme
    assert "--with-types hazard" in readme
    assert "specflow-pack-author" in readme


def test_pack_still_validates_and_installs(tmp_path: Path, capsys):
    assert pv.run(tmp_path, {"pack_dir": str(PACK)}) == 0, capsys.readouterr().out
    root = tmp_path / "proj"
    (root / ".specflow" / "schema").mkdir(parents=True)
    (root / ".specflow" / "standards").mkdir(parents=True)
    (root / ".specflow" / "config.yaml").write_text(
        "project: {name: p, created: '2026-01-01'}\nartifact_types: []\nactive_packs: []\n", encoding="utf-8")
    (root / ".specflow" / "state.yaml").write_text("current: idle\nhistory: []\n", encoding="utf-8")
    result = scaffold_lib.apply_pack(root, "iso26262-demo", PACKS_DIR)
    assert result["ok"], result
    ids = {c["id"] for s in standards_lib.load_standards(root) for c in s.get("clauses", [])}
    assert {"DEMO-1", "DEMO-5"} <= ids
