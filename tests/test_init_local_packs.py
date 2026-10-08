"""STORY-681 — init and refresh resolve project-local packs before bundled packs."""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow import cli
from specflow.commands import init as init_cmd
from specflow.commands import refresh as refresh_cmd
from specflow.lib import config as config_lib
from specflow.lib import scaffold as scaffold_lib

_SNIPPET = "### Local pack\nLocal guidance line."


def _write_local_pack(root: Path, name: str, *, checklist_text: str = "v1") -> Path:
    pack = root / ".specflow" / "packs" / name
    (pack / "schemas").mkdir(parents=True)
    (pack / "checklists" / "review").mkdir(parents=True)
    (pack / "standards").mkdir(parents=True)
    (pack / "skills" / "specflow-localpack").mkdir(parents=True)
    (pack / "pack.yaml").write_text(yaml.dump({
        "name": name,
        "version": "0.1.0",
        "description": "temporary local pack",
        "adds_artifact_types": ["local-thing"],
        "adds_skills": ["specflow-localpack"],
        "context_snippet": _SNIPPET,
    }, sort_keys=False))
    (pack / "schemas" / "local-thing.yaml").write_text(
        "type: local-thing\nid_prefix: LT\ndirectory: _specflow/specs/local-things/\n"
    )
    (pack / "checklists" / "review" / "local-review.yaml").write_text(
        f"name: local-review\nnote: {checklist_text}\nitems: []\n"
    )
    (pack / "standards" / "local-std.yaml").write_text("id: LOCAL-STD\nclauses: []\n")
    (pack / "skills" / "specflow-localpack" / "SKILL.md").write_text("# local pack skill\n")
    return pack


def test_resolve_prefers_local_over_bundled(tmp_path: Path):
    root = tmp_path / "p"
    _write_local_pack(root, "ops")  # shadow a bundled name
    assert scaffold_lib.resolve_packs_dir(root, "ops") == root / ".specflow" / "packs"
    assert scaffold_lib.resolve_packs_dir(root, "tldr-communication") == scaffold_lib.bundled_packs_dir()


def test_resolve_ignores_local_dir_without_manifest(tmp_path: Path):
    root = tmp_path / "p"
    (root / ".specflow" / "packs" / "ops").mkdir(parents=True)
    assert scaffold_lib.resolve_packs_dir(root, "ops") == scaffold_lib.bundled_packs_dir()


def test_init_preset_installs_local_pack(tmp_path: Path):
    root = tmp_path / "p"
    root.mkdir()
    _write_local_pack(root, "mylocal")

    rc = init_cmd.run(root, {"platform": "claude-code", "preset": "mylocal", "no_ci": True})

    assert rc == 0
    assert (root / ".specflow" / "schema" / "local-thing.yaml").exists()
    assert (root / ".specflow" / "standards" / "local-std.yaml").exists()
    assert (root / ".claude" / "skills" / "specflow-localpack" / "SKILL.md").exists()
    cfg = config_lib.read_config(root)
    assert "mylocal" in cfg["active_packs"]
    assert "local-thing" in cfg["artifact_types"]
    assert "Local guidance line." in (root / "AGENTS.md").read_text()
    # Pack-first flow: `.specflow/` existed (only packs/) before init — the
    # project must still end up initialised with a state.yaml.
    assert (root / ".specflow" / "state.yaml").exists()
    assert config_lib.read_state(root)


def test_reinit_backfills_missing_state(tmp_path: Path):
    root = tmp_path / "p"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    (root / ".specflow" / "state.yaml").unlink()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    assert (root / ".specflow" / "state.yaml").exists()


def test_refresh_packs_applies_local_pack_changes(tmp_path: Path):
    root = tmp_path / "p"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    # Already-initialised project: install the local pack via re-init merge
    # mode, then evolve the pack and sync it with refresh --packs.
    pack = _write_local_pack(root, "mylocal")
    assert init_cmd.run(root, {"platform": "claude-code", "preset": "mylocal", "no_ci": True}) == 0
    (pack / "checklists" / "review" / "local-review.yaml").write_text(
        "name: local-review\nnote: v2\nitems: []\n"
    )
    (pack / "schemas" / "local-extra.yaml").write_text("type: local-extra\n")
    # F-103: standards/ is part of the sync too.
    (pack / "standards" / "local-std.yaml").write_text("id: LOCAL-STD\nclauses: [edited]\n")

    rc = refresh_cmd.run(root, {"platform": "claude-code", "packs": True, "force": True})

    assert rc == 0
    assert "v2" in (root / ".specflow" / "checklists" / "review" / "local-review.yaml").read_text()
    assert (root / ".specflow" / "schema" / "local-extra.yaml").exists()
    assert "edited" in (root / ".specflow" / "standards" / "local-std.yaml").read_text()


def test_refresh_packs_dry_run_resolves_local_pack(tmp_path: Path, capsys):
    root = tmp_path / "p"
    root.mkdir()
    _write_local_pack(root, "mylocal")
    assert init_cmd.run(root, {"platform": "claude-code", "preset": "mylocal", "no_ci": True}) == 0
    capsys.readouterr()

    assert refresh_cmd.run(root, {"platform": "claude-code", "packs": True, "dry_run": True}) == 0

    out = capsys.readouterr().out
    assert "pack:mylocal" in out
    assert "not found" not in out


def test_cli_init_preset_local_pack(tmp_path: Path, monkeypatch):
    root = tmp_path / "p"
    root.mkdir()
    _write_local_pack(root, "mylocal")
    monkeypatch.chdir(root)
    assert cli.main(["init", "--platform", "claude-code", "--preset", "mylocal", "--no-ci"]) == 0
    assert cli.main(["refresh", "--packs"]) == 0
    assert "mylocal" in config_lib.read_config(root)["active_packs"]
