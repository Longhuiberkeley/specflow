"""Tests for specflow artifact-lint command validation checks."""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.commands import artifact_lint as lint_cmd
from specflow.commands import trace as trace_cmd
from specflow.lib import artifacts as art_lib

_SCHEMA_TYPES = [
    ("requirement", "REQ"), ("architecture", "ARCH"), ("detailed-design", "DDD"),
    ("unit-test", "UT"), ("integration-test", "IT"), ("qualification-test", "QT"),
    ("story", "STORY"), ("spike", "SPIKE"), ("decision", "DEC"),
    ("defect", "DEF"),
]

_STATUS_FLOW = {
    "draft": [], "approved": ["draft"], "implemented": ["approved"],
    "verified": ["implemented"],
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
        (schema_dir / f"{art_type}.yaml").write_text(
            yaml.dump(schema), encoding="utf-8"
        )

    config = {
        "project": {"name": "test-project", "created": "2026-01-01"},
        "impact_analysis": {
            "auto_flag": True, "auto_resolve": False, "remind_after": "7d",
        },
        "artifact_types": [t for t, _ in _SCHEMA_TYPES],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump(config), encoding="utf-8"
    )

    state = {"current": "idle", "history": []}
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump(state), encoding="utf-8"
    )

    for subdir in [
        "_specflow/specs/requirements", "_specflow/specs/architecture",
        "_specflow/specs/detailed-design", "_specflow/specs/unit-tests",
        "_specflow/specs/integration-tests", "_specflow/specs/qualification-tests",
        "_specflow/work/stories", "_specflow/work/spikes",
        "_specflow/work/decisions", "_specflow/work/defects",
    ]:
        (root / subdir).mkdir(parents=True, exist_ok=True)

    return root


def _write_artifact(
    root: Path,
    artifact_id: str,
    art_type: str,
    title: str,
    status: str = "draft",
    body: str = "",
    links: list[dict] | None = None,
    extra_fm: dict | None = None,
) -> Path:
    rel_dir = art_lib.TYPE_TO_DIR.get(art_type, "")
    if not rel_dir:
        raise ValueError(f"Unknown type: {art_type}")
    target_dir = root / "_specflow" / rel_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    fm: dict = {
        "id": artifact_id,
        "title": title,
        "type": art_type,
        "status": status,
        "tags": [],
        "suspect": False,
        "links": links or [],
    }
    if extra_fm:
        fm.update(extra_fm)

    fm_yaml = yaml.dump(fm, default_flow_style=False, sort_keys=False)
    content = f"---\n{fm_yaml}---\n\n# {title}\n\n{body}\n"
    file_path = target_dir / f"{artifact_id}.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def _make_art(
    art_id: str,
    art_type: str,
    status: str = "draft",
    body: str = "body",
    links: list[art_lib.Link] | None = None,
    extra_fm: dict | None = None,
) -> art_lib.Artifact:
    fm: dict = {
        "id": art_id, "title": f"Test {art_id}",
        "type": art_type, "status": status,
    }
    if extra_fm:
        fm.update(extra_fm)
    return art_lib.Artifact(
        path=Path(f"{art_id}.md"),
        frontmatter=fm,
        body=body,
        links=links or [],
    )


# ── check_schema ────────────────────────────────────────────────────────────

class TestCheckSchema:
    def test_valid_artifact_passes(self, project_root: Path):
        arts = [_make_art("REQ-001", "requirement", status="draft")]
        result = lint_cmd.check_schema(
            arts, project_root / ".specflow" / "schema"
        )
        assert result["blocking_count"] == 0
        assert result["warning_count"] == 0

    def test_missing_required_field_is_blocking(self, project_root: Path):
        schema_dir = project_root / ".specflow" / "schema"
        schema = yaml.safe_load(
            (schema_dir / "requirement.yaml").read_text()
        )
        schema["required_fields"] = ["status", "title", "priority"]
        (schema_dir / "requirement.yaml").write_text(
            yaml.dump(schema), encoding="utf-8"
        )

        art = art_lib.Artifact(
            path=Path("REQ-001.md"),
            frontmatter={
                "id": "REQ-001", "title": "Test",
                "type": "requirement", "status": "draft",
            },
            body="body",
            links=[],
        )
        result = lint_cmd.check_schema([art], schema_dir)
        assert result["blocking_count"] >= 1
        assert "priority" in result["detail"]

    def test_unknown_type_triggers_warning(self, project_root: Path):
        arts = [_make_art("FOO-001", "unknown-type")]
        result = lint_cmd.check_schema(
            arts, project_root / ".specflow" / "schema"
        )
        assert result["warning_count"] >= 1
        assert "Unknown type" in result["detail"]


