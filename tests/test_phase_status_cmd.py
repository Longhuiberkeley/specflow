"""`specflow phase-status` behaviour (STORY-718).

The advisory never blocks: it exits 0 whatever it finds and only exits 1 when
SpecFlow is not initialised. Suspects and a failing gate are surfaced as
"blocked on", never acted on.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from conftest import write_artifact

from specflow import cli
from specflow.commands import init as init_cmd
from specflow.commands import phase_status as phase_status_cmd
from specflow.lib import artifacts as art_lib

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    return _ANSI.sub("", text)


@pytest.fixture
def project(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "p"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    monkeypatch.chdir(root)
    return root


def test_uninitialised_directory_exits_one(tmp_path: Path, capsys):
    assert phase_status_cmd.run(tmp_path, {}) == 1
    assert "not initialized" in _plain(capsys.readouterr().out)


def test_fresh_project_reports_phase_counts_wave_and_advisory(project: Path, capsys):
    write_artifact(project, "REQ-001", "requirement", "Login", status="approved")
    write_artifact(project, "STORY-001", "story", "Build login", status="approved",
                   links=[{"target": "REQ-001", "role": "implements"}])
    write_artifact(project, "STORY-002", "story", "Later", status="draft")

    assert cli.main(["phase-status"]) == 0
    out = _plain(capsys.readouterr().out)
    assert "SpecFlow Phase Status" in out and "phase: idle" in out
    assert "approved: 2" in out and "draft: 1" in out
    assert "No unresolved suspects" in out
    assert "Next executable wave: 1 story(ies) — STORY-001" in out
    assert "Phase gate (idle)" in out
    assert "Advisory" in out
    assert "Suggested next phase: discovering" in out


def test_open_suspects_block_the_advisory_but_not_the_exit_code(project: Path, capsys):
    write_artifact(project, "REQ-001", "requirement", "Login", status="approved")
    res = art_lib.update_artifact(project, "REQ-001", suspect=True)
    assert res.get("ok"), res

    assert cli.main(["phase-status"]) == 0
    out = _plain(capsys.readouterr().out)
    assert "Suspects open: 1" in out and "REQ-001" in out
    assert "Not ready to close — blocked on: 1 suspect(s) open" in out
    assert "Next executable wave: (none ready)" in out


def test_gate_failure_is_advisory_only(project: Path, monkeypatch, capsys):
    monkeypatch.setattr(phase_status_cmd, "_gate_result", lambda root, phase: (False, "FAIL: 1 blocking"))
    assert cli.main(["phase-status"]) == 0
    out = _plain(capsys.readouterr().out)
    assert "not green" in out and "FAIL: 1 blocking" in out
    assert "blocked on: phase gate (idle) not green" in out


def test_gate_pass_and_no_suspects_is_ready_to_close(project: Path, monkeypatch, capsys):
    monkeypatch.setattr(phase_status_cmd, "_gate_result", lambda root, phase: (True, "PASS"))
    assert cli.main(["phase-status"]) == 0
    out = _plain(capsys.readouterr().out)
    assert "green (automated blocking checks pass)" in out
    assert "Ready to close — run `specflow done`" in out
