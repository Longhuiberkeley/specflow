"""Tests for the suspect → DEF pipeline (defects.create_defect_from_suspect)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
import pytest

from specflow.lib import artifacts as art_lib
from specflow.lib import defects as defects_lib

# Defect uses its own lifecycle; other types use the standard flow.
_STD_FLOW = {"draft": [], "approved": ["draft"], "implemented": ["approved"], "verified": ["implemented"]}
_DEF_FLOW = {
    "open": [], "investigating": ["open"], "fixing": ["investigating"],
    "verified": ["fixing"], "closed": ["verified"], "wontfix": ["open", "investigating"],
}
_SCHEMA_TYPES = [
    ("requirement", "REQ", _STD_FLOW), ("architecture", "ARCH", _STD_FLOW),
    ("story", "STORY", _STD_FLOW), ("spike", "SPIKE", _STD_FLOW),
    ("defect", "DEF", _DEF_FLOW),
]


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)

    for art_type, prefix, flow in _SCHEMA_TYPES:
        schema = {
            "type": art_type,
            "prefix": prefix,
            "allowed_status": dict(flow),
            "allowed_link_roles": ["fails_to_meet", "exposed_by", "addresses", "implements"],
        }
        (schema_dir / f"{art_type}.yaml").write_text(yaml.dump(schema), encoding="utf-8")

    config = {
        "project": {"name": "test-project", "created": "2026-01-01"},
        "artifact_types": [t for t, _, _ in _SCHEMA_TYPES],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "executing", "history": []}), encoding="utf-8"
    )

    for subdir in [
        "_specflow/specs/requirements", "_specflow/specs/architecture",
        "_specflow/work/stories", "_specflow/work/spikes", "_specflow/work/defects",
    ]:
        (root / subdir).mkdir(parents=True, exist_ok=True)

    return root


def _seed_req_and_arch(root: Path) -> None:
    art_lib.create_artifact(root, "requirement", title="Rate limiting", status="approved", body="req body")
    art_lib.create_artifact(root, "architecture", title="Limiter middleware", status="approved", body="arch body")


class TestCreateDefectFromSuspect:
    def test_creates_indexed_defect_with_links(self, project_root: Path):
        _seed_req_and_arch(project_root)
        result = defects_lib.create_defect_from_suspect(
            project_root, suspect_artifact_id="ARCH-001", upstream_req_id="REQ-001",
        )
        assert result["ok"], result
        defect_id = result["id"]

        # Registered in the index (the key reason for using create_artifact).
        index = yaml.safe_load(
            (project_root / "_specflow" / "work" / "defects" / "_index.yaml").read_text()
        )
        assert defect_id in index.get("artifacts", {})

        # Parseable, correct links and status, fingerprint present.
        arts = {a.id: a for a in art_lib.discover_artifacts(project_root)}
        defect = arts[defect_id]
        assert defect.status == "open"
        roles = {(lk.role, lk.target) for lk in defect.links}
        assert ("fails_to_meet", "REQ-001") in roles
        assert ("exposed_by", "ARCH-001") in roles
        assert "suspect-derived" in (defect.frontmatter.get("tags") or [])

    def test_missing_suspect_returns_error(self, project_root: Path):
        _seed_req_and_arch(project_root)
        result = defects_lib.create_defect_from_suspect(
            project_root, suspect_artifact_id="ARCH-999", upstream_req_id="REQ-001",
        )
        assert not result["ok"]
        assert "not found" in result["error"]

    def test_severity_maps_to_priority(self, project_root: Path):
        _seed_req_and_arch(project_root)
        result = defects_lib.create_defect_from_suspect(
            project_root, suspect_artifact_id="ARCH-001", upstream_req_id="REQ-001",
            severity="high",
        )
        assert result["ok"]
        arts = {a.id: a for a in art_lib.discover_artifacts(project_root)}
        assert arts[result["id"]].frontmatter.get("priority") == "high"

    def test_impact_event_recorded_in_body(self, project_root: Path):
        _seed_req_and_arch(project_root)
        result = defects_lib.create_defect_from_suspect(
            project_root, suspect_artifact_id="ARCH-001", upstream_req_id="REQ-001",
            impact_event_path=".specflow/impact-log/2026-06-06-evt.yaml",
        )
        assert result["ok"]
        body = Path(result["path"]).read_text(encoding="utf-8")
        assert "2026-06-06-evt.yaml" in body

    def test_suspect_body_bytes_stable_after_extraction(self, project_root: Path):
        """Pin the `_create_linked_defect` extraction: the DEF body, links, tag,
        and priority are byte-identical to the pre-refactor construction. The
        body is joined with "\n" exactly as before; only the call site moved."""
        _seed_req_and_arch(project_root)
        result = defects_lib.create_defect_from_suspect(
            project_root, suspect_artifact_id="ARCH-001", upstream_req_id="REQ-001",
            impact_event_path=".specflow/impact-log/evt.yaml", severity="high",
        )
        assert result["ok"]
        text = Path(result["path"]).read_text(encoding="utf-8")
        # The exact body the pre-refactor code produced (joined with "\n").
        expected_body = "\n".join([
            "## Context",
            "",
            "Artifact **ARCH-001** was flagged `suspect` after **REQ-001** changed. "
            "This defect tracks the resolution of that suspect flag.",
            "",
            "Impact event: `.specflow/impact-log/evt.yaml`",
            "",
            "## Resolution",
            "",
            "(To be filled when the defect is resolved.)",
        ])
        assert expected_body in text
        arts = {a.id: a for a in art_lib.discover_artifacts(project_root)}
        defect = arts[result["id"]]
        assert defect.frontmatter.get("priority") == "high"
        assert "suspect-derived" in (defect.frontmatter.get("tags") or [])
        roles = {(lk.role, lk.target) for lk in defect.links}
        assert roles == {("fails_to_meet", "REQ-001"), ("exposed_by", "ARCH-001")}


# --- monitor → DEF pipeline (ops outcome feedback) ---

def _write_monitor(
    root: Path,
    mon_id: str,
    *,
    status: str = "flagged",
    health: str | None = "breached",
    metrics: Any = None,
    signals: Any = None,
    captures: Any = None,
    observed_at: str | None = "2026-08-01",
) -> Path:
    """Write a raw MONITOR artifact under _specflow/ops/monitors/.

    `create_defect_from_monitor` reads the MONITOR via parse_artifact (not
    create_artifact), so no monitor schema needs to be registered — a parseable
    file with the right frontmatter is enough for resolve_link_target to find it.
    A None value for any optional field omits it, to exercise the defensive path.
    """
    mon_dir = root / "_specflow" / "ops" / "monitors"
    mon_dir.mkdir(parents=True, exist_ok=True)
    fm: dict[str, Any] = {
        "id": mon_id,
        "title": f"{mon_id} observation",
        "type": "monitor",
        "status": status,
        "created": "2026-08-01",
        "run": "RUN-001",
        "summary": "observation",
    }
    if observed_at is not None:
        fm["observed_at"] = observed_at
    if health is not None:
        fm["health"] = health
    if metrics is not None:
        fm["metrics"] = metrics
    if signals is not None:
        fm["signals"] = signals
    if captures is not None:
        fm["captures"] = captures
    content = (
        "---\n"
        + yaml.dump(fm, default_flow_style=False, sort_keys=False)
        + "---\n\n"
        + f"# {fm['title']}\n\nobservation body\n"
    )
    path = mon_dir / f"{mon_id}.md"
    path.write_text(content, encoding="utf-8")
    return path


class TestCreateDefectFromMonitor:
    def test_creates_defect_with_both_links_and_frozen_evidence(self, project_root: Path):
        art_lib.create_artifact(project_root, "requirement", title="Latency SLO", status="approved", body="req")
        _write_monitor(
            project_root, "MON-001",
            metrics={"p99_ms": 850}, signals={"trend": "rising"}, captures={"snap": 3},
        )
        result = defects_lib.create_defect_from_monitor(
            project_root, monitor_id="MON-001", upstream_req_id="REQ-001",
        )
        assert result["ok"], result

        arts = {a.id: a for a in art_lib.discover_artifacts(project_root)}
        defect = arts[result["id"]]
        # Both schema-blessed links present.
        roles = {(lk.role, lk.target) for lk in defect.links}
        assert ("fails_to_meet", "REQ-001") in roles
        assert ("exposed_by", "MON-001") in roles
        assert "monitor-derived" in (defect.frontmatter.get("tags") or [])

        # Frozen-evidence block carries the MONITOR's snapshot verbatim.
        body = Path(result["path"]).read_text(encoding="utf-8")
        assert "## Observed at breach" in body
        assert "p99_ms" in body and "850" in body   # metrics frozen
        assert "trend" in body                       # signals frozen
        assert "snap" in body                        # captures frozen
        assert "Frozen from MON-001 at creation" in body
        assert "append-only" in body

    def test_warn_and_proceed_on_healthy_monitor(self, project_root: Path):
        art_lib.create_artifact(project_root, "requirement", title="R", status="approved", body="req")
        _write_monitor(project_root, "MON-002", status="logged", health="ok", metrics={"x": 1})
        result = defects_lib.create_defect_from_monitor(
            project_root, monitor_id="MON-002", upstream_req_id="REQ-001",
        )
        # DEF still created, warning surfaced — never refuses.
        assert result["ok"]
        assert "healthy at capture" in result.get("warning", "")
        arts = {a.id: a for a in art_lib.discover_artifacts(project_root)}
        assert result["id"] in arts

    def test_monitor_untouched_no_status_mutation(self, project_root: Path):
        art_lib.create_artifact(project_root, "requirement", title="R", status="approved", body="req")
        mon_path = _write_monitor(project_root, "MON-003", status="flagged", health="breached", metrics={"d": 0.9})
        before = mon_path.read_text(encoding="utf-8")
        defects_lib.create_defect_from_monitor(
            project_root, monitor_id="MON-003", upstream_req_id="REQ-001",
        )
        after = mon_path.read_text(encoding="utf-8")
        assert before == after  # MONITOR never mutated — journal stays append-only

    def test_missing_monitor_returns_error(self, project_root: Path):
        art_lib.create_artifact(project_root, "requirement", title="R", status="approved", body="req")
        result = defects_lib.create_defect_from_monitor(
            project_root, monitor_id="MON-999", upstream_req_id="REQ-001",
        )
        assert not result["ok"]
        assert "not found" in result["error"]

    def test_defensive_when_monitor_has_no_evidence_fields(self, project_root: Path):
        art_lib.create_artifact(project_root, "requirement", title="R", status="approved", body="req")
        # A malformed MONITOR carrying none of the five evidence fields.
        _write_monitor(
            project_root, "MON-005",
            metrics=None, signals=None, captures=None, health=None, observed_at=None,
        )
        result = defects_lib.create_defect_from_monitor(
            project_root, monitor_id="MON-005", upstream_req_id="REQ-001",
        )
        assert result["ok"]
        body = Path(result["path"]).read_text(encoding="utf-8")
        assert "## Observed at breach" in body  # block present even if empty
        assert "no metrics/signals/captures fields" in body

    def test_def_closure_fires_prev_persistence(self, project_root: Path):
        """The monitor-derived DEF flows through the EXISTING on_closure → PREV
        path with zero new PREV code: closing it captures a prevention pattern
        seeded from the fails_to_meet/exposed_by links."""
        from specflow.lib import learning as learn_lib

        art_lib.create_artifact(project_root, "requirement", title="R", status="approved", body="req")
        _write_monitor(project_root, "MON-004", metrics={"drift": 0.9})
        result = defects_lib.create_defect_from_monitor(
            project_root, monitor_id="MON-004", upstream_req_id="REQ-001",
        )
        assert result["ok"]

        closure = defects_lib.on_closure(project_root, result["id"])
        assert closure["ok"], closure
        assert closure["defect"] == result["id"]
        assert closure["broken_requirements"] == ["REQ-001"]
        assert closure["catching_tests"] == ["MON-004"]
        assert closure["pattern_path"]  # PREV file written
        # A learned pattern now exists on disk.
        assert learn_lib.list_learned_patterns(project_root)
