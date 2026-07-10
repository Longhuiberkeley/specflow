"""Tests for the specflow brief one-call recall digest."""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.commands import brief as brief_cmd
from specflow.lib import artifacts as art_lib

_STD_FLOW = {"draft": [], "approved": ["draft"], "implemented": ["approved"], "verified": ["implemented"]}
_SCHEMA_TYPES = [("requirement", "REQ"), ("architecture", "ARCH"), ("story", "STORY")]


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    for art_type, prefix in _SCHEMA_TYPES:
        schema = {"type": art_type, "prefix": prefix, "allowed_status": dict(_STD_FLOW), "category": "spec" if prefix != "STORY" else "work"}
        (schema_dir / f"{art_type}.yaml").write_text(yaml.dump(schema), encoding="utf-8")
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump({"project": {"name": "brief-test", "created": "2026-01-01"}, "artifact_types": [t for t, _ in _SCHEMA_TYPES], "active_packs": []}),
        encoding="utf-8",
    )
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "planning", "history": []}), encoding="utf-8"
    )
    for subdir in ["_specflow/specs/requirements", "_specflow/specs/architecture", "_specflow/work/stories"]:
        (root / subdir).mkdir(parents=True, exist_ok=True)
    return root


def test_brief_uninitialized_returns_error(tmp_path: Path, capsys):
    rc = brief_cmd.run(tmp_path, {})
    assert rc == 1
    assert "not initialized" in capsys.readouterr().out


def test_brief_runs_and_reports_phase_and_inventory(project_root: Path, capsys):
    art_lib.create_artifact(project_root, "requirement", title="A req", status="approved", body="b")
    art_lib.create_artifact(project_root, "story", title="A story", status="draft", body="b")
    rc = brief_cmd.run(project_root, {})
    out = capsys.readouterr().out
    assert rc == 0
    assert "brief-test" in out
    assert "planning" in out
    assert "Inventory" in out
    assert "No unresolved suspects" in out


# --- next-skill recommendation: execute → artifact-review → ship (not execute → ship) ---

from types import SimpleNamespace


def _art(artifact_id: str, status: str) -> SimpleNamespace:
    """Minimal artifact stub for the pure recommendation function."""
    return SimpleNamespace(id=artifact_id, status=status, suspect=False)


def test_next_skill_routes_through_artifact_review_before_ship():
    """All stories implemented, not yet reviewed → insert /specflow-artifact-review before ship.

    Guards the rank-1 fix: the deterministic router used to jump from 'all implemented'
    straight to /specflow-ship, silently dropping the artifact-review lifecycle step.
    """
    artifacts = [_art("STORY-001", "implemented"), _art("STORY-002", "implemented")]
    out = brief_cmd._next_skill_recommendation("executing", artifacts, [], [])
    assert "/specflow-artifact-review" in out
    assert "/specflow-ship" in out


def test_next_skill_skips_to_ship_when_reviewed():
    """All stories implemented AND V-model tests already exist → go straight to ship."""
    artifacts = [_art("STORY-001", "implemented"), _art("UT-001", "approved")]
    out = brief_cmd._next_skill_recommendation("executing", artifacts, [], [])
    assert "/specflow-ship" in out
    assert "/specflow-artifact-review" not in out


def test_next_skill_still_points_at_execute_when_wave_ready():
    """A pending next wave still routes to /specflow-execute (regression guard)."""
    artifacts = [_art("STORY-001", "approved")]
    out = brief_cmd._next_skill_recommendation("executing", artifacts, [], ["STORY-001"])
    assert "/specflow-execute" in out