# ── _check_links ────────────────────────────────────────────────────────────

class TestCheckLinks:
    def test_all_valid_links_pass(self, project_root: Path):
        _write_artifact(
            project_root, "REQ-001", "requirement", "Test REQ",
        )
        _write_artifact(
            project_root, "STORY-001", "story", "Test Story",
            links=[{"target": "REQ-001", "role": "implements"}],
        )
        arts = art_lib.discover_artifacts(project_root)
        result = lint_cmd._check_links(arts, project_root)
        assert result["blocking_count"] == 0

    def test_broken_link_is_blocking(self, project_root: Path):
        _write_artifact(
            project_root, "REQ-001", "requirement", "Test REQ",
        )
        _write_artifact(
            project_root, "STORY-001", "story", "Test Story",
            links=[{"target": "REQ-999", "role": "implements"}],
        )
        arts = art_lib.discover_artifacts(project_root)
        result = lint_cmd._check_links(arts, project_root)
        assert result["blocking_count"] >= 1
        assert "broken link" in result["detail"]

    def test_complies_with_known_clause_is_valid(self, project_root: Path):
        standards_dir = project_root / ".specflow" / "standards"
        standard = {
            "title": "Test Standard",
            "clauses": [
                {"id": "ISO-001", "title": "Clause A", "severity": "medium"},
            ],
        }
        (standards_dir / "test-standard.yaml").write_text(
            yaml.dump(standard), encoding="utf-8"
        )

        _write_artifact(
            project_root, "REQ-001", "requirement", "Test REQ",
            links=[{"target": "ISO-001", "role": "complies_with"}],
        )
        arts = art_lib.discover_artifacts(project_root)
        result = lint_cmd._check_links(arts, project_root)
        assert result["blocking_count"] == 0

    def test_complies_with_unknown_clause_is_broken(self, project_root: Path):
        _write_artifact(
            project_root, "REQ-001", "requirement", "Test REQ",
            links=[{"target": "ISO-999", "role": "complies_with"}],
        )
        arts = art_lib.discover_artifacts(project_root)
        result = lint_cmd._check_links(arts, project_root)
        assert result["blocking_count"] >= 1
        assert "broken link" in result["detail"]


# ── _check_status ───────────────────────────────────────────────────────────

class TestCheckStatus:
    def test_valid_status_passes(self, project_root: Path):
        arts = [_make_art("REQ-001", "requirement", status="draft")]
        result = lint_cmd._check_status(
            arts, project_root / ".specflow" / "schema"
        )
        assert result["blocking_count"] == 0

    def test_invalid_status_is_blocking(self, project_root: Path):
        arts = [_make_art("REQ-001", "requirement", status="foobar")]
        result = lint_cmd._check_status(
            arts, project_root / ".specflow" / "schema"
        )
        assert result["blocking_count"] >= 1
        assert "invalid status" in result["detail"]

    def test_all_valid_statuses_pass_individually(self, project_root: Path):
        for s in ("draft", "approved", "implemented", "verified"):
            arts = [_make_art("REQ-001", "requirement", status=s)]
            result = lint_cmd._check_status(
                arts, project_root / ".specflow" / "schema"
            )
            assert result["blocking_count"] == 0, f"status '{s}' should be valid"


# ── _check_acceptance ───────────────────────────────────────────────────────

class TestCheckAcceptance:
    def test_req_with_acceptance_criteria_passes(self):
        arts = [
            _make_art(
                "REQ-001", "requirement",
                body="# Test\n\n## Acceptance Criteria\n\n1. Given X",
            )
        ]
        result = lint_cmd._check_acceptance(arts)
        assert result["blocking_count"] == 0

    def test_req_without_acceptance_criteria_fails(self):
        arts = [
            _make_art(
                "REQ-001", "requirement",
                body="# Test\n\nThe system shall work.",
            )
        ]
        result = lint_cmd._check_acceptance(arts)
        assert result["blocking_count"] >= 1
        assert "no acceptance criteria" in result["detail"]

    def test_non_req_artifact_is_not_checked(self):
        arts = [
            _make_art("STORY-001", "story", body="# Test\n\nNo AC here.")
        ]
        result = lint_cmd._check_acceptance(arts)
        assert result["blocking_count"] == 0

    def test_req_with_given_pattern_passes(self):
        arts = [
            _make_art(
                "REQ-001", "requirement",
                body="# Test\n\n1. Given a user is logged in",
            )
        ]
        result = lint_cmd._check_acceptance(arts)
        assert result["blocking_count"] == 0


