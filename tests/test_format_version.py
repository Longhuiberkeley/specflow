"""STORY-678 — format_version stamped on init and refresh, read-side warning,
pre-commit hook format guard."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import specflow
from specflow import cli
from specflow.commands import hook as hook_cmd
from specflow.commands import init as init_cmd
from specflow.commands import refresh as refresh_cmd
from specflow.lib import config as config_lib

UPGRADE = "uv tool install --force git+https://github.com/Longhuiberkeley/specflow"


@pytest.fixture(autouse=True)
def _reset_warned():
    config_lib._FORMAT_WARNED.clear()
    yield
    config_lib._FORMAT_WARNED.clear()


def _cfg(root: Path) -> dict:
    return yaml.safe_load((root / ".specflow" / "config.yaml").read_text())


def _write_cfg(root: Path, cfg: dict) -> None:
    (root / ".specflow").mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(cfg, sort_keys=False))


def test_supported_format_version_is_integer_one():
    assert config_lib.SUPPORTED_FORMAT_VERSION == 1
    assert isinstance(config_lib.SUPPORTED_FORMAT_VERSION, int)


# ── AC1: init + refresh stamp ────────────────────────────────────────────────

def test_init_stamps_format_version_and_keeps_version(tmp_path: Path):
    root = tmp_path / "p"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    cfg = _cfg(root)
    assert cfg["format_version"] == 1
    assert cfg["version"] == specflow.__version__


def test_reinit_stamps_format_version_on_legacy_config(tmp_path: Path):
    root = tmp_path / "p"
    root.mkdir()
    _write_cfg(root, {"version": "1.0.0", "project": {"name": "p"}})
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    assert _cfg(root)["format_version"] == 1


def test_refresh_stamps_format_version_without_touching_version(tmp_path: Path):
    root = tmp_path / "p"
    (root / ".claude").mkdir(parents=True)
    body = "# user comment kept\nversion: 1.2.3\nproject:\n  name: p\nactive_packs: []\n"
    (root / ".specflow").mkdir()
    (root / ".specflow" / "config.yaml").write_text(body)

    assert refresh_cmd.run(root, {"no_skills": True, "no_context": True}) == 0

    text = (root / ".specflow" / "config.yaml").read_text()
    cfg = yaml.safe_load(text)
    assert cfg["format_version"] == 1
    assert cfg["version"] == "1.2.3", "refresh must not restamp the legacy version key"
    assert "# user comment kept" in text, "stamp is a minimal text edit"


def test_refresh_dry_run_reports_but_does_not_stamp(tmp_path: Path, capsys):
    root = tmp_path / "p"
    (root / ".claude").mkdir(parents=True)
    _write_cfg(root, {"version": "1.2.3", "active_packs": []})

    assert refresh_cmd.run(root, {"dry_run": True, "no_skills": True, "no_context": True}) == 0

    assert "format_version" not in _cfg(root)
    assert "format_version" in capsys.readouterr().out


def test_stamp_never_downgrades(tmp_path: Path):
    root = tmp_path / "p"
    _write_cfg(root, {"version": "9.0.0", "format_version": 7})
    assert config_lib.stamp_format_version(root) is False
    assert _cfg(root)["format_version"] == 7


# ── AC2: read-side warning ───────────────────────────────────────────────────

def test_mismatch_message_names_exact_upgrade(tmp_path: Path):
    root = tmp_path / "p"
    _write_cfg(root, {"format_version": 2})
    msg = config_lib.format_version_mismatch(root)
    assert msg is not None
    assert UPGRADE in msg
    assert "2" in msg and "1" in msg


def test_no_mismatch_for_current_or_missing(tmp_path: Path):
    root = tmp_path / "p"
    _write_cfg(root, {"format_version": 1})
    assert config_lib.format_version_mismatch(root) is None
    _write_cfg(root, {"version": "1.0.0"})
    assert config_lib.format_version_mismatch(root) is None
    assert config_lib.format_version_mismatch(tmp_path / "nowhere") is None


def test_cli_warns_once_on_newer_format(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "p"
    _write_cfg(root, {"format_version": 2, "active_packs": []})
    monkeypatch.chdir(root)

    cli.main(["transitions", "STORY-001"])
    cli.main(["transitions", "STORY-001"])

    err = capsys.readouterr().err
    assert err.count(UPGRADE) == 1


def test_cli_silent_on_supported_format(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "p"
    _write_cfg(root, {"format_version": 1, "active_packs": []})
    monkeypatch.chdir(root)
    cli.main(["transitions", "STORY-001"])
    assert UPGRADE not in capsys.readouterr().err


# ── AC3: hook refusal ────────────────────────────────────────────────────────

def test_pre_commit_refuses_on_newer_format(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    _write_cfg(root, {"format_version": 2})

    def boom(*a, **k):  # no stale check may run
        raise AssertionError("pre-commit ran checks despite a format mismatch")

    monkeypatch.setattr(hook_cmd.rbac_lib, "staged_artifact_changes", boom)
    monkeypatch.setattr(hook_cmd.subprocess, "run", boom)

    rc = hook_cmd._pre_commit(root)
    out = capsys.readouterr().out
    assert rc != 0
    assert UPGRADE in out


def test_pre_commit_proceeds_on_supported_format(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    _write_cfg(root, {"format_version": 1})
    monkeypatch.setattr(hook_cmd.rbac_lib, "current_git_author_email", lambda r: "a@b.com")
    monkeypatch.setattr(hook_cmd.rbac_lib, "staged_artifact_changes", lambda r: [])
    assert hook_cmd._pre_commit(root) == 0


# ── CLI-level (integration) ─────────────────────────────────────────────────

def test_cli_hook_pre_commit_refuses_newer_format(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    _write_cfg(root, {"format_version": 2})
    monkeypatch.chdir(root)

    rc = cli.main(["hook", "pre-commit"])

    captured = capsys.readouterr()
    assert rc == 1
    assert UPGRADE in captured.out
    assert UPGRADE not in captured.err, "hook refusal is not double-reported"


def test_cli_init_then_refresh_keep_format_version(tmp_path: Path, monkeypatch):
    root = tmp_path / "p"
    root.mkdir()
    monkeypatch.chdir(root)
    assert cli.main(["init", "--platform", "claude-code", "--no-ci"]) == 0
    assert _cfg(root)["format_version"] == 1
    assert cli.main(["refresh"]) == 0
    assert _cfg(root)["format_version"] == 1
