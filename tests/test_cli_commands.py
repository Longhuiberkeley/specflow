"""Tests for specflow CLI commands — create, update, status."""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.commands import create as create_cmd
from specflow.commands import update as update_cmd
from specflow.commands import status as status_cmd
from specflow.commands import artifact_lint as lint_cmd

_SCHEMA_TYPES = [
    ("requirement", "REQ"), ("architecture", "ARCH"), ("detailed-design", "DDD"),
    ("unit-test", "UT"), ("integration-test", "IT"), ("qualification-test", "QT"),
    ("story", "STORY"), ("spike", "SPIKE"), ("decision", "DEC"),
    ("defect", "DEF"), ("challenge", "CHL"), ("audit", "AUD"),
]

_STATUS_FLOW = {
    "draft": [], "approved": ["draft"], "implemented": ["approved"], "verified": ["implemented"],
}


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)

    for art_type, prefix in _SCHEMA_TYPES:
        schema = {
            "type": art_type,
            "prefix": prefix,
            "allowed_status": dict(_STATUS_FLOW),
        }
        (schema_dir / f"{art_type}.yaml").write_text(yaml.dump(schema), encoding="utf-8")

    config = {
        "project": {"name": "test-project", "created": "2026-01-01"},
        "impact_analysis": {"auto_flag": True, "auto_resolve": False, "remind_after": "7d"},
        "artifact_types": [t for t, _ in _SCHEMA_TYPES],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")

    state = {"current": "idle", "history": []}
    (root / ".specflow" / "state.yaml").write_text(yaml.dump(state), encoding="utf-8")

    for subdir in [
        "_specflow/specs/requirements", "_specflow/specs/architecture",
        "_specflow/specs/detailed-design", "_specflow/specs/unit-tests",
        "_specflow/specs/integration-tests", "_specflow/specs/qualification-tests",
        "_specflow/specs/challenges", "_specflow/specs/audits",
        "_specflow/work/stories", "_specflow/work/spikes",
        "_specflow/work/decisions", "_specflow/work/defects",
    ]:
        (root / subdir).mkdir(parents=True, exist_ok=True)

    return root


class TestCreateCommand:
    def test_creates_requirement(self, project_root: Path):
        rc = create_cmd.run(project_root, {
            "type": "requirement", "title": "Test requirement",
            "status": "draft", "priority": "high", "rationale": "Testing",
            "tags": "test, smoke", "links": None,
            "body": "The system shall do X.",
            "from_standard": None, "force": False,
            "skip_dedup_check": True, "nfr_category": None,
        })
        assert rc == 0
        req_dir = project_root / "_specflow" / "specs" / "requirements"
        files = list(req_dir.glob("REQ-*.md"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "Test requirement" in content
        assert "status: draft" in content

    def test_creates_story(self, project_root: Path):
        rc = create_cmd.run(project_root, {
            "type": "story", "title": "Implement feature",
            "status": "draft", "priority": None, "rationale": None,
            "tags": None, "links": None,
            "body": "As a user I want X.",
            "from_standard": None, "force": False,
            "skip_dedup_check": True, "nfr_category": None,
        })
        assert rc == 0
        story_dir = project_root / "_specflow" / "work" / "stories"
        files = list(story_dir.glob("STORY-*.md"))
        assert len(files) == 1

    def test_missing_type_returns_error(self, project_root: Path):
        rc = create_cmd.run(project_root, {
            "type": "", "title": "No type",
            "status": "draft", "priority": None, "rationale": None,
            "tags": None, "links": None, "body": "",
            "from_standard": None, "force": False,
            "skip_dedup_check": True, "nfr_category": None,
        })
        assert rc == 1

    def test_missing_title_returns_error(self, project_root: Path):
        rc = create_cmd.run(project_root, {
            "type": "requirement", "title": "",
            "status": "draft", "priority": None, "rationale": None,
            "tags": None, "links": None, "body": "",
            "from_standard": None, "force": False,
            "skip_dedup_check": True, "nfr_category": None,
        })
        assert rc == 1


class TestUpdateCommand:
    def test_updates_status(self, project_root: Path):
        create_cmd.run(project_root, {
            "type": "requirement", "title": "Test REQ",
            "status": "draft", "priority": None, "rationale": None,
            "tags": None, "links": None, "body": "Body.",
            "from_standard": None, "force": False,
            "skip_dedup_check": True, "nfr_category": None,
        })
        req_file = list((project_root / "_specflow" / "specs" / "requirements").glob("REQ-*.md"))[0]
        rc = update_cmd.run(project_root, {
            "artifact_id": req_file.stem,
            "status": "approved", "priority": None,
            "rationale": None, "tags": None, "title": None,
        })
        assert rc == 0
        assert "status: approved" in req_file.read_text()

    def test_updates_title(self, project_root: Path):
        create_cmd.run(project_root, {
            "type": "requirement", "title": "Original title",
            "status": "draft", "priority": None, "rationale": None,
            "tags": None, "links": None, "body": "Body.",
            "from_standard": None, "force": False,
            "skip_dedup_check": True, "nfr_category": None,
        })
        req_id = list((project_root / "_specflow" / "specs" / "requirements").glob("REQ-*.md"))[0].stem
        rc = update_cmd.run(project_root, {
            "artifact_id": req_id,
            "status": None, "priority": None,
            "rationale": None, "tags": None, "title": "Updated title",
        })
        assert rc == 0

    def test_nonexistent_artifact_returns_error(self, project_root: Path):
        rc = update_cmd.run(project_root, {
            "artifact_id": "REQ-999",
            "status": "approved", "priority": None,
            "rationale": None, "tags": None, "title": None,
        })
        assert rc == 1

    def test_no_fields_returns_error(self, project_root: Path):
        rc = update_cmd.run(project_root, {
            "artifact_id": "REQ-001",
            "status": None, "priority": None,
            "rationale": None, "tags": None, "title": None,
        })
        assert rc == 1


class TestStatusCommand:
    def test_runs_on_empty_project(self, project_root: Path):
        rc = status_cmd.run(project_root, {})
        assert rc == 0

    def test_runs_with_artifacts(self, project_root: Path):
        create_cmd.run(project_root, {
            "type": "requirement", "title": "Test REQ",
            "status": "draft", "priority": None, "rationale": None,
            "tags": None, "links": None, "body": "Body.",
            "from_standard": None, "force": False,
            "skip_dedup_check": True, "nfr_category": None,
        })
        rc = status_cmd.run(project_root, {})
        assert rc == 0


class TestLintPublicAPI:
    def test_check_schema_public(self):
        assert callable(lint_cmd.check_schema)

    def test_check_coverage_public(self):
        assert callable(lint_cmd.check_coverage)
