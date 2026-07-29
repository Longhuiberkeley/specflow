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


# --- Knowledge-surfaces block: makes BP/PREV dormancy visible ---

def _bp_art(bp_id: str, status: str = "approved") -> art_lib.Artifact:
    return art_lib.Artifact(
        path=Path(f"/fake/{bp_id}.md"),
        frontmatter={"id": bp_id, "title": f"BP {bp_id}", "type": "best-practice",
                      "status": status, "tags": ["core"]},
        body="## Verification\nDo the thing",
    )


def test_knowledge_summary_reports_all_empty_surfaces(tmp_path: Path):
    summary = brief_cmd._knowledge_summary(tmp_path, [])
    assert summary["bp_total"] == 0
    assert summary["prev_count"] == 0
    assert summary["find_count"] == 0
    assert summary["chl_open"] == 0
    assert any("no active/approved BPs" in hint for hint in summary["hints"])
    assert any("0 PREV" in hint for hint in summary["hints"])


def test_brief_renders_empty_knowledge_surfaces(project_root: Path, capsys):
    assert brief_cmd.run(project_root, {}) == 0
    out = capsys.readouterr().out
    assert "Knowledge surfaces" in out
    assert "BP 0 (none)" in out
    assert "PREV 0" in out
    assert "FIND 0" in out
    assert "CHL 0 open / 0 done" in out


def test_brief_discovers_artifacts_once(project_root: Path, monkeypatch):
    original = art_lib.discover_artifacts
    calls = 0

    def counted(root: Path, artifact_type: str | None = None):
        nonlocal calls
        calls += 1
        return original(root, artifact_type)

    monkeypatch.setattr(art_lib, "discover_artifacts", counted)
    assert brief_cmd.run(project_root, {}) == 0
    assert calls == 1


def test_knowledge_summary_reports_bp_and_prev_dormancy(tmp_path: Path):
    from specflow.lib import learning as learn_lib

    arts = [_bp_art("BP-001")]
    # No PREV yet -> dormancy hint for PREV fires; approved BP means no BP-dormancy hint.
    s = brief_cmd._knowledge_summary(tmp_path, arts)
    assert s is not None
    assert s["bp_total"] == 1
    assert s["prev_count"] == 0
    assert any("PREV" in h for h in s["hints"])
    assert not any("no active/approved BPs" in h for h in s["hints"])

    # Add a PREV via the blessed path -> prev_count rises, PREV hint clears.
    story = art_lib.Artifact(
        path=Path("/fake/STORY-1.md"),
        frontmatter={"id": "STORY-001", "type": "story", "tags": ["core"]},
        body="",
    )
    learn_lib.persist_prevention_pattern(
        tmp_path,
        learn_lib.extract_prevention_pattern(story, "Prevent X", "Verify that X holds"),
    )
    s2 = brief_cmd._knowledge_summary(tmp_path, arts)
    assert s2["prev_count"] == 1
    assert not any("PREV" in h for h in s2["hints"])


def test_brief_knowledge_bp_dormancy_hint_when_no_active_bp(tmp_path: Path):
    # Only a draft BP -> "no active/approved BPs" hint fires.
    s = brief_cmd._knowledge_summary(tmp_path, [_bp_art("BP-009", status="draft")])
    assert s is not None
    assert any("no active/approved BPs" in h for h in s["hints"])



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


def test_next_skill_backlog_advisory_on_rewind():
    """A rewind to 'specifying' that leaves implemented stories in the backlog
    appends an advisory pointing at /specflow-execute — the primary /specflow-plan
    line alone looks nonsensical when 61 stories are already implemented."""
    artifacts = [_art(f"STORY-00{i}", "implemented") for i in range(1, 5)]
    out = brief_cmd._next_skill_recommendation("specifying", artifacts, [], ["STORY-001"])
    assert "/specflow-plan" in out  # primary line unchanged
    assert "remain implemented after rewind" in out
    assert "/specflow-execute" in out


def test_next_skill_no_backlog_advisory_when_clean():
    """specifying with no implemented backlog → no rewind advisory noise."""
    artifacts = [_art("REQ-001", "approved")]
    out = brief_cmd._next_skill_recommendation("specifying", artifacts, [], ["STORY-001"])
    assert "remain implemented after rewind" not in out


def test_next_skill_backlog_advisory_fires_without_next_wave():
    """The advisory keys off backlog presence, NOT next_wave. The motivating
    case — a rewound project with a deep implemented backlog and nothing newly
    queued — has an empty next_wave and must still fire (next_wave only ever
    holds *approved* stories, so gating on it silenced exactly this case)."""
    artifacts = [_art(f"STORY-00{i}", "implemented") for i in range(1, 5)]
    out = brief_cmd._next_skill_recommendation("specifying", artifacts, [], [])  # empty next_wave
    assert "remain implemented after rewind" in out
    assert "/specflow-execute" in out


def test_next_skill_backlog_all_verified_points_at_review():
    """An all-verified backlog wants artifact-review/ship, not more execute."""
    artifacts = [_art(f"STORY-00{i}", "verified") for i in range(1, 5)]
    out = brief_cmd._next_skill_recommendation("planning", artifacts, [], [])
    assert "remain implemented after rewind" in out
    assert "/specflow-artifact-review" in out


# --- health nags (D2) ---

def test_health_nags_domain_unset(tmp_path: Path):
    nags = brief_cmd._health_nags(tmp_path, {"project": {}}, [], None)
    assert any("domain not set" in n for n in nags)


def test_health_nags_clean_when_healthy(tmp_path: Path):
    nags = brief_cmd._health_nags(tmp_path, {"project": {"domain": "quant"}}, [], None)
    assert nags == []


def test_health_nags_stale_fingerprint(tmp_path: Path):
    art = art_lib.Artifact(
        path=Path("REQ-001.md"),
        frontmatter={"id": "REQ-001", "fingerprint": "sha256:deadbeefdead"},
        body="real body content that hashes differently",
    )
    nags = brief_cmd._health_nags(tmp_path, {"project": {"domain": "quant"}}, [art], None)
    assert any("fingerprint(s) stale" in n for n in nags)


def test_health_nags_adoption_handshake_incomplete(tmp_path: Path):
    """Adoption started (backfilled artifacts) but no baseline was ever cut —
    the one _health_nags branch that touches the filesystem."""
    nags = brief_cmd._health_nags(
        tmp_path, {"project": {"domain": "quant"}}, [],
        adoption={"backfilled_count": 5},
    )
    assert any("adoption handshake incomplete" in n for n in nags)


def test_health_nags_adoption_complete_with_baseline(tmp_path: Path):
    """Once a baseline exists, the adoption nag stays silent."""
    baselines = tmp_path / ".specflow" / "baselines"
    baselines.mkdir(parents=True)
    (baselines / "adoption-v0.yaml").write_text("entries: []\n", encoding="utf-8")
    nags = brief_cmd._health_nags(
        tmp_path, {"project": {"domain": "quant"}}, [],
        adoption={"backfilled_count": 5},
    )
    assert not any("adoption handshake" in n for n in nags)


def test_health_nags_no_adoption_nag_when_not_adopting(tmp_path: Path):
    """adoption=None (not an adopt project) → no adoption nag even with no baseline."""
    nags = brief_cmd._health_nags(tmp_path, {"project": {"domain": "quant"}}, [], None)
    assert not any("adoption handshake" in n for n in nags)
