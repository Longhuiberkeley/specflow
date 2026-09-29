"""STORY-685 — platform install never deletes the instruction file or pack blocks.

Covers:
1. No platforms.yaml legacy_dir is the instruction file or one of its ancestors.
2. Legacy cleanup refuses ancestors of the instruction file and removes only
   specflow-owned entries inside a legacy dir.
3. init installs skills before injecting context (same order as refresh).
4. For EVERY platforms.yaml entry: init --platform X --preset ops, then
   refresh, keeps the base + pack sentinel blocks and a user-authored sibling
   file next to the instruction file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specflow.commands import init as init_cmd
from specflow.commands import refresh as refresh_cmd
from specflow.lib import platform as plat_lib
from specflow.lib import scaffold as scaffold_lib

_ALL_PLATFORMS = sorted(plat_lib.get_all_platforms().keys())
_PACK = "ops"
_BASE_START = scaffold_lib._BASE_SENTINEL_START
_PACK_START = scaffold_lib._SENTINEL_START.format(pack_name=_PACK)
_PACK_END = scaffold_lib._SENTINEL_END.format(pack_name=_PACK)


def _is_ancestor_or_self(candidate: Path, target: Path) -> bool:
    return candidate == target or candidate in target.parents


# ── 1. Registry shape ────────────────────────────────────────────────────────

@pytest.mark.parametrize("code", _ALL_PLATFORMS)
def test_no_legacy_dir_contains_the_instruction_file(code: str):
    cfg = plat_lib.get_platform(code)
    inst = Path(cfg["instruction_file"])
    for legacy in cfg.get("legacy_dirs", []) or []:
        assert not _is_ancestor_or_self(Path(legacy), inst), (
            f"{code}: legacy_dir {legacy!r} would delete instruction_file {inst}"
        )


def test_kiro_and_trae_no_longer_name_their_rules_dir():
    assert ".kiro/steering" not in (plat_lib.get_platform("kiro").get("legacy_dirs") or [])
    assert ".trae/rules" not in (plat_lib.get_platform("trae").get("legacy_dirs") or [])


# ── 2. Cleanup guard ─────────────────────────────────────────────────────────

def _fake_registry(monkeypatch, entry: dict) -> None:
    monkeypatch.setattr(plat_lib, "_REGISTRY", {"fake": entry})


def test_cleanup_refuses_ancestor_of_instruction_file(tmp_path: Path, monkeypatch):
    _fake_registry(monkeypatch, {
        "name": "Fake",
        "skills_dir": ".fake/skills",
        "instruction_file": ".fake/rules/specflow.md",
        "legacy_dirs": [".fake/rules", ".fake"],
    })
    rules = tmp_path / ".fake" / "rules"
    rules.mkdir(parents=True)
    (rules / "specflow.md").write_text("instructions\n")
    (rules / "specflow-old.md").write_text("old specflow command\n")

    removed = plat_lib.cleanup_legacy_dirs(tmp_path, "fake")

    assert removed == []
    assert (rules / "specflow.md").exists()
    assert (rules / "specflow-old.md").exists(), "refused dirs are not touched at all"


def test_cleanup_removes_only_specflow_owned_entries(tmp_path: Path, monkeypatch):
    _fake_registry(monkeypatch, {
        "name": "Fake",
        "skills_dir": ".fake/skills",
        "instruction_file": "AGENTS.md",
        "legacy_dirs": [".fake/commands"],
    })
    legacy = tmp_path / ".fake" / "commands"
    (legacy / "specflow").mkdir(parents=True)
    (legacy / "specflow" / "init.md").write_text("x\n")
    (legacy / "specflow-plan.md").write_text("x\n")
    (legacy / "my-own-command.md").write_text("user\n")

    removed = plat_lib.cleanup_legacy_dirs(tmp_path, "fake")

    assert sorted(removed) == [".fake/commands/specflow", ".fake/commands/specflow-plan.md"]
    assert (legacy / "my-own-command.md").exists()
    assert not (legacy / "specflow").exists()
    assert not (legacy / "specflow-plan.md").exists()


def test_cleanup_drops_legacy_dir_emptied_of_specflow_entries(tmp_path: Path, monkeypatch):
    _fake_registry(monkeypatch, {
        "name": "Fake",
        "skills_dir": ".fake/skills",
        "instruction_file": "AGENTS.md",
        "legacy_dirs": [".fake/commands"],
    })
    legacy = tmp_path / ".fake" / "commands"
    legacy.mkdir(parents=True)
    (legacy / "specflow-plan.md").write_text("x\n")

    plat_lib.cleanup_legacy_dirs(tmp_path, "fake")

    assert not legacy.exists()


def test_cleanup_dry_run_reports_without_deleting(tmp_path: Path, monkeypatch):
    _fake_registry(monkeypatch, {
        "name": "Fake",
        "skills_dir": ".fake/skills",
        "instruction_file": "AGENTS.md",
        "legacy_dirs": [".fake/commands"],
    })
    legacy = tmp_path / ".fake" / "commands"
    legacy.mkdir(parents=True)
    (legacy / "specflow-plan.md").write_text("x\n")

    removed = plat_lib.cleanup_legacy_dirs(tmp_path, "fake", dry_run=True)

    assert removed == [".fake/commands/specflow-plan.md"]
    assert (legacy / "specflow-plan.md").exists()


@pytest.fixture(autouse=True)
def _restore_registry():
    yield
    plat_lib.reload_registry()


# ── 3. init ordering ─────────────────────────────────────────────────────────

def test_init_installs_skills_before_injecting_context(tmp_path: Path, monkeypatch):
    order: list[str] = []
    real_install = init_cmd._install_skills
    real_inject = scaffold_lib.inject_base_context

    def spy_install(root, code):
        order.append("skills")
        return real_install(root, code)

    def spy_inject(*a, **k):
        order.append("context")
        return real_inject(*a, **k)

    monkeypatch.setattr(init_cmd, "_install_skills", spy_install)
    monkeypatch.setattr(init_cmd.scaffold_lib, "inject_base_context", spy_inject)

    root = tmp_path / "proj"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    assert order == ["skills", "context"]


# ── 4. Every platform: init --preset then refresh keeps blocks + user files ──

@pytest.mark.parametrize("code", _ALL_PLATFORMS)
def test_init_preset_then_refresh_keeps_blocks_and_user_sibling(tmp_path: Path, code: str):
    cfg = plat_lib.get_platform(code)
    root = tmp_path / "proj"
    root.mkdir()
    inst = root / cfg["instruction_file"]
    inst.parent.mkdir(parents=True, exist_ok=True)
    sibling = inst.parent / "team-notes.md"
    sibling.write_text("user-authored, not SpecFlow's\n", encoding="utf-8")

    rc = init_cmd.run(root, {"platform": code, "preset": _PACK, "no_ci": True})
    assert rc == 0
    assert inst.exists(), f"{code}: init deleted {cfg['instruction_file']}"
    text = inst.read_text(encoding="utf-8")
    assert _BASE_START in text, f"{code}: base block missing after init"
    assert _PACK_START in text and _PACK_END in text, f"{code}: pack block missing after init"
    assert sibling.exists(), f"{code}: init deleted a user file beside the instruction file"

    rc = refresh_cmd.run(root, {"platform": code})
    assert rc == 0
    assert inst.exists(), f"{code}: refresh deleted {cfg['instruction_file']}"
    text = inst.read_text(encoding="utf-8")
    assert _BASE_START in text, f"{code}: base block missing after refresh"
    assert _PACK_START in text, f"{code}: pack block missing after refresh"
    assert sibling.read_text(encoding="utf-8") == "user-authored, not SpecFlow's\n"


@pytest.mark.parametrize("code", _ALL_PLATFORMS)
def test_fresh_init_creates_nested_instruction_file(tmp_path: Path, code: str):
    """No pre-existing host dir: init must still land both blocks."""
    cfg = plat_lib.get_platform(code)
    root = tmp_path / "fresh"
    root.mkdir()

    assert init_cmd.run(root, {"platform": code, "preset": _PACK, "no_ci": True}) == 0

    text = (root / cfg["instruction_file"]).read_text(encoding="utf-8")
    assert _BASE_START in text
    assert _PACK_START in text
