"""OpenCode consumes .claude/skills; AGENTS.md is the only instruction file."""

from __future__ import annotations

from pathlib import Path

from specflow.commands import init as init_cmd
from specflow.lib import platform as plat_lib
from specflow.lib import scaffold as scaffold_lib

TEMPLATES_DIR = Path(__file__).parent.parent / "src" / "specflow" / "templates"
PACKS_DIR = Path(__file__).parent.parent / "src" / "specflow" / "packs"


class TestSkillInstallRemap:

    def test_opencode_installs_into_claude_skills(self, tmp_path: Path):
        root = tmp_path / "proj"
        root.mkdir()
        assert plat_lib.get_skills_install_code("opencode") == "claude-code"
        assert plat_lib.get_skills_install_dir(root, "opencode") == root / ".claude" / "skills"
        assert plat_lib.get_skills_dir(root, "opencode") == root / ".opencode" / "skills"

    def test_unique_install_codes_collapse_claude_and_opencode(self):
        assert plat_lib.unique_skill_install_codes(
            ["claude-code", "opencode", "cursor"]
        ) == ["claude-code", "cursor"]

    def test_init_opencode_writes_claude_skills_not_opencode(self, tmp_path: Path):
        root = tmp_path / "proj"
        root.mkdir()
        (root / ".opencode").mkdir()

        rc = init_cmd.run(root, {"platform": "opencode", "no_ci": True})
        assert rc == 0
        assert (root / ".claude" / "skills" / "specflow-discover" / "SKILL.md").is_file()
        assert not (root / ".opencode" / "skills").exists() or not any(
            p.name.startswith("specflow-")
            for p in (root / ".opencode" / "skills").iterdir()
            if p.is_dir()
        )

    def test_init_does_not_delete_opencode_agents_or_commands(self, tmp_path: Path):
        root = tmp_path / "proj"
        root.mkdir()
        (root / ".opencode" / "agents").mkdir(parents=True)
        (root / ".opencode" / "commands").mkdir(parents=True)
        (root / ".opencode" / "agents" / "reviewer.md").write_text("# keep\n", encoding="utf-8")
        (root / ".opencode" / "commands" / "orient.md").write_text("# keep\n", encoding="utf-8")

        rc = init_cmd.run(root, {"platform": "opencode", "no_ci": True})
        assert rc == 0
        assert (root / ".opencode" / "agents" / "reviewer.md").is_file()
        assert (root / ".opencode" / "commands" / "orient.md").is_file()

    def test_pack_skills_follow_the_install_remap(self, tmp_path: Path):
        root = tmp_path / "proj"
        root.mkdir()
        (root / ".opencode").mkdir()
        (root / ".specflow" / "schema").mkdir(parents=True)
        (root / ".specflow" / "standards").mkdir(parents=True)

        result = scaffold_lib.apply_pack(root, "ops", PACKS_DIR, platform_code="opencode")
        assert result["ok"]
        assert (root / ".claude" / "skills" / "specflow-ops").is_dir()
        assert not (root / ".opencode" / "skills" / "specflow-ops").exists()


class TestAgentsMdOnly:

    def test_opencode_and_claude_share_agents_md(self, tmp_path: Path):
        root = tmp_path / "proj"
        root.mkdir()
        (root / ".claude").mkdir()
        (root / ".opencode").mkdir()

        assert scaffold_lib.inject_base_context(root, TEMPLATES_DIR, "claude-code")
        assert scaffold_lib.inject_base_context(root, TEMPLATES_DIR, "opencode") is False
        assert (root / "AGENTS.md").is_file()
        assert not (root / "CLAUDE.md").exists()
        text = (root / "AGENTS.md").read_text(encoding="utf-8")
        assert text.count("<!-- SpecFlow section") == 1
        assert "Lead with the answer" in text


BASE_START = "<!-- SpecFlow section (auto-generated, do not edit manually) -->"
BASE_END = "<!-- End SpecFlow section -->"
PACK_START = "<!-- pack:tldr-communication context (auto-generated, do not edit manually) -->"
PACK_END = "<!-- end pack:tldr-communication context -->"


def _legacy_claude_md(root: Path, *, with_pack: bool = False) -> None:
    parts = ["# My project\n", "\nUser prose stays.\n", f"\n{BASE_START}\n", "old fat block\n", f"{BASE_END}\n"]
    if with_pack:
        parts += [f"\n{PACK_START}\n", "pack guidance\n", f"{PACK_END}\n", "\nMore user prose.\n"]
    (root / "CLAUDE.md").write_text("".join(parts), encoding="utf-8")


