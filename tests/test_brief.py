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
    line alone looks nonsensical when 61 stories are already implemented. Gated on
    a real rewind entry in history (set_phase stamps ``rewind: true``)."""
    artifacts = [_art(f"STORY-00{i}", "implemented") for i in range(1, 5)]
    history = [{"phase": "specifying", "entered": "2026-08-01", "rewind": True}]
    out = brief_cmd._next_skill_recommendation("specifying", artifacts, [], ["STORY-001"], history=history)
    assert "/specflow-plan" in out  # primary line unchanged
    assert "remain implemented after rewind" in out
    assert "/specflow-execute" in out


def test_next_skill_no_backlog_advisory_when_clean():
    """specifying with no implemented backlog → no rewind advisory noise.
    (Independent of history: done < 3 short-circuits before the rewind gate.)"""
    artifacts = [_art("REQ-001", "approved")]
    out = brief_cmd._next_skill_recommendation("specifying", artifacts, [], ["STORY-001"])
    assert "remain implemented after rewind" not in out


def test_next_skill_backlog_advisory_fires_without_next_wave():
    """The advisory keys off backlog presence, NOT next_wave. The motivating
    case — a rewound project with a deep implemented backlog and nothing newly
    queued — has an empty next_wave and must still fire (next_wave only ever
    holds *approved* stories, so gating on it silenced exactly this case).
    Gated on a real rewind entry in history."""
    artifacts = [_art(f"STORY-00{i}", "implemented") for i in range(1, 5)]
    history = [{"phase": "specifying", "entered": "2026-08-01", "rewind": True}]
    out = brief_cmd._next_skill_recommendation("specifying", artifacts, [], [], history=history)  # empty next_wave
    assert "remain implemented after rewind" in out
    assert "/specflow-execute" in out


def test_next_skill_backlog_all_verified_points_at_review():
    """An all-verified backlog wants artifact-review/ship, not more execute.
    Gated on a real rewind entry in history."""
    artifacts = [_art(f"STORY-00{i}", "verified") for i in range(1, 5)]
    history = [{"phase": "planning", "entered": "2026-08-01", "rewind": True}]
    out = brief_cmd._next_skill_recommendation("planning", artifacts, [], [], history=history)
    assert "remain implemented after rewind" in out
    assert "/specflow-artifact-review" in out


def test_next_skill_no_rewind_advisory_when_history_lacks_rewind():
    """A deep implemented backlog during specifying/planning but NO rewind entry
    in history → the 'after rewind' wording is a false positive (this repo's
    state.yaml has zero rewind entries). Stay silent."""
    artifacts = [_art(f"STORY-00{i}", "implemented") for i in range(1, 5)]
    history = [{"phase": "planning", "entered": "2026-08-01"}]  # no rewind key
    out = brief_cmd._next_skill_recommendation("specifying", artifacts, [], [], history=history)
    assert "remain implemented after rewind" not in out


def test_next_skill_no_rewind_advisory_when_state_has_no_history():
    """state has no history list at all (history=None default) → no rewind
    evidence → advisory silent even with a deep implemented backlog."""
    artifacts = [_art(f"STORY-00{i}", "implemented") for i in range(1, 5)]
    out = brief_cmd._next_skill_recommendation("specifying", artifacts, [], [])  # history defaults to None
    assert "remain implemented after rewind" not in out


# --- verification-contract advisory (v1.13): declared verify_command with no
#     matching verify_run evidence → one advisory line, never blocking ---

def _vart(artifact_id: str, status: str, frontmatter: dict | None = None) -> SimpleNamespace:
    """Artifact stub carrying a frontmatter dict (for verify-contract fields)."""
    return SimpleNamespace(id=artifact_id, status=status, suspect=False, frontmatter=frontmatter or {})


def test_next_skill_verify_advisory_fires_when_no_run_evidence():
    """An implemented UT that declares verify_command but has no verify_run_at
    surfaces a `specflow verify` advisory. Accounting — never blocking."""
    artifacts = [_vart("UT-001", "implemented", {"verify_command": "pytest tests/x.py"})]
    out = brief_cmd._next_skill_recommendation("executing", artifacts, [], [])
    assert "specflow verify" in out
    assert "UT-001" in out


def test_next_skill_verify_advisory_fires_on_exit_code_divergence():
    """Declared verify_exit_code=0 but recorded verify_run_exit_code=1 → the run
    diverged from the contract → recommend re-verifying (recorded, not blocking)."""
    artifacts = [_vart(
        "QT-003", "verified",
        {"verify_command": "./run.sh", "verify_exit_code": 0,
         "verify_run_at": "2026-08-01", "verify_run_exit_code": 1},
    )]
    out = brief_cmd._next_skill_recommendation("executing", artifacts, [], [])
    assert "specflow verify" in out
    assert "QT-003" in out


def test_next_skill_verify_advisory_silent_when_evidence_matches():
    """verify_run_exit_code equals declared verify_exit_code → contract satisfied,
    no advisory noise."""
    artifacts = [_vart(
        "STORY-010", "verified",
        {"verify_command": "pytest", "verify_exit_code": 0,
         "verify_run_at": "2026-08-01", "verify_run_exit_code": 0},
    )]
    out = brief_cmd._next_skill_recommendation("executing", artifacts, [], [])
    assert "specflow verify" not in out


def test_next_skill_verify_advisory_silent_without_verify_command():
    """No verify_command declared → the project doesn't use contracts → no noise.
    This is the guard that keeps the advisory invisible for ordinary projects."""
    artifacts = [_art("STORY-001", "implemented")]  # no frontmatter / no verify_command
    out = brief_cmd._next_skill_recommendation("executing", artifacts, [], [])
    assert "specflow verify" not in out


# --- auto-DEC de-pollution: change-record/audit DECs must not inflate the
#     unreviewed count, the blast-radius cone, or the "durable why" section ---

def _dec(
    dec_id: str,
    review_status: str = "unreviewed",
    tags: list[str] | None = None,
    body: str = "",
    title: str | None = None,
    dec_kind: str | None = None,
) -> SimpleNamespace:
    """Minimal DEC stub carrying frontmatter (review_status) + a tags attribute.

    `_is_auto_dec` reads ``a.tags``; on real Artifact that's a frontmatter-derived
    property, so the stub mirrors it as an explicit attribute. ``path`` points at a
    nonexistent file so _recent_decisions' mtime sort falls back to 0.0 (stable)."""
    fm: dict = {"id": dec_id, "review_status": review_status, "type": "decision"}
    if tags:
        fm["tags"] = tags
    if dec_kind:
        fm["dec_kind"] = dec_kind
    return SimpleNamespace(
        id=dec_id,
        status="approved",
        suspect=False,
        tags=tags or [],
        frontmatter=fm,
        body=body,
        title=title or f"Decision {dec_id}",
        links=[],
        path=Path(f"/fake/{dec_id}.md"),
    )


