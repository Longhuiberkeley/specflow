"""Tests for the suspect → DEF pipeline (defects.create_defect_from_suspect)."""

from __future__ import annotations

from pathlib import Path

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