# ── check_coverage ──────────────────────────────────────────────────────────

class TestCheckCoverage:
    def test_full_coverage_passes(self):
        arts = [
            _make_art("REQ-001", "requirement", status="approved"),
            _make_art(
                "STORY-001", "story", status="approved",
                links=[art_lib.Link(target="REQ-001", role="implements")],
            ),
            _make_art(
                "UT-001", "unit-test",
                links=[art_lib.Link(target="STORY-001", role="verified_by")],
            ),
            _make_art(
                "IT-001", "integration-test",
                links=[art_lib.Link(target="STORY-001", role="verified_by")],
            ),
            _make_art(
                "QT-001", "qualification-test",
                links=[art_lib.Link(target="STORY-001", role="verified_by")],
            ),
        ]
        result = lint_cmd.check_coverage(arts)
        assert result["blocking_count"] == 0
        assert result["warning_count"] == 0

    def test_approved_req_without_story_triggers_warning(self):
        arts = [
            _make_art("REQ-001", "requirement", status="approved"),
        ]
        result = lint_cmd.check_coverage(arts)
        assert result["warning_count"] >= 1
        assert "no STORY" in result["detail"]

    def test_approved_story_without_tests_triggers_warnings(self):
        arts = [
            _make_art("REQ-001", "requirement", status="approved"),
            _make_art(
                "STORY-001", "story", status="approved",
                links=[art_lib.Link(target="REQ-001", role="implements")],
            ),
        ]
        result = lint_cmd.check_coverage(arts)
        assert result["warning_count"] >= 3
        assert "verified_by" in result["detail"]

    def test_draft_req_is_not_checked(self):
        arts = [
            _make_art("REQ-001", "requirement", status="draft"),
        ]
        result = lint_cmd.check_coverage(arts)
        assert result["warning_count"] == 0


# ── trace.run ───────────────────────────────────────────────────────────────

class TestTrace:
    def test_trace_with_upstream_and_downstream(self, project_root: Path):
        _write_artifact(
            project_root, "REQ-001", "requirement", "Parent REQ",
            status="approved",
        )
        _write_artifact(
            project_root, "STORY-001", "story", "Child Story",
            links=[{"target": "REQ-001", "role": "implements"}],
        )
        rc = trace_cmd.run(project_root, {"artifact_id": "REQ-001"})
        assert rc == 0

    def test_trace_nonexistent_artifact_returns_error(
        self, project_root: Path
    ):
        rc = trace_cmd.run(project_root, {"artifact_id": "REQ-999"})
        assert rc == 1

    def test_trace_missing_artifact_id_returns_error(
        self, project_root: Path
    ):
        rc = trace_cmd.run(project_root, {"artifact_id": ""})
        assert rc == 1


# ── lint_cmd.run (integration) ─────────────────────────────────────────────

class TestLintRunIntegration:
    def test_clean_project_passes(self, project_root: Path):
        _write_artifact(
            project_root, "REQ-001", "requirement", "Test REQ",
            body="## Acceptance Criteria\n\n1. Given X",
            status="draft",
        )
        rc = lint_cmd.run(project_root, {})
        assert rc == 0

    def test_missing_specflow_dir_fails(self, tmp_path: Path):
        root = tmp_path / "empty_project"
        root.mkdir()
        rc = lint_cmd.run(root, {})
        assert rc == 1

    def test_single_check_type(self, project_root: Path):
        _write_artifact(
            project_root, "REQ-001", "requirement", "Test REQ",
        )
        rc = lint_cmd.run(project_root, {"type": "schema"})
        assert rc == 0

    def test_unknown_check_type_fails(self, project_root: Path):
        rc = lint_cmd.run(project_root, {"type": "nonexistent"})
        assert rc == 1