def test_auto_dec_excluded_from_unreviewed_count_and_cone(tmp_path):
    """An unreviewed DEC tagged change-record/auto-generated is an auto change
    record, not a human ADR — excluded from both the unreviewed count and the
    blast-radius cone, while a real unreviewed ADR is still surfaced."""
    auto_dec = _dec("DEC-001", tags=["change-record", "auto-generated"], body="auto change record")
    real_dec = _dec("DEC-002", tags=None, body="We chose X because Y")
    out = brief_cmd._next_skill_recommendation(
        "executing", [auto_dec, real_dec], [], [], root=tmp_path,
    )
    assert "DEC-002" in out  # real ADR still surfaced
    assert "DEC-001" not in out  # auto change record suppressed
    assert "1 unreviewed DEC" in out  # count excludes the auto one


def test_dec_kind_change_record_excluded_without_tags(tmp_path):
    """The explicit discriminator is authoritative even when tags are absent."""
    auto_dec = _dec("DEC-001", dec_kind="change_record", body="auto change record")
    real_adr = _dec("DEC-002", dec_kind="adr", body="We chose X because Y")
    out = brief_cmd._next_skill_recommendation(
        "executing", [auto_dec, real_adr], [], [], root=tmp_path,
    )
    assert "DEC-002" in out
    assert "DEC-001" not in out
    assert "1 unreviewed DEC" in out


def test_unreviewed_advisory_silent_when_every_dec_is_auto(tmp_path):
    """Every unreviewed DEC is auto-generated → no real review debt → advisory
    silent. This is the cry-wolf that inflated the count by ~49 auto records and
    made the blast-radius cone unusable."""
    auto_decs = [
        _dec("DEC-001", tags=["change-record", "auto-generated"]),
        _dec("DEC-002", tags=["project-audit", "auto-generated"]),
        _dec("DEC-003", tags=["auto-generated"]),
    ]
    out = brief_cmd._next_skill_recommendation(
        "executing", auto_decs, [], [], root=tmp_path,
    )
    assert "unreviewed DEC" not in out
    assert "blast radius" not in out