class TestLegacySentinelMigration:

    def test_opencode_only_project_strips_claude_md_sentinel(self, tmp_path: Path):
        """Fix: the old CLAUDE.md fallback applied to OpenCode hosts too."""
        root = tmp_path / "proj"
        root.mkdir()
        (root / ".opencode").mkdir()
        _legacy_claude_md(root)

        assert scaffold_lib.inject_base_context(root, TEMPLATES_DIR, "opencode")
        assert (root / "AGENTS.md").is_file()
        legacy = (root / "CLAUDE.md").read_text(encoding="utf-8")
        assert BASE_START not in legacy
        assert "User prose stays." in legacy  # only the block is removed

    def test_migrated_claude_md_gets_agents_md_bridge(self, tmp_path: Path):
        """Claude Code reads CLAUDE.md only; the @AGENTS.md import keeps it
        loading the shared guidance after the block moves to AGENTS.md."""
        root = tmp_path / "proj"
        root.mkdir()
        (root / ".opencode").mkdir()
        _legacy_claude_md(root)

        assert scaffold_lib.inject_base_context(root, TEMPLATES_DIR, "opencode")
        legacy_lines = (root / "CLAUDE.md").read_text(encoding="utf-8").splitlines()
        assert legacy_lines[0].strip() == "@AGENTS.md"  # documented bridge, first line
        assert "User prose stays." in legacy_lines

        # Idempotent: a second refresh must not duplicate the bridge.
        scaffold_lib.inject_base_context(root, TEMPLATES_DIR, "opencode")
        text = (root / "CLAUDE.md").read_text(encoding="utf-8")
        assert sum(1 for line in text.splitlines() if line.strip() == "@AGENTS.md") == 1

    def test_prose_only_claude_md_gets_bridge_too(self, tmp_path: Path):
        """Even without a legacy sentinel, Claude Code cannot see AGENTS.md —
        the bridge is required whenever SpecFlow injects into AGENTS.md."""
        root = tmp_path / "proj"
        root.mkdir()
        (root / ".claude").mkdir()
        (root / "CLAUDE.md").write_text("# My conventions\n\nRun tests with pytest.\n", encoding="utf-8")

        assert scaffold_lib.inject_base_context(root, TEMPLATES_DIR, "claude-code")
        text = (root / "CLAUDE.md").read_text(encoding="utf-8")
        assert text.splitlines()[0].strip() == "@AGENTS.md"
        assert "# My conventions" in text
        assert "Run tests with pytest." in text

    def test_block_only_claude_md_becomes_bridge_only(self, tmp_path: Path):
        root = tmp_path / "proj"
        root.mkdir()
        (root / ".claude").mkdir()
        (root / "CLAUDE.md").write_text(
            f"{BASE_START}\nold block\n{BASE_END}\n", encoding="utf-8"
        )

        assert scaffold_lib.inject_base_context(root, TEMPLATES_DIR, "claude-code")
        text = (root / "CLAUDE.md").read_text(encoding="utf-8")
        assert text.strip() == "@AGENTS.md"
        assert BASE_START not in text

    def test_pack_sentinels_migrate_not_drop(self, tmp_path: Path):
        """Fix: a pack block in CLAUDE.md survives until it lands in AGENTS.md."""
        root = tmp_path / "proj"
        root.mkdir()
        (root / ".claude").mkdir()
        _legacy_claude_md(root, with_pack=True)

        # Context refresh only: base block migrates, pack block must remain.
        assert scaffold_lib.inject_base_context(root, TEMPLATES_DIR, "claude-code")
        legacy = (root / "CLAUDE.md").read_text(encoding="utf-8")
        assert BASE_START not in legacy
        assert PACK_START in legacy, "pack guidance must not be dropped before migrating"

        # Pack refresh: now the pack block migrates too.
        assert scaffold_lib.inject_pack_context(root, "tldr-communication", "new pack guidance\n", "claude-code")
        legacy = (root / "CLAUDE.md").read_text(encoding="utf-8")
        agents = (root / "AGENTS.md").read_text(encoding="utf-8")
        assert PACK_START not in legacy
        assert PACK_START in agents
        assert "More user prose." in legacy

    def test_gemini_platform_never_touches_claude_md(self, tmp_path: Path):
        root = tmp_path / "proj"
        root.mkdir()
        (root / ".gemini").mkdir()
        _legacy_claude_md(root)

        assert scaffold_lib.inject_base_context(root, TEMPLATES_DIR, "gemini")
        # Gemini's instruction_file is GEMINI.md — CLAUDE.md is untouched
        # (no strip, and no @AGENTS.md bridge: not an AGENTS.md platform here).
        legacy = (root / "CLAUDE.md").read_text(encoding="utf-8")
        assert BASE_START in legacy
        assert not any(line.strip() == "@AGENTS.md" for line in legacy.splitlines())


def _make_specflow_project(root: Path) -> None:
    import yaml

    (root / ".specflow" / "schema").mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "config.yaml").write_text(yaml.dump({
        "project": {"name": root.name, "created": "2026-08-18"},
        "artifact_types": [],
        "active_packs": [],
    }))
    (root / ".specflow" / "state.yaml").write_text(yaml.dump({"current": "idle", "history": []}))


class TestDefaultRefreshLeftoverScan:

    def test_default_refresh_warns_opencode_leftovers(self, tmp_path: Path, capsys):
        """Fix: plain `specflow refresh` resolves to claude-code on a dual-host
        repo; it must still surface .opencode leftovers (they silently win)."""
        from specflow.commands import refresh as refresh_cmd

        root = tmp_path / "proj"
        root.mkdir()
        (root / ".claude").mkdir()
        (root / ".opencode" / "skills" / "specflow-discover").mkdir(parents=True)
        (root / ".opencode" / "skills" / "specflow-discover" / "SKILL.md").write_text(
            "# leftover fork\n", encoding="utf-8"
        )
        _make_specflow_project(root)

        rc = refresh_cmd.run(root, {})
        assert rc == 0

        out = capsys.readouterr().out
        assert "skills-leftover" in out
        assert "specflow-discover" in out
        # Not deleted — reported.
        assert (root / ".opencode" / "skills" / "specflow-discover").is_dir()
