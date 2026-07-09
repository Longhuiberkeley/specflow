"""Tests for the lifecycle phase machine — `close_phase` advancing `current`.

Covers the REQ-004 §6 / ARCH-002 accounting behavior: closing a phase records
the advance of `current` to the next phase (accounting, never a gate/block).
"""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.lib import config as config_lib
from specflow.lib.learning import PHASE_ORDER, close_phase, next_phase


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / ".specflow").mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump({"project": {"name": "phase-test"}, "artifact_types": ["requirement"]}),
        encoding="utf-8",
    )
    for subdir in ["_specflow/specs/requirements", "_specflow/work/stories"]:
        (root / subdir).mkdir(parents=True, exist_ok=True)
    return root


def _set_phase(root: Path, phase: str) -> None:
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": phase, "history": [{"phase": phase, "entered": "2026-01-01"}]}),
        encoding="utf-8",
    )


def test_next_phase_walks_the_chain():
    assert next_phase("idle") == "discovering"
    assert next_phase("planning") == "executing"
    assert next_phase("executing") == "verifying"
    assert next_phase("verifying") == "complete"


def test_next_phase_terminal_and_unknown_are_noops():
    assert next_phase("complete") == "complete"  # terminal: stay
    assert next_phase("bogus") == "bogus"        # unknown: don't invent


def test_close_phase_advances_current(project_root: Path):
    _set_phase(project_root, "planning")
    result = close_phase(project_root)
    assert result["ok"] is True
    assert result["phase_closed"] == "planning"
    assert result["phase_entered"] == "executing"
    state = config_lib.read_state(project_root)
    assert state["current"] == "executing"


def test_close_phase_records_entered_history_for_new_phase(project_root: Path):
    _set_phase(project_root, "executing")
    close_phase(project_root)
    state = config_lib.read_state(project_root)
    # The new phase ('verifying') must have an entered history entry without an exit.
    entered = [e for e in state["history"] if e.get("phase") == "verifying"]
    assert len(entered) == 1
    assert "entered" in entered[0]
    assert "exited" not in entered[0]


def test_close_phase_marks_old_phase_exited(project_root: Path):
    _set_phase(project_root, "planning")
    close_phase(project_root)
    state = config_lib.read_state(project_root)
    planning_entries = [e for e in state["history"] if e.get("phase") == "planning"]
    assert any("exited" in e for e in planning_entries)


def test_close_phase_at_complete_stays_put(project_root: Path):
    _set_phase(project_root, "complete")
    result = close_phase(project_root)
    assert result["phase_closed"] == "complete"
    assert result["phase_entered"] == "complete"
    assert config_lib.read_state(project_root)["current"] == "complete"


def test_phase_order_is_canonical_seven_phases():
    assert PHASE_ORDER == [
        "idle", "discovering", "specifying", "planning",
        "executing", "verifying", "complete",
    ]
