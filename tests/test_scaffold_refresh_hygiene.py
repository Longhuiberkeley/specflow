"""STORY-709 (v1.17.2 P-3) — scaffold / refresh / init hygiene regressions.

Covers F-072, F-103, F-109, F-114, F-117, F-123, F-125, F-127, F-130:

- refresh reports only the skills that changed as "installed" (F-072);
- `refresh --packs` syncs a pack's standards/ tree, preserving edits unless
  `--force` and naming every file it writes / preserves / backs up (F-103,
  F-109); `--force` backs the old copy up under one timestamped run dir;
- an unknown preset names both lookup locations and the available packs (F-114);
- `init --force` keeps an existing findings baseline and backs up the
  baseline, checklists and source fingerprints (F-117);
- malformed sentinel markers (missing END, END before START) are repaired
  idempotently instead of crashing or growing the file (F-123);
- installed optional-type schemas get a drift signal; uninstalled ones are
  never reported as new (F-125);
- Codex and Junie share one skills tree: one install, no false warning, one
  AGENTS.md block (F-127);
- legacy-dir cleanup runs even when the skills are already current, honours
  dry-run, and reports what it removed (F-130).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.commands import init as init_cmd
from specflow.commands import refresh as refresh_cmd
from specflow.commands.findings_baseline import write_baseline
from specflow.core import findings_baseline as fb
from specflow.lib import config as config_lib
from specflow.lib import platform as plat_lib
from specflow.lib import scaffold as scaffold_lib

_TEMPLATES = Path(scaffold_lib.__file__).resolve().parents[1] / "templates"
_BASE_START = scaffold_lib._BASE_SENTINEL_START
_BASE_END = scaffold_lib._BASE_SENTINEL_END
_PACK = "ops"
_PACK_START = scaffold_lib._SENTINEL_START.format(pack_name=_PACK)
_PACK_END = scaffold_lib._SENTINEL_END.format(pack_name=_PACK)


def _init(tmp_path: Path, **extra) -> Path:
    root = tmp_path / "p"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True, **extra}) == 0
    return root


def _write_local_pack(root: Path, name: str) -> Path:
    pack = root / ".specflow" / "packs" / name
    (pack / "standards").mkdir(parents=True)
    (pack / "schemas").mkdir(parents=True)
    (pack / "pack.yaml").write_text(yaml.dump({
        "name": name, "version": "0.1.0", "description": "local pack",
        "adds_artifact_types": [], "context_snippet": "### Local pack\nline.",
    }, sort_keys=False))
    (pack / "standards" / "local-std.yaml").write_text("standard: LOCAL\ntitle: v1\nclauses: []\n")
    (pack / "schemas" / "local-thing.yaml").write_text("type: local-thing\n")
    return pack


def _backups(root: Path) -> Path:
    return root / ".specflow" / "cache" / "backups"


# ── F-072 ────────────────────────────────────────────────────────────────────

def test_refresh_reports_only_changed_skills_as_installed(tmp_path: Path, capsys):
    root = _init(tmp_path)
    (root / ".claude" / "skills" / "specflow-plan" / "SKILL.md").write_text("# drifted\n")
    capsys.readouterr()

    assert refresh_cmd.run(root, {"platform": "claude-code", "no_context": True}) == 0

    out = capsys.readouterr().out
    assert "1 installed (specflow-plan)" in out
    assert "13 installed" not in out


# ── F-103 / F-109 ────────────────────────────────────────────────────────────

def test_refresh_packs_preserves_edited_standard_and_names_it(tmp_path: Path, capsys):
    root = _init(tmp_path)
    pack = _write_local_pack(root, "mylocal")
    assert init_cmd.run(root, {"platform": "claude-code", "preset": "mylocal", "no_ci": True}) == 0
    installed = root / ".specflow" / "standards" / "local-std.yaml"
    assert installed.exists()
    (pack / "standards" / "local-std.yaml").write_text("standard: LOCAL\ntitle: v2\nclauses: []\n")
    capsys.readouterr()

    # dry-run names the standard
    assert refresh_cmd.run(root, {"platform": "claude-code", "packs": True, "dry_run": True, "no_skills": True}) == 0
    out = capsys.readouterr().out
    assert "would preserve 1 changed: .specflow/standards/local-std.yaml" in out
    assert "title: v1" in installed.read_text()

    # default run preserves, names the file, no backup taken
    assert refresh_cmd.run(root, {"platform": "claude-code", "packs": True, "no_skills": True}) == 0
    out = capsys.readouterr().out
    assert "1 preserved (changed): .specflow/standards/local-std.yaml" in out
    assert "--packs --force" in out
    assert "title: v1" in installed.read_text()
    assert not (_backups(root)).exists() or not list(_backups(root).rglob("packs/*"))


def test_refresh_packs_force_overwrites_standard_with_backup(tmp_path: Path, capsys):
    root = _init(tmp_path)
    pack = _write_local_pack(root, "mylocal")
    assert init_cmd.run(root, {"platform": "claude-code", "preset": "mylocal", "no_ci": True}) == 0
    (pack / "standards" / "local-std.yaml").write_text("standard: LOCAL\ntitle: v2\nclauses: []\n")
    capsys.readouterr()

    assert refresh_cmd.run(root, {"platform": "claude-code", "packs": True, "force": True, "no_skills": True}) == 0

    out = capsys.readouterr().out
    installed = root / ".specflow" / "standards" / "local-std.yaml"
    assert "title: v2" in installed.read_text()
    assert "1 written: .specflow/standards/local-std.yaml" in out
    assert "backups in .specflow/cache/backups/" in out
    backed = list(_backups(root).glob("*/packs/mylocal/.specflow/standards/local-std.yaml"))
    assert len(backed) == 1, "the overwritten standard must be backed up once"
    assert "title: v1" in backed[0].read_text()


def test_refresh_packs_lists_new_files_in_dry_run(tmp_path: Path, capsys):
    root = _init(tmp_path)
    pack = _write_local_pack(root, "mylocal")
    assert init_cmd.run(root, {"platform": "claude-code", "preset": "mylocal", "no_ci": True}) == 0
    (pack / "schemas" / "local-extra.yaml").write_text("type: local-extra\n")
    capsys.readouterr()

    assert refresh_cmd.run(root, {"platform": "claude-code", "packs": True, "dry_run": True, "no_skills": True}) == 0

    out = capsys.readouterr().out
    assert "would write 1 new: .specflow/schema/local-extra.yaml" in out
    assert not (root / ".specflow" / "schema" / "local-extra.yaml").exists()


def test_checklist_backup_shares_the_run_timestamp_dir(tmp_path: Path):
    root = _init(tmp_path)
    target = root / ".specflow" / "checklists" / "in-process" / "story-writing.yaml"
    target.write_text("name: story-writing\nnote: edited\nitems: []\n")

    result = scaffold_lib.copy_checklists(root, _TEMPLATES, force=True, backup_stamp="20260101T000000Z")

    assert result["backup_dir"] == ".specflow/cache/backups/20260101T000000Z"
    assert (_backups(root) / "20260101T000000Z" / "checklists" / "in-process" / "story-writing.yaml").exists()


# ── F-114 ────────────────────────────────────────────────────────────────────

def test_unknown_preset_error_names_both_locations_and_available_packs(tmp_path: Path, capsys):
    root = tmp_path / "p"
    root.mkdir()

    rc = init_cmd.run(root, {"platform": "claude-code", "preset": "nope", "no_ci": True})

    assert rc == 1
    out = capsys.readouterr().out
    assert ".specflow/packs/nope/pack.yaml" in out
    assert str(scaffold_lib.bundled_packs_dir() / "nope" / "pack.yaml") in out
    assert "available:" in out and "ops" in out
    assert "exists but has no pack.yaml" not in out


def test_unknown_preset_error_flags_local_dir_without_manifest_and_case(tmp_path: Path):
    root = tmp_path / "p"
    (root / ".specflow" / "packs" / "OPS").mkdir(parents=True)

    msg = scaffold_lib.pack_not_found_error(root, "OPS")

    assert ".specflow/packs/OPS/ exists but has no pack.yaml" in msg
    assert "did you mean 'ops'?" in msg


# ── F-117 ────────────────────────────────────────────────────────────────────

def test_init_force_keeps_baseline_and_backs_up_state_files(tmp_path: Path, capsys):
    root = _init(tmp_path)
    key = ("coverage/no-test", ("STORY-001",))
    write_baseline(root, {key})
    (root / ".specflow" / "source-fingerprints.yaml").write_text("fingerprints: {}\n")
    capsys.readouterr()

    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True, "force": True}) == 0

    out = capsys.readouterr().out
    keys, err = fb.load(root)
    assert err is None and keys is not None
    assert key in keys, "--force must not empty an existing findings baseline"
    assert "findings-baseline.yaml kept" in out
    runs = sorted(p for p in _backups(root).iterdir() if p.is_dir())
    assert runs, "a backup run dir must exist"
    run_dir = runs[-1]
    assert (run_dir / "findings-baseline.yaml").exists()
    assert (run_dir / "source-fingerprints.yaml").exists()
    assert (run_dir / "checklists" / "in-process" / "story-writing.yaml").exists()
    assert (run_dir / "config.yaml").exists() and (run_dir / "schema").is_dir()
    assert ".specflow/findings-baseline.yaml" in out and ".specflow/checklists/" in out
    assert "reset to fresh defaults" in out
    assert "active_packs" not in out, "no packs were active, so none are reported cleared"


def test_init_force_names_cleared_packs_and_skips_preset_hint_when_reapplied(tmp_path: Path, capsys):
    root = _init(tmp_path, preset=_PACK)
    assert (config_lib.read_config(root) or {}).get("active_packs") == [_PACK]
    capsys.readouterr()

    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True, "force": True}) == 0
    out = capsys.readouterr().out
    assert f"active_packs cleared ({_PACK})" in out
    assert "re-apply with --preset" in out
    assert not (config_lib.read_config(root) or {}).get("active_packs")

    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True, "preset": _PACK}) == 0
    capsys.readouterr()
    assert init_cmd.run(
        root, {"platform": "claude-code", "no_ci": True, "force": True, "preset": _PACK},
    ) == 0
    out = capsys.readouterr().out
    assert f"active_packs cleared ({_PACK})" in out
    assert "re-apply with --preset" not in out, "the pack is re-applied in this very run"
    assert (config_lib.read_config(root) or {}).get("active_packs") == [_PACK]
    runs = sorted(p for p in _backups(root).iterdir() if p.is_dir())
    assert (runs[-1] / "config.yaml").exists()  # shared backup_run_dir layout


def test_fresh_init_still_writes_empty_baseline(tmp_path: Path):
    root = _init(tmp_path)
    keys, err = fb.load(root)
    assert err is None and keys == frozenset()


# ── F-123 ────────────────────────────────────────────────────────────────────

def _inject_base(root: Path) -> bool:
    return scaffold_lib.inject_base_context(root, _TEMPLATES, "claude-code")


def test_missing_end_marker_is_repaired_idempotently(tmp_path: Path, capsys):
    root = tmp_path / "p"
    root.mkdir()
    agents = root / "AGENTS.md"
    agents.write_text(f"# Head\n\n{_BASE_START}\nold body\nuser tail\n", encoding="utf-8")

    assert _inject_base(root) is True  # no ValueError
    text = agents.read_text(encoding="utf-8")
    assert text.count(_BASE_START) == 1 and text.count(_BASE_END) == 1
    assert text.index(_BASE_END) > text.index(_BASE_START)
    assert "# Head" in text and "user tail" in text and "old body" in text
    warning = capsys.readouterr().out
    assert "malformed" in warning
    assert "text from the old block may remain" in warning  # stale copy is reviewable

    assert _inject_base(root) is False
    assert agents.read_text(encoding="utf-8") == text


def test_reversed_markers_do_not_grow_the_file(tmp_path: Path):
    root = tmp_path / "p"
    root.mkdir()
    agents = root / "AGENTS.md"
    agents.write_text(
        f"head\n{_BASE_END}\nmid\n{_BASE_START}\nold\ntail\n", encoding="utf-8",
    )

    assert _inject_base(root) is True
    first = agents.read_text(encoding="utf-8")
    assert first.count(_BASE_START) == 1 and first.count(_BASE_END) == 1
    assert first.index(_BASE_START) < first.index(_BASE_END)
    for user_line in ("head", "mid", "old", "tail"):
        assert f"\n{user_line}\n" in f"\n{first}" or first.startswith(f"{user_line}\n")

    assert _inject_base(root) is False
    assert _inject_base(root) is False
    assert agents.read_text(encoding="utf-8") == first, "second run must not grow the file"


def test_pack_block_reversed_markers_repaired(tmp_path: Path):
    root = tmp_path / "p"
    root.mkdir()
    agents = root / "AGENTS.md"
    agents.write_text(f"intro\n{_PACK_END}\nbetween\n{_PACK_START}\nstale\n", encoding="utf-8")

    assert scaffold_lib.inject_pack_context(root, _PACK, "fresh snippet", "claude-code") is True
    text = agents.read_text(encoding="utf-8")
    assert text.count(_PACK_START) == 1 and text.count(_PACK_END) == 1
    assert text.index(_PACK_START) < text.index(_PACK_END)
    assert "between" in text and "stale" in text and "fresh snippet" in text

    assert scaffold_lib.inject_pack_context(root, _PACK, "fresh snippet", "claude-code") is False
    assert agents.read_text(encoding="utf-8") == text


def test_pack_block_missing_end_repaired(tmp_path: Path):
    root = tmp_path / "p"
    root.mkdir()
    agents = root / "AGENTS.md"
    agents.write_text(f"intro\n{_PACK_START}\nstale\n", encoding="utf-8")

    assert scaffold_lib.inject_pack_context(root, _PACK, "snippet", "claude-code") is True
    text = agents.read_text(encoding="utf-8")
    assert text.count(_PACK_START) == 1 and text.count(_PACK_END) == 1
    assert scaffold_lib.inject_pack_context(root, _PACK, "snippet", "claude-code") is False


def test_strip_sentinel_block_ignores_reversed_markers(tmp_path: Path):
    path = tmp_path / "CLAUDE.md"
    original = f"a\n{_BASE_END}\nb\n{_BASE_START}\nc\n"
    path.write_text(original, encoding="utf-8")

    assert scaffold_lib._strip_sentinel_block(path, _BASE_START, _BASE_END) is False
    assert path.read_text(encoding="utf-8") == original


# ── F-125 ────────────────────────────────────────────────────────────────────

def test_installed_optional_schema_drift_is_classified_but_uninstalled_never_new(tmp_path: Path):
    root = _init(tmp_path, with_types="hazard")
    hazard = root / ".specflow" / "schema" / "hazard.yaml"
    assert hazard.exists()

    new, identical, changed = refresh_cmd.classify_schemas(root)
    assert "hazard" in identical
    assert "risk" not in new and "control" not in new

    hazard.write_text(hazard.read_text() + "\n# local drift\n")
    new, identical, changed = refresh_cmd.classify_schemas(root)
    assert "hazard" in changed
    assert "risk" not in new and "control" not in new

    _written, preserved, _replaced = refresh_cmd._update_schemas(root, _TEMPLATES, force=False)
    assert "hazard" in preserved and "# local drift" in hazard.read_text()
    assert not (root / ".specflow" / "schema" / "risk.yaml").exists()

    _written, _preserved, replaced = refresh_cmd._update_schemas(root, _TEMPLATES, force=True)
    assert "hazard" in replaced and "# local drift" not in hazard.read_text()
    assert not (root / ".specflow" / "schema" / "risk.yaml").exists()


def _write_pack_owning_control(root: Path, name: str = "iso27001") -> Path:
    pack = root / ".specflow" / "packs" / name
    (pack / "schemas").mkdir(parents=True)
    (pack / "pack.yaml").write_text(yaml.dump({
        "name": name, "version": "0.1.0", "description": "pack reusing an optional core name",
        "adds_artifact_types": ["control"], "adds_directories": ["controls"],
        "context_snippet": "### ISO pack\nline.",
    }, sort_keys=False))
    (pack / "schemas" / "control.yaml").write_text(
        "type: control\nid_prefix: CTL\nfields: {}\n", encoding="utf-8",
    )
    return pack


def test_pack_owned_optional_schema_is_never_core_drift(tmp_path: Path, capsys):
    """A pack that ships its own `control.yaml` is not a drifted core optional type."""
    root = tmp_path / "p"
    root.mkdir()
    _write_pack_owning_control(root)
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True, "preset": "iso27001"}) == 0
    control = root / ".specflow" / "schema" / "control.yaml"
    pack_bytes = control.read_bytes()
    assert b"CTL" in pack_bytes
    assert scaffold_lib.pack_owned_schema_names(root, ["iso27001"]) == {"control"}

    new, identical, changed = refresh_cmd.classify_schemas(root)
    assert "control" not in new and "control" not in changed and "control" not in identical

    _written, preserved, replaced = refresh_cmd._update_schemas(root, _TEMPLATES, force=True)
    assert "control" not in replaced and "control" not in preserved
    assert control.read_bytes() == pack_bytes, "--force must not clobber the pack's schema"

    capsys.readouterr()
    assert refresh_cmd.run(root, {"dry_run": True, "schemas": True, "no_skills": True, "no_context": True}) == 0
    out = capsys.readouterr().out
    assert "changed: control" not in out
    assert refresh_cmd.run(root, {"schemas": True, "force": True, "no_skills": True, "no_context": True}) == 0
    assert control.read_bytes() == pack_bytes
    assert "replaced: control" not in capsys.readouterr().out


def test_pack_ownership_by_manifest_alone_also_skips_classification(tmp_path: Path):
    """`adds_artifact_types: [hazard]` with no shipped schema still owns the name."""
    root = _init(tmp_path, with_types="hazard")
    pack = root / ".specflow" / "packs" / "haz"
    pack.mkdir(parents=True)
    (pack / "pack.yaml").write_text(yaml.dump({
        "name": "haz", "version": "0.1.0", "description": "owns hazard",
        "adds_artifact_types": ["hazard"],
    }))
    hazard = root / ".specflow" / "schema" / "hazard.yaml"
    hazard.write_text(hazard.read_text() + "\n# pack tuned\n")
    assert "hazard" in refresh_cmd.classify_schemas(root)[2], "sanity: drift seen when no pack owns it"

    cfg = config_lib.read_config(root) or {}
    cfg["active_packs"] = ["haz"]
    config_lib.write_config(root, cfg)
    assert scaffold_lib.pack_owned_schema_names(root, ["haz"]) == {"hazard"}
    new, _identical, changed = refresh_cmd.classify_schemas(root)
    assert "hazard" not in changed and "hazard" not in new
    refresh_cmd._update_schemas(root, _TEMPLATES, force=True)
    assert "# pack tuned" in hazard.read_text()


def test_install_skills_has_no_dead_dry_run_parameter():
    import inspect

    assert "dry_run" not in inspect.signature(refresh_cmd._install_skills).parameters


def test_init_force_resets_requested_drifted_optional_type(tmp_path: Path, capsys):
    root = _init(tmp_path, with_types="hazard")
    hazard = root / ".specflow" / "schema" / "hazard.yaml"
    hazard.write_text(hazard.read_text() + "\n# local drift\n")
    capsys.readouterr()

    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True, "with_types": "hazard"}) == 0
    assert "# local drift" in hazard.read_text(), "merge mode keeps the edit"
    assert "already installed" in capsys.readouterr().out

    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True, "with_types": "hazard", "force": True}) == 0
    assert "# local drift" not in hazard.read_text()
    assert "reset to the shipped schema" in capsys.readouterr().out


def test_unknown_optional_type_lists_available_dynamically(tmp_path: Path, capsys):
    root = tmp_path / "p"
    root.mkdir()
    rc = init_cmd.run(root, {"platform": "claude-code", "no_ci": True, "with_types": "nope"})
    assert rc == 1
    assert "available: control, hazard, risk" in capsys.readouterr().out


# ── F-127 ────────────────────────────────────────────────────────────────────

def test_codex_and_junie_share_one_install_code():
    assert plat_lib.get_skills_install_code("junie") == "codex"
    assert plat_lib.get_skills_install_code("codex") == "codex"
    assert plat_lib.unique_skill_install_codes(["codex", "junie"]) == ["codex"]
    assert plat_lib.get_skills_install_code("claude-code") == "claude-code"
    assert plat_lib.get_skills_install_code("opencode") == "claude-code"


def test_codex_plus_junie_install_once_without_warning(tmp_path: Path, capsys):
    root = tmp_path / "p"
    root.mkdir()
    (root / ".codex").mkdir()
    (root / ".junie").mkdir()

    assert init_cmd.run(root, {"no_ci": True}) == 0
    out = capsys.readouterr().out
    assert "Multiple AI-host platforms detected" not in out
    assert init_cmd._multi_platform_warning(root, "codex", False) is None
    assert plat_lib.leftover_specflow_skills(root, "junie") == []
    assert plat_lib.leftover_specflow_skills(root, "codex") == []
    assert (root / ".agents" / "skills" / "specflow-init" / "SKILL.md").is_file()

    assert refresh_cmd.run(root, {"all_platforms": True}) == 0
    out = capsys.readouterr().out
    assert "shared with codex (.agents/skills)" in out
    assert "(.claude/skills)" not in out
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    assert agents.count(_BASE_START) == 1, "AGENTS.md must hold one base block, not one per host"


# ── F-130 ────────────────────────────────────────────────────────────────────

def test_refresh_cleans_legacy_dir_even_when_skills_current(tmp_path: Path, capsys):
    root = _init(tmp_path)
    legacy = root / ".claude" / "commands"
    legacy.mkdir(parents=True)
    (legacy / "specflow-x.md").write_text("old\n")
    (legacy / "mine.md").write_text("user\n")
    capsys.readouterr()

    assert refresh_cmd.run(root, {"platform": "claude-code", "dry_run": True}) == 0
    out = capsys.readouterr().out
    assert "skills: up to date" in out
    assert "skills-legacy: would remove .claude/commands/specflow-x.md" in out
    assert (legacy / "specflow-x.md").exists(), "dry-run must not delete"

    assert refresh_cmd.run(root, {"platform": "claude-code"}) == 0
    out = capsys.readouterr().out
    assert "skills-legacy: removed .claude/commands/specflow-x.md" in out
    assert not (legacy / "specflow-x.md").exists()
    assert (legacy / "mine.md").exists()

    assert refresh_cmd.run(root, {"platform": "claude-code"}) == 0
    assert "skills-legacy" not in capsys.readouterr().out, "no row when nothing to remove"


def test_refresh_no_skills_skips_legacy_cleanup(tmp_path: Path, capsys):
    root = _init(tmp_path)
    legacy = root / ".claude" / "commands"
    legacy.mkdir(parents=True)
    (legacy / "specflow-x.md").write_text("old\n")
    capsys.readouterr()

    assert refresh_cmd.run(root, {"platform": "claude-code", "no_skills": True}) == 0
    assert (legacy / "specflow-x.md").exists()
    assert "skills-legacy" not in capsys.readouterr().out


def test_healthy_consumer_refresh_has_no_new_rows(tmp_path: Path, capsys):
    """No-cry-wolf guard: a freshly initialised project prints only the
    established rows on a plain refresh."""
    root = _init(tmp_path)
    capsys.readouterr()
    assert refresh_cmd.run(root, {"platform": "claude-code"}) == 0
    out = capsys.readouterr().out
    for noisy in ("skills-legacy", "backups in", "preserved", "malformed"):
        assert noisy not in out, out
