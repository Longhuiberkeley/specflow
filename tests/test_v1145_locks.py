"""Locking tests for the v1.14.5 schema/lint registrations (STORY-647).

v1.14.5 shipped four wiring changes with zero locking coverage (UT-079/IT-046
recorded green runs over suites that never exercised them — the evidentiary
gap found in the v1.14.5 post-release audit):

  1. experiment.yaml optional_fields += ``competition`` (stamped on every
     logged EXPT by the autoresearch CLI; omission produced one unknown-field
     info finding per experiment, ~50 per LOOP).
  2. competition.yaml optional_fields += ``custom_categories``
     (protocol-instructed on COMP creation).
  3. loop.yaml allowed_link_roles += ``derives_from`` (the LOOP→MON escalation
     edge; matches finding/run/monitor siblings).
  4. lint accepts protocol-shaped ``condensation_brief_<N>`` stamps alongside
     the plural ``condensation_briefs`` (loop.yaml lists only the plural).

These tests pin all four: silently reverting any registration fails here
instead of shipping unnoticed.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import lint as lint_lib

PACK_SCHEMAS = (
    Path(__file__).parent.parent / "src" / "specflow" / "packs" / "autoresearch" / "schemas"
)
OPS_PACK_SCHEMAS = (
    Path(__file__).parent.parent / "src" / "specflow" / "packs" / "ops" / "schemas"
)


def _schema(name: str) -> dict:
    return yaml.safe_load((PACK_SCHEMAS / name).read_text(encoding="utf-8"))


def _art(fm: dict, links: list[art_lib.Link] | None = None) -> art_lib.Artifact:
    return art_lib.Artifact(
        path=Path(f"{fm['id']}.md"),
        frontmatter=fm,
        body="body",
        links=links or [],
    )


def _no_unknown_field_or_role_issues(issues: list[dict]) -> None:
    bad = [
        i["message"] for i in issues
        if "Unknown field" in i["message"] or "Unknown link role" in i["message"]
        or "not allowed" in i["message"].lower()
    ]
    assert not bad, f"registration regressed: {bad}"


def test_expt_competition_field_registered():
    """AC: an EXPT stamped with `competition` (autoresearch CLI writes it on
    every logged experiment) produces zero unknown-field findings."""
    schema = _schema("experiment.yaml")
    assert "competition" in schema["optional_fields"], (
        "experiment.yaml lost the `competition` optional field"
    )
    fm = {
        "id": "EXPT-001",
        "title": "Locked EXPT",
        "type": "experiment",
        "status": "kept",
        "created": "2026-08-30",
        "loop": "LOOP-001",
        "competition": "COMP-001",
        "metric_value": 0.87,
        "change_category": "features",
        "summary": "locking test",
    }
    _no_unknown_field_or_role_issues(lint_lib.validate_artifact_schema(_art(fm), schema))


def test_comp_custom_categories_field_registered():
    """AC: a COMP carrying `custom_categories` (protocol-instructed) produces
    zero unknown-field findings."""
    schema = _schema("competition.yaml")
    assert "custom_categories" in schema["optional_fields"], (
        "competition.yaml lost the `custom_categories` optional field"
    )
    fm = {
        "id": "COMP-001",
        "title": "Locked COMP",
        "type": "competition",
        "status": "active",
        "created": "2026-08-30",
        "verify_command": "uv run pytest -q",
        "metric_name": "auc",
        "metric_direction": "maximize",
        "custom_categories": {"screener": ["stability", "cost"]},
    }
    _no_unknown_field_or_role_issues(lint_lib.validate_artifact_schema(_art(fm), schema))


def test_loop_numbered_condensation_briefs_accepted():
    """AC: protocol-shaped ``condensation_brief_<N>`` stamps (the protocol
    numbers them: condensation_brief_10, condensation_brief_20, …) pass lint
    alongside the plural ``condensation_briefs`` form."""
    schema = _schema("loop.yaml")
    fm = {
        "id": "LOOP-001",
        "title": "Locked LOOP",
        "type": "loop",
        "status": "running",
        "created": "2026-08-30",
        "competition": "COMP-001",
        "mode": "explore",
        "budget": "40",
        "condensation_briefs": "plural-form summary",
        "condensation_brief_10": "first protocol-stamped brief",
        "condensation_brief_20": "second protocol-stamped brief",
    }
    _no_unknown_field_or_role_issues(lint_lib.validate_artifact_schema(_art(fm), schema))


def test_loop_derives_from_link_role_allowed():
    """AC: LOOP→MON escalation edges (`derives_from`) are a legal link role —
    the edge that renders monitor-escalated loops upstream in `specflow trace`."""
    schema = _schema("loop.yaml")
    assert "derives_from" in schema["allowed_link_roles"], (
        "loop.yaml lost the `derives_from` allowed link role"
    )
    fm = {
        "id": "LOOP-001",
        "title": "Locked LOOP",
        "type": "loop",
        "status": "running",
        "created": "2026-08-30",
        "competition": "COMP-001",
        "mode": "validate",
        "budget": "20",
    }
    links = [art_lib.Link(target="MON-007", role="derives_from")]
    issues = lint_lib.validate_artifact_schema(_art(fm, links=links), schema)
    _no_unknown_field_or_role_issues(issues)


# ── STORY-652: reversible COMP pause (initial_statuses) ──────────────────────


def test_comp_reversible_pause_schema_pin():
    """AC: competition.yaml keeps paused→active legal while create still
    enters at active via initial_statuses (not an empty-predecessor root)."""
    schema = _schema("competition.yaml")
    assert schema["allowed_status"]["active"] == ["paused"], (
        "competition.yaml lost paused→active (reversible pause)"
    )
    assert schema.get("initial_statuses") == ["active"], (
        "competition.yaml lost initial_statuses: [active]"
    )


def _restore_type_registry():
    dirs = dict(art_lib.TYPE_TO_DIR)
    prefixes = dict(art_lib.TYPE_TO_PREFIX)
    reverse = dict(art_lib.PREFIX_TO_TYPE)
    aliases = dict(art_lib.TYPE_ALIASES)

    def restore() -> None:
        art_lib.TYPE_TO_DIR.clear()
        art_lib.TYPE_TO_DIR.update(dirs)
        art_lib.TYPE_TO_PREFIX.clear()
        art_lib.TYPE_TO_PREFIX.update(prefixes)
        art_lib.PREFIX_TO_TYPE.clear()
        art_lib.PREFIX_TO_TYPE.update(reverse)
        art_lib.TYPE_ALIASES.clear()
        art_lib.TYPE_ALIASES.update(aliases)

    return restore


def _comp_project(tmp: Path) -> Path:
    """Temp project whose competition schema is the shipped pack file."""
    root = tmp / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    src = PACK_SCHEMAS / "competition.yaml"
    (schema_dir / "competition.yaml").write_text(
        src.read_text(encoding="utf-8"), encoding="utf-8"
    )
    config = {
        "project": {"name": "comp-lock", "created": "2026-01-01"},
        "artifact_types": ["competition"],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump(config), encoding="utf-8"
    )
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "idle", "history": []}), encoding="utf-8"
    )
    (root / "_specflow" / "specs" / "competitions").mkdir(parents=True, exist_ok=True)
    return root


def _create_args(**over) -> dict:
    base = {
        "type": "competition",
        "title": "Lock COMP",
        "status": None,
        "priority": None,
        "rationale": None,
        "tags": "",
        "links": "",
        "add_link": [],
        "body": "b",
        "from_standard": None,
        "force": True,
        "skip_dedup_check": True,
        "nfr_category": None,
        "sanctioned": None,
        "set_fields": [],
    }
    base.update(over)
    return base


def test_comp_create_defaults_to_active_without_sanction(tmp_path: Path):
    """AC: creating a competition without --status lands on active;
    --status active needs no --sanctioned."""
    from specflow.commands import create as create_cmd

    restore = _restore_type_registry()
    try:
        root = _comp_project(tmp_path)
        rc = create_cmd.run(root, _create_args())
        assert rc == 0
        arts = art_lib.discover_artifacts(root)
        assert len(arts) == 1
        assert arts[0].status == "active"

        root2 = _comp_project(tmp_path / "explicit")
        rc = create_cmd.run(root2, _create_args(status="active"))
        assert rc == 0
        arts2 = art_lib.discover_artifacts(root2)
        assert arts2[0].status == "active"
        assert "sanctioned_justification" not in arts2[0].frontmatter
    finally:
        restore()


def test_comp_create_completed_still_requires_sanction(tmp_path: Path, capsys):
    """AC: --status completed at create still requires --sanctioned."""
    from specflow.commands import create as create_cmd

    restore = _restore_type_registry()
    try:
        root = _comp_project(tmp_path)
        rc = create_cmd.run(root, _create_args(status="completed"))
        out = capsys.readouterr().out
        assert rc == 1
        assert "--sanctioned" in out
        assert art_lib.discover_artifacts(root) == []
    finally:
        restore()


def test_comp_paused_to_active_succeeds_completed_to_active_rejected(tmp_path: Path):
    """AC: paused→active update succeeds; completed→active is still rejected."""
    restore = _restore_type_registry()
    try:
        root = _comp_project(tmp_path)
        paused = art_lib.create_artifact(
            root, "competition", title="Paused COMP", status="paused", body="b"
        )
        assert paused["ok"], paused
        result = art_lib.update_artifact(root, paused["id"], status="active")
        assert result["ok"] is True, result
        art = art_lib.parse_artifact(Path(result["path"]))
        assert art is not None
        assert art.status == "active"

        done = art_lib.create_artifact(
            root, "competition", title="Done COMP", status="completed", body="b"
        )
        assert done["ok"], done
        rejected = art_lib.update_artifact(root, done["id"], status="active")
        assert rejected["ok"] is False
        assert "Cannot transition" in rejected["error"]
    finally:
        restore()


# ── STORY-653: window_end on competition.yaml ────────────────────────────────


def test_comp_closure_disposition_field_registered():
    """AC: a completed COMP stamped with `closure_disposition` (closure
    protocol) produces zero unknown-field findings."""
    schema = _schema("competition.yaml")
    assert "closure_disposition" in schema["optional_fields"], (
        "competition.yaml lost the `closure_disposition` optional field"
    )


def test_comp_window_end_field_registered():
    """AC: a COMP stamped with `window_end` (rolling-evaluation recipe) produces
    zero unknown-field findings."""
    schema = _schema("competition.yaml")
    assert "window_end" in schema["optional_fields"], (
        "competition.yaml lost the `window_end` optional field"
    )
    fm = {
        "id": "COMP-001",
        "title": "Locked COMP",
        "type": "competition",
        "status": "active",
        "created": "2026-08-30",
        "verify_command": "uv run pytest -q",
        "metric_name": "auc",
        "metric_direction": "maximize",
        "window_end": "2026-12-31",
    }
    _no_unknown_field_or_role_issues(lint_lib.validate_artifact_schema(_art(fm), schema))


# ── STORY-655: reversible RUN pause ──────────────────────────────────────────


def test_run_reversible_pause_schema_pin():
    """AC: run.yaml keeps paused→live legal (reversible pause)."""
    schema = yaml.safe_load((OPS_PACK_SCHEMAS / "run.yaml").read_text(encoding="utf-8"))
    assert schema["allowed_status"]["live"] == ["deployed", "paused"], (
        "run.yaml lost paused→live (reversible pause)"
    )
