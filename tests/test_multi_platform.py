"""Tests for multi-host skill-install awareness.

Covers:
1. lib.platform.detect_platforms — returns ALL detected platforms, in registry order.
2. commands.refresh --all-platforms — installs skills for every detected platform.
3. commands.init._multi_platform_warning — warns when skills were installed for only
   one of several detected AI-host platforms.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.commands import init as init_cmd
from specflow.commands import refresh as refresh_cmd
from specflow.lib import platform as plat_lib


def _make_specflow_project(root: Path) -> None:
    """Minimal .specflow/ scaffold sufficient for `specflow refresh` to run."""
    (root / ".specflow" / "schema").mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    config = {
        "project": {"name": root.name, "created": "2026-07-01"},
        "artifact_types": [],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(config))
    state = {"current": "idle", "history": []}
    (root / ".specflow" / "state.yaml").write_text(yaml.dump(state))


# ── 1. detect_platforms ──────────────────────────────────────────────────────

class TestDetectPlatforms:

    def test_two_markers_returns_both_platforms(self, tmp_path: Path):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".cursor").mkdir()

        detected = plat_lib.detect_platforms(tmp_path)

        codes = [code for code, _ in detected]
        assert "claude-code" in codes
        assert "cursor" in codes
        assert len(detected) == 2
        for _, cfg in detected:
            assert isinstance(cfg, dict)
            assert "skills_dir" in cfg

    def test_one_marker_returns_one_platform(self, tmp_path: Path):
        (tmp_path / ".claude").mkdir()

        detected = plat_lib.detect_platforms(tmp_path)

        assert len(detected) == 1
        assert detected[0][0] == "claude-code"

    def test_no_markers_returns_empty(self, tmp_path: Path):
        detected = plat_lib.detect_platforms(tmp_path)
        assert detected == []

    def test_registry_order_matches_detect_platform_first_hit(self, tmp_path: Path):
        """detect_platform() (singular) must agree with detect_platforms()[0]."""
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".cursor").mkdir()
        (tmp_path / ".opencode").mkdir()

        single_code, single_cfg = plat_lib.detect_platform(tmp_path)
        multi = plat_lib.detect_platforms(tmp_path)

        assert multi[0][0] == single_code
        assert multi[0][1] == single_cfg
        assert len(multi) == 3


# ── 2. refresh --all-platforms ───────────────────────────────────────────────

class TestRefreshAllPlatforms:

    def test_installs_skills_for_every_detected_platform(self, tmp_path: Path, capsys):
        root = tmp_path / "project"
        root.mkdir()
        (root / ".claude").mkdir()
        (root / ".cursor").mkdir()
        _make_specflow_project(root)

        rc = refresh_cmd.run(root, {"all_platforms": True})
        assert rc == 0

        claude_skills = root / ".claude" / "skills"
        cursor_skills = root / ".cursor" / "skills"
        assert claude_skills.is_dir() and any(claude_skills.iterdir()), \
            "claude-code skills dir should be populated"
        assert cursor_skills.is_dir() and any(cursor_skills.iterdir()), \
            "cursor skills dir should be populated"

        # Same skill set installed on both hosts.
        claude_names = {p.name for p in claude_skills.iterdir() if p.is_dir()}
        cursor_names = {p.name for p in cursor_skills.iterdir() if p.is_dir()}
        assert claude_names == cursor_names
        assert "specflow-init" in claude_names

        out = capsys.readouterr().out
        assert "claude-code" in out
        assert "cursor" in out

    def test_dry_run_does_not_write_skill_files(self, tmp_path: Path, capsys):
        root = tmp_path / "project"
        root.mkdir()
        (root / ".claude").mkdir()
        (root / ".cursor").mkdir()
        _make_specflow_project(root)

        rc = refresh_cmd.run(root, {"all_platforms": True, "dry_run": True})
        assert rc == 0

        assert not (root / ".claude" / "skills").exists() or \
            not any((root / ".claude" / "skills").iterdir())
        assert not (root / ".cursor" / "skills").exists() or \
            not any((root / ".cursor" / "skills").iterdir())

        out = capsys.readouterr().out
        assert "[dry-run]" in out

    def test_all_platforms_overrides_explicit_platform(self, tmp_path: Path, capsys):
        root = tmp_path / "project"
        root.mkdir()
        (root / ".claude").mkdir()
        (root / ".cursor").mkdir()
        _make_specflow_project(root)

        rc = refresh_cmd.run(root, {"all_platforms": True, "platform": "windsurf"})
        assert rc == 0

        out = capsys.readouterr().out
        assert "overrides" in out
        # windsurf was not detected, so it must not have been installed to.
        assert not (root / ".windsurf" / "skills").exists()
        assert (root / ".claude" / "skills").is_dir()
        assert (root / ".cursor" / "skills").is_dir()

    def test_no_detected_platform_fails_cleanly(self, tmp_path: Path, capsys):
        root = tmp_path / "project"
        root.mkdir()
        _make_specflow_project(root)

        rc = refresh_cmd.run(root, {"all_platforms": True})
        assert rc == 1

        out = capsys.readouterr().out
        assert "No AI platform detected" in out

    def test_claude_plus_opencode_installs_skills_once_to_claude(self, tmp_path: Path, capsys):
        root = tmp_path / "project"
        root.mkdir()
        (root / ".claude").mkdir()
        (root / ".opencode").mkdir()
        leftover = root / ".opencode" / "skills" / "specflow-discover"
        leftover.mkdir(parents=True)
        (leftover / "SKILL.md").write_text("# leftover fork\n", encoding="utf-8")
        _make_specflow_project(root)

        rc = refresh_cmd.run(root, {"all_platforms": True})
        assert rc == 0

        claude_skills = root / ".claude" / "skills"
        assert claude_skills.is_dir()
        assert (claude_skills / "specflow-init").is_dir()
        assert not (root / ".opencode" / "skills" / "specflow-init").exists()
        # Leftovers are not deleted — they are reported.
        assert leftover.is_dir()

        out = capsys.readouterr().out
        assert "claude-code" in out
        assert "opencode" in out
        assert "skills-leftover" in out or "leftover" in out.lower()
        assert "specflow-discover" in out


# ── 3. init multi-platform warning ───────────────────────────────────────────

class TestInitMultiPlatformWarning:

    def test_warns_when_multiple_platforms_detected(self, tmp_path: Path):
        root = tmp_path / "project"
        root.mkdir()
        (root / ".claude").mkdir()
        (root / ".cursor").mkdir()

        warning = init_cmd._multi_platform_warning(root, "claude-code", False)

        assert warning is not None
        assert "Multiple AI-host platforms detected" in warning
        assert "claude-code (installed)" in warning
        assert "cursor" in warning
        assert "specflow refresh --platform <code>" in warning
        assert "specflow refresh --all-platforms" in warning

    def test_no_warning_for_single_platform(self, tmp_path: Path):
        root = tmp_path / "project"
        root.mkdir()
        (root / ".claude").mkdir()

        warning = init_cmd._multi_platform_warning(root, "claude-code", False)
        assert warning is None

    def test_no_warning_when_platform_explicit(self, tmp_path: Path):
        root = tmp_path / "project"
        root.mkdir()
        (root / ".claude").mkdir()
        (root / ".cursor").mkdir()

        warning = init_cmd._multi_platform_warning(root, "claude-code", True)
        assert warning is None

    def test_no_warning_when_no_platform_detected(self, tmp_path: Path):
        root = tmp_path / "project"
        root.mkdir()

        warning = init_cmd._multi_platform_warning(root, "claude-code", False)
        assert warning is None

    def test_claude_plus_opencode_is_not_a_missing_install(self, tmp_path: Path):
        root = tmp_path / "project"
        root.mkdir()
        (root / ".claude").mkdir()
        (root / ".opencode").mkdir()

        warning = init_cmd._multi_platform_warning(root, "claude-code", False)
        assert warning is None

    def test_leftover_opencode_skills_warn_even_when_platform_explicit(self, tmp_path: Path):
        root = tmp_path / "project"
        root.mkdir()
        (root / ".claude").mkdir()
        leftover = root / ".opencode" / "skills" / "specflow-discover"
        leftover.mkdir(parents=True)
        (leftover / "SKILL.md").write_text("# leftover\n", encoding="utf-8")

        warning = init_cmd._multi_platform_warning(root, "claude-code", True)
        assert warning is not None
        assert "Leftover SpecFlow skills" in warning
        assert "specflow-discover" in warning