def test_recent_decisions_skips_auto_records():
    """Auto change records don't belong in 'the durable why' — filter them out
    so the section surfaces real ADRs."""
    auto = _dec("DEC-A1", tags=["change-record", "auto-generated"], body="bumped version")
    real = _dec("DEC-R1", tags=None, body="We chose X because Y")
    decs = brief_cmd._recent_decisions([auto, real])
    ids = [d[0] for d in decs]
    assert "DEC-R1" in ids
    assert "DEC-A1" not in ids


def test_recent_decisions_shows_few_real_adrs_without_padding():
    """Fewer real ADRs than the limit → show what's there; never pad the section
    with auto change records to reach the limit."""
    auto_decs = [_dec(f"DEC-A{i}", tags=["auto-generated"]) for i in range(12)]
    real = _dec("DEC-R1", tags=None, body="We chose X because Y")
    decs = brief_cmd._recent_decisions(auto_decs + [real])
    assert len(decs) == 1
    assert decs[0][0] == "DEC-R1"


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


# --- outcome-feedback note (v1.13): breached MONITOR with no DEF/informs →
#     route to `specflow defect-from-monitor`. Two-direction walk; ops-gated. ---

class _OLink:
    """Minimal link stub (target + role) for the pure graph queries."""

    def __init__(self, target: str, role: str) -> None:
        self.target = target
        self.role = role


def _mon(
    mon_id: str,
    status: str = "flagged",
    health: str | None = "breached",
    links: list[_OLink] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=mon_id, status=status, suspect=False,
        frontmatter={"health": health} if health is not None else {},
        links=links or [],
    )


def _def_stub(def_id: str, links: list[_OLink] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=def_id, status="open", suspect=False, frontmatter={}, links=links or [],
    )


def test_outcome_note_silent_on_non_ops_project():
    """No ops pack → never print (no cry-wolf on non-ops projects)."""
    mon = _mon("MON-001")
    assert brief_cmd._outcome_feedback_note([mon], active_packs=[]) == ""


def test_outcome_note_silent_with_no_monitors():
    """Ops active but zero MONITOR artifacts → silent."""
    out = brief_cmd._outcome_feedback_note(
        [SimpleNamespace(id="REQ-001", status="approved", suspect=False,
                         frontmatter={}, links=[])],
        active_packs=["ops"],
    )
    assert out == ""


def test_outcome_note_fires_for_breached_unlinked_monitor():
    """A flagged+breached MONITOR with no DEF backlink and no informs edge →
    'breach unaccountable', routed to defect-from-monitor."""
    mon = _mon("MON-001")
    out = brief_cmd._outcome_feedback_note([mon], active_packs=["ops"])
    assert "1 breached MONITOR(s)" in out
    assert "defect-from-monitor MON-001" in out
    assert "unaccountable" in out


def test_outcome_note_suppressed_by_def_backlink():
    """Backward direction: a DEF whose exposed_by points back at the MONITOR →
    accountable, no note (the two-direction walk must catch this)."""
    mon = _mon("MON-001")
    d = _def_stub("DEF-001", [_OLink("MON-001", "exposed_by")])
    out = brief_cmd._outcome_feedback_note([mon, d], active_packs=["ops"])
    assert "unaccountable" not in out


def test_outcome_note_suppressed_by_informs_edge():
    """Forward direction: the MONITOR's own outgoing `informs` edge records a
    follow-up → accountable, no note."""
    mon = _mon("MON-001", links=[_OLink("LOOP-001", "informs")])
    out = brief_cmd._outcome_feedback_note([mon], active_packs=["ops"])
    assert "unaccountable" not in out


def test_outcome_note_resolved_vanished_count():
    """A resolved MONITOR never linked to any DEF → 'vanished without prevention
    record'."""
    mon = _mon("MON-002", status="resolved", health="ok")
    out = brief_cmd._outcome_feedback_note([mon], active_packs=["ops"])
    assert "1 resolved MONITOR(s)" in out
    assert "vanished without prevention record" in out


def test_outcome_note_resolved_suppressed_when_def_backlink_exists():
    """Resolved but a DEF was filed → prevention trace exists, no vanished note."""
    mon = _mon("MON-002", status="resolved", health="ok")
    d = _def_stub("DEF-001", [_OLink("MON-002", "exposed_by")])
    out = brief_cmd._outcome_feedback_note([mon, d], active_packs=["ops"])
    assert "vanished" not in out


def test_outcome_note_router_recommendation_in_next_skill():
    """The same conditions surface inside _next_skill_recommendation as an
    advisory recommending defect-from-monitor (the router wire)."""
    mon = _mon("MON-001")
    out = brief_cmd._next_skill_recommendation(
        "executing", [mon], [], [], active_packs=["ops"],
    )
    assert "defect-from-monitor" in out
