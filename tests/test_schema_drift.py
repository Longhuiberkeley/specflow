"""Tests for safe schema-drift behavior in `specflow refresh --schemas` and
the matching `specflow brief` health nag.

Covers:
1. classify_schemas — new / identical / changed classification.
2. refresh --schemas dry-run reports changed without writing.
3. refresh --schemas writes missing but preserves changed + prints an actionable hint.
4. refresh --schemas --force replaces changed schemas.
5. brief health nags fire on drift but stay silent when healthy (no false positives).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from specflow.commands import brief as brief_cmd
from specflow.commands import refresh as refresh_cmd

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_SCHEMAS = REPO_ROOT / "src" / "specflow" / "templates" / "schemas"


def _make_project(root: Path, name: str = "drift-project") -> Path:
    (root / ".specflow" / "schema").mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    config = {"project": {"name": name, "created": "2026-08-01"},
              "artifact_types": [], "active_packs": []}
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")
    state = {"current": "idle", "history": []}
    (root / ".specflow" / "state.yaml").write_text(yaml.dump(state), encoding="utf-8")
    return root


def _install_base_schema(root: Path, stem: str, *, mutate: bool = False) -> None:
    """Copy one base schema into the project; optionally mutate its bytes."""
    src = BASE_SCHEMAS / f"{stem}.yaml"
    dst = root / ".specflow" / "schema" / f"{stem}.yaml"
    shutil.copy2(str(src), str(dst))
    if mutate:
        dst.write_text(dst.read_text(encoding="utf-8") + "\n# local drift\n", encoding="utf-8")


def _install_all_identical(root: Path) -> None:
    """Copy every base schema unchanged → all classified identical."""
    dst = root / ".specflow" / "schema"
    dst.mkdir(parents=True, exist_ok=True)
    for f in sorted(BASE_SCHEMAS.glob("*.yaml")):
        shutil.copy2(str(f), str(dst / f.name))


def _mutated_stem() -> str:
    """Pick a base schema stem we know exists (requirement.yaml)."""
    return "requirement"


# ── 1. classify_schemas ──────────────────────────────────────────────────────

class TestClassifySchemas:

    def test_missing_schema_is_new(self, tmp_path: Path):
        root = _make_project(tmp_path / "p")  # empty schema dir
        new, identical, changed = refresh_cmd.classify_schemas(root)
        assert "requirement" in new
        assert "story" in new
        assert identical == []
        assert changed == []

    def test_identical_and_changed_and_new(self, tmp_path: Path):
        root = _make_project(tmp_path / "p")
        _install_base_schema(root, "requirement", mutate=True)   # changed
        _install_base_schema(root, "story")                      # identical
        # defect.yaml left missing -> new
        new, identical, changed = refresh_cmd.classify_schemas(root)
        assert "requirement" in changed
        assert "story" in identical
        assert "defect" in new
        assert set(new) & set(changed) == set()
        assert set(new) & set(identical) == set()
        assert set(changed) & set(identical) == set()

    def test_pack_added_schema_never_classified(self, tmp_path: Path):
        """A schema that lives only in .specflow/schema (pack-owned) is ignored."""
        root = _make_project(tmp_path / "p")
        (root / ".specflow" / "schema" / "loop.yaml").write_text("# pack schema\n")
        new, identical, changed = refresh_cmd.classify_schemas(root)
        assert "loop" not in new and "loop" not in changed


# ── 2/3/4. refresh --schemas behavior ────────────────────────────────────────

class TestRefreshSchemas:

    def test_dry_run_reports_changed_without_writing(self, tmp_path: Path, capsys):
        root = _make_project(tmp_path / "p")
        _install_base_schema(root, "requirement", mutate=True)   # changed
        # story.yaml missing -> new; nothing written on dry-run
        rc = refresh_cmd.run(root, {"schemas": True, "dry_run": True,
                                    "no_skills": True, "no_context": True})
        out = capsys.readouterr().out
        assert rc == 0
        assert "schemas" in out
        assert "changed: requirement" in out
        assert "new:" in out and "story" in out  # story.yaml missing -> listed as new
        # dry-run must not have installed the missing schema
        assert not (root / ".specflow" / "schema" / "story.yaml").exists()

    def test_normal_writes_missing_preserves_changed_with_hint(self, tmp_path: Path, capsys):
        root = _make_project(tmp_path / "p")
        _install_base_schema(root, "requirement", mutate=True)   # drifted copy
        story_dst = root / ".specflow" / "schema" / "story.yaml"
        assert not story_dst.exists()

        rc = refresh_cmd.run(root, {"schemas": True, "no_skills": True, "no_context": True})
        out = capsys.readouterr().out
        assert rc == 0

        # missing schema installed
        assert story_dst.exists()
        # drifted schema preserved (not overwritten)
        assert "local drift" in (root / ".specflow" / "schema" / "requirement.yaml").read_text()
        # actionable hint printed
        assert "preserved (changed): requirement" in out
        assert "--force" in out

    def test_force_replaces_changed(self, tmp_path: Path, capsys):
        root = _make_project(tmp_path / "p")
        _install_base_schema(root, "requirement", mutate=True)
        rc = refresh_cmd.run(root, {"schemas": True, "force": True,
                                    "no_skills": True, "no_context": True})
        out = capsys.readouterr().out
        assert rc == 0
        text = (root / ".specflow" / "schema" / "requirement.yaml").read_text(encoding="utf-8")
        assert "local drift" not in text
        assert "replaced: requirement" in out
        assert "preserved" not in out


# ── 5. brief health nag ──────────────────────────────────────────────────────

class TestBriefHealthNag:

    def _nags(self, root: Path) -> list[str]:
        config = yaml.safe_load((root / ".specflow" / "config.yaml").read_text())
        return brief_cmd._health_nags(root, config, [], None)

    def test_nag_fires_on_drift(self, tmp_path: Path):
        root = _make_project(tmp_path / "p")
        _install_base_schema(root, _mutated_stem(), mutate=True)
        nags = self._nags(root)
        assert any("schema(s) diverged" in n for n in nags)
        assert any("--force" in n for n in nags)

    def test_no_nag_when_all_identical(self, tmp_path: Path):
        root = _make_project(tmp_path / "p")
        _install_all_identical(root)
        nags = self._nags(root)
        assert not any("schema" in n for n in nags)

    def test_no_nag_without_schema_dir(self, tmp_path: Path):
        root = _make_project(tmp_path / "p")
        nags = self._nags(root)
        assert not any("schema" in n for n in nags)
