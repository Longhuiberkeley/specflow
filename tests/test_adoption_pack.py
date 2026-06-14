"""Adoption pack install + context-injection tests.

Mirrors the autoresearch pack tests (tests/test_autoresearch_pack.py) but
checks the adoption pack's distinct contract: it reuses the core artifact
model (no new types, no new directories, no schemas) and ships exactly one
skill (`specflow-adopt`) plus an AGENTS.md routing snippet.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from specflow.lib import scaffold as scaffold_lib

PACKS_DIR = Path(__file__).parent.parent / "src" / "specflow" / "packs"
ADOPT_SKILL = "specflow-adopt"
REFERENCE_FILES = (
    "as-built-baseline-protocol.md",
    "backfill-extraction-checklist.md",
    "conflict-resolution-protocol.md",
    "incremental-adoption-protocol.md",
)


@pytest.fixture
def fresh_project(tmp_path: Path) -> Path:
    """Minimal project dir with .claude/ marker so platform detection works."""
    root = tmp_path / "fresh-project"
    root.mkdir()
    (root / ".claude").mkdir()
    (root / ".specflow" / "schema").mkdir(parents=True)
    (root / ".specflow" / "standards").mkdir(parents=True)
    config = {
        "project": {"name": "fresh-project", "created": "2026-01-01"},
        "artifact_types": [],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump(config), encoding="utf-8"
    )
    state = {"current": "idle", "history": []}
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump(state), encoding="utf-8"
    )
    return root


# ── 1. Pack manifest contract ──────────────────────────────────────────────

class TestAdoptionManifest:
    """Adoption reuses the core model: no new types, no new dirs, no schemas."""

    def test_manifest_declares_no_types_or_dirs(self):
        manifest = yaml.safe_load(
            (PACKS_DIR / "adoption" / "pack.yaml").read_text(encoding="utf-8")
        )
        assert manifest["name"] == "adoption"
        assert manifest.get("adds_artifact_types") == []
        assert manifest.get("adds_directories") == []
        assert manifest.get("adds_skills") == [ADOPT_SKILL]
        assert manifest.get("context_snippet"), "context_snippet must be present"

    def test_pack_has_no_schemas_dir(self):
        # Adoption deliberately adds no new artifact types → no schemas.
        assert not (PACKS_DIR / "adoption" / "schemas").exists()


# ── 2. Pack install ────────────────────────────────────────────────────────

class TestAdoptionPackInstall:

    def test_apply_returns_ok_with_no_new_types(self, fresh_project: Path):
        result = scaffold_lib.apply_pack(fresh_project, "adoption", PACKS_DIR)
        assert result["ok"]
        assert result["pack"] == "adoption"
        assert result["types_added"] == [], "adoption must add no artifact types"
        assert result["standards_added"] == [], "adoption ships no standards"

    def test_skill_installed_with_references(self, fresh_project: Path):
        result = scaffold_lib.apply_pack(fresh_project, "adoption", PACKS_DIR)
        assert result["ok"]
        assert ADOPT_SKILL in result.get("skills_added", [])

        skill_dir = fresh_project / ".claude" / "skills" / ADOPT_SKILL
        assert skill_dir.is_dir()
        assert (skill_dir / "SKILL.md").exists()

        refs = skill_dir / "references"
        for name in REFERENCE_FILES:
            assert (refs / name).exists(), f"reference {name} not installed"

    def test_no_new_spec_directories_created(self, fresh_project: Path):
        # adds_directories is [] — apply_pack must not create any _specflow/ dirs.
        specflow_dir = fresh_project / "_specflow"
        before = {p for p in specflow_dir.rglob("*") if p.is_dir()} if specflow_dir.exists() else set()
        scaffold_lib.apply_pack(fresh_project, "adoption", PACKS_DIR)
        after = {p for p in specflow_dir.rglob("*") if p.is_dir()} if specflow_dir.exists() else set()
        new_dirs = after - before
        assert not new_dirs, (
            f"adoption must add no _specflow/ artifact dirs, but created: {new_dirs}"
        )

    def test_reinstall_preserves_edited_skill(self, fresh_project: Path):
        result1 = scaffold_lib.apply_pack(fresh_project, "adoption", PACKS_DIR)
        assert result1["ok"]
        assert ADOPT_SKILL in result1["skills_added"]

        skill_file = (
            fresh_project / ".claude" / "skills" / ADOPT_SKILL / "SKILL.md"
        )
        original = skill_file.read_text(encoding="utf-8")
        edited = original.replace("SpecFlow Adopt", "MY CUSTOM ADOPT TITLE")
        skill_file.write_text(edited, encoding="utf-8")

        result2 = scaffold_lib.apply_pack(fresh_project, "adoption", PACKS_DIR)
        assert result2["ok"]
        assert result2.get("skills_added") == [], "reinstall must not re-add skills"

        after = skill_file.read_text(encoding="utf-8")
        assert "MY CUSTOM ADOPT TITLE" in after
        assert after == edited, "user edits must survive reinstall byte-for-byte"


# ── 3. Context injection ───────────────────────────────────────────────────

class TestAdoptionContextInjection:

    def test_apply_returns_context_snippet(self, fresh_project: Path):
        result = scaffold_lib.apply_pack(fresh_project, "adoption", PACKS_DIR)
        assert result["ok"]
        snippet = result["context_snippet"]
        assert snippet
        assert "adoption" in snippet.lower()
        assert "/specflow-adopt" in snippet

    def test_inject_creates_sentinel_block(self, fresh_project: Path):
        agents_md = fresh_project / "AGENTS.md"
        agents_md.write_text("# Existing content\n\nSome text.\n", encoding="utf-8")

        result = scaffold_lib.apply_pack(fresh_project, "adoption", PACKS_DIR)
        snippet = result["context_snippet"]

        modified = scaffold_lib.inject_pack_context(
            fresh_project, "adoption", snippet
        )
        assert modified

        content = agents_md.read_text(encoding="utf-8")
        assert "# Existing content" in content
        assert "<!-- pack:adoption context" in content
        assert "Adoption Pack" in content

    def test_inject_is_idempotent(self, fresh_project: Path):
        agents_md = fresh_project / "AGENTS.md"
        agents_md.write_text("# Content\n", encoding="utf-8")

        result = scaffold_lib.apply_pack(fresh_project, "adoption", PACKS_DIR)
        snippet = result["context_snippet"]

        modified1 = scaffold_lib.inject_pack_context(
            fresh_project, "adoption", snippet
        )
        modified2 = scaffold_lib.inject_pack_context(
            fresh_project, "adoption", snippet
        )
        assert modified1
        assert not modified2, "second injection should be a no-op"

        content = agents_md.read_text(encoding="utf-8")
        assert content.count("<!-- pack:adoption context") == 1


# ── 4. Coexists with other packs (multi-preset) ───────────────────────────

class TestAdoptionMultiPreset:

    def test_adoption_and_autoresearch_both_install(self, fresh_project: Path):
        agents_md = fresh_project / "AGENTS.md"
        agents_md.write_text("# Content\n", encoding="utf-8")

        for pack_name in ("adoption", "tldr-communication"):
            result = scaffold_lib.apply_pack(fresh_project, pack_name, PACKS_DIR)
            assert result["ok"]
            snippet = result["context_snippet"]
            if snippet:
                scaffold_lib.inject_pack_context(
                    fresh_project, pack_name, snippet, "claude-code"
                )

        content = agents_md.read_text(encoding="utf-8")
        assert "<!-- pack:adoption context" in content
        assert "<!-- pack:tldr-communication context" in content
        assert "# Content" in content


# ── 5. D-20 content contract: code-linking model + skeleton-first ──────────

class TestAdoptionD20Content:
    """The skill text must reflect D-20: ARCH-per-component code-linking,
    STORY reserved for forward action, skeleton-first strategy, and the
    `specflow adopt status` completeness view."""

    @pytest.fixture
    def skill_text(self) -> str:
        return (PACKS_DIR / "adoption" / "skills" / "specflow-adopt" / "SKILL.md").read_text(
            encoding="utf-8"
        )

    @pytest.fixture
    def checklist_text(self) -> str:
        return (PACKS_DIR / "adoption" / "skills" / "specflow-adopt" /
                "references" / "backfill-extraction-checklist.md").read_text(
            encoding="utf-8"
        )

    def test_skill_publishes_arch_per_component_guidance(self, skill_text):
        assert "ARCH per component" in skill_text
        assert "output_files" in skill_text
        # Globs are the code-linking vehicle; ensure the word appears.
        assert "glob" in skill_text.lower()

    def test_skill_forbids_backfilled_story(self, skill_text):
        # The skill must say STORY is not backfilled / reserved for forward action.
        # Look for the explicit "NOT" + STORY phrasing.
        lower = skill_text.lower()
        assert "not backfilled" in lower or ("reserved for forward action" in lower)

    def test_skill_references_adopt_status(self, skill_text):
        # The completeness view is the steering signal — it must be in the skill.
        assert "adopt status" in skill_text.lower()

    def test_skill_documents_skeleton_first(self, skill_text):
        assert "skeleton-first" in skill_text.lower() or "skeleton first" in skill_text.lower()

    def test_skill_under_500_lines(self):
        # The skill-standards rule: keep SKILL.md under 500 lines.
        path = PACKS_DIR / "adoption" / "skills" / "specflow-adopt" / "SKILL.md"
        n_lines = sum(1 for _ in path.read_text(encoding="utf-8").splitlines())
        assert n_lines < 500, f"SKILL.md is {n_lines} lines; skill-standards cap is 500"

    def test_checklist_drops_story_creation(self, checklist_text):
        # The checklist must NOT say to create a backfilled STORY.
        lower = checklist_text.lower()
        # Strong negative: no "backfilled from code" pointing at STORY.
        assert "backfill a req/story" not in lower
        # Positive: STORY section explicitly says "NOT backfilled" / "do not create".
        assert "not backfilled" in lower or "do not create" in lower

    def test_context_snippet_mentions_d20_signals(self):
        manifest = yaml.safe_load(
            (PACKS_DIR / "adoption" / "pack.yaml").read_text(encoding="utf-8")
        )
        snippet = manifest.get("context_snippet", "")
        # D-20 signals the user sees in AGENTS.md routing:
        assert "adopt status" in snippet
        assert "STORY" in snippet  # context explains the reservation
        assert "skeleton-first" in snippet or "skeleton first" in snippet.lower()
