"""Tests for `specflow phase-set` — reverse-lifecycle accounting.

Covers lib.learning.set_phase() directly and the command wrapper
(commands/phase_set.py), following the fixture style of test_phase_machine.py.
"""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.lib import config as config_lib
from specflow.lib.learning import set_phase
from specflow.commands import phase_set as phase_set_cmd


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / ".specflow").mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump({"project": {"name": "phase-set-test"}, "artifact_types": ["requirement"]}),
        encoding="utf-8",
    )
    for subdir in ["_specflow/specs/requirements", "_specflow/work/stories"]:
        (root / subdir).mkdir(parents=True, exist_ok=True)
    return root


def _set_state(root: Path, phase: str, extra: dict | None = None) -> None:
    state = {"current": phase, "history": [{"phase": phase, "entered": "2026-01-01"}]}
    if extra:
        state.update(extra)
    (root / ".specflow" / "state.yaml").write_text(yaml.dump(state), encoding="utf-8")


class TestSetPhaseLib:
    def test_forward_transition(self, project_root: Path):
        _set_state(project_root, "planning")
        result = set_phase(project_root, "executing")
        assert result["ok"] is True
        assert result["old_phase"] == "planning"
        assert result["new_phase"] == "executing"
        assert result["rewind"] is False
        state = config_lib.read_state(project_root)
        assert state["current"] == "executing"

    def test_rewind_records_history_and_clears_execution(self, project_root: Path):
        _set_state(project_root, "executing", extra={"execution": {"wave": 2}})
        result = set_phase(project_root, "specifying", reason="requirements were wrong")
        assert result["ok"] is True
        assert result["rewind"] is True

        state = config_lib.read_state(project_root)
        assert state["current"] == "specifying"
        assert "execution" not in state

        # Old phase entry stamped exited.
        old_entries = [e for e in state["history"] if e.get("phase") == "executing"]
        assert any("exited" in e for e in old_entries)

        # New phase entry carries reason + rewind flag.
        new_entries = [e for e in state["history"] if e.get("phase") == "specifying" and "exited" not in e]
        assert len(new_entries) == 1
        assert new_entries[0]["reason"] == "requirements were wrong"
        assert new_entries[0]["rewind"] is True

    def test_forward_transition_has_no_rewind_flag(self, project_root: Path):
        _set_state(project_root, "planning")
        set_phase(project_root, "executing")
        state = config_lib.read_state(project_root)
        new_entries = [e for e in state["history"] if e.get("phase") == "executing" and "exited" not in e]
        assert len(new_entries) == 1
        assert "rewind" not in new_entries[0]

    def test_invalid_phase(self, project_root: Path):
        _set_state(project_root, "planning")
        result = set_phase(project_root, "bogus-phase")
        assert result["ok"] is False
        assert "bogus-phase" in result["error"]
        # Valid phases are listed so the caller can self-correct.
        assert "idle" in result["error"]

        # State is untouched.
        state = config_lib.read_state(project_root)
        assert state["current"] == "planning"

    def test_same_phase_is_noop(self, project_root: Path):
        _set_state(project_root, "planning")
        result = set_phase(project_root, "planning")
        assert result["ok"] is True
        assert result["old_phase"] == "planning"
        assert result["new_phase"] == "planning"
        assert result["rewind"] is False


class TestPhaseSetCommand:
    def test_forward_prints_arrow(self, project_root: Path, capsys):
        _set_state(project_root, "planning")
        rc = phase_set_cmd.run(project_root, {"phase": "executing", "reason": None})
        assert rc == 0
        out = capsys.readouterr().out
        assert "planning" in out and "executing" in out
        assert "brief --next" in out

    def test_rewind_note_in_output(self, project_root: Path, capsys):
        _set_state(project_root, "executing")
        rc = phase_set_cmd.run(project_root, {"phase": "discovering", "reason": "rethink reqs"})
        assert rc == 0
        out = capsys.readouterr().out
        assert "rewind" in out.lower()
        assert "rethink reqs" in out

    def test_invalid_phase_exits_nonzero(self, project_root: Path, capsys):
        _set_state(project_root, "planning")
        rc = phase_set_cmd.run(project_root, {"phase": "not-a-phase", "reason": None})
        assert rc == 1
        out = capsys.readouterr().out
        assert "Unknown phase" in out or "not-a-phase" in out

    def test_same_phase_is_friendly_noop(self, project_root: Path, capsys):
        _set_state(project_root, "planning")
        rc = phase_set_cmd.run(project_root, {"phase": "planning", "reason": None})
        assert rc == 0
        out = capsys.readouterr().out
        assert "no change" in out.lower() or "already" in out.lower()

    def test_not_initialized(self, tmp_path: Path, capsys):
        rc = phase_set_cmd.run(tmp_path, {"phase": "planning", "reason": None})
        assert rc == 1
        out = capsys.readouterr().out
        assert "not initialized" in out.lower()
