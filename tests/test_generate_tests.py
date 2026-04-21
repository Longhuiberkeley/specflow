"""Tests for specflow generate-tests command."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
import pytest

from specflow.commands import generate_tests
from specflow.lib import artifacts as art_lib


@pytest.fixture
def project_root(tmp_path: Path):
    """Create a minimal SpecFlow project structure."""
    specflow = tmp_path / "_specflow"
    specflow.mkdir()

    for subdir in [
        "specs/requirements",
        "specs/architecture",
        "specs/detailed-design",
        "specs/unit-tests",
        "specs/integration-tests",
        "specs/qualification-tests",
        "work/stories",
    ]:
        (specflow / subdir).mkdir(parents=True, exist_ok=True)

    schema_dir = tmp_path / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)

    for art_type, prefix in [("unit-test", "UT"), ("integration-test", "IT"), ("qualification-test", "QT"),
                             ("requirement", "REQ"), ("architecture", "ARCH"), ("detailed-design", "DDD")]:
        schema = {
            "type": art_type,
            "prefix": prefix,
            "allowed_status": {"draft": [], "approved": ["draft"], "implemented": ["approved"], "verified": ["implemented"]},
        }
        (schema_dir / f"{art_type}.yaml").write_text(yaml.dump(schema), encoding="utf-8")

    return tmp_path


def _write_artifact(root: Path, art_type: str, art_id: str, title: str, status: str, body: str = "",
                    links: list[dict] | None = None) -> Path:
    """Write a minimal artifact file."""
    rel_dir = art_lib.TYPE_TO_DIR.get(art_type, f"specs/{art_type}")
    target_dir = root / "_specflow" / rel_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    fm = {"id": art_id, "title": title, "type": art_type, "status": status, "suspect": False,
          "links": links or [], "created": "2026-04-21"}
    content = f"---\n{yaml.dump(fm, default_flow_style=False, sort_keys=False)}---\n\n{body}\n"
    path = target_dir / f"{art_id}.md"
    path.write_text(content, encoding="utf-8")
    return path


class TestGenerateTestsFromSingleArtifact:
    def test_from_implemented_ddd_creates_ut(self, project_root):
        _write_artifact(project_root, "detailed-design", "DDD-100", "Design", "implemented",
                        body="# Design\n\nSome design detail.")
        args = {"from": "DDD-100", "dry_run": False}
        rc = generate_tests.run(project_root, args)
        assert rc == 0

        ut_dir = project_root / "_specflow" / "specs" / "unit-tests"
        ut_files = list(ut_dir.glob("UT-*.md"))
        assert len(ut_files) == 1
        art = art_lib.parse_artifact(ut_files[0])
        assert art is not None
        assert art.type == "unit-test"
        assert "DDD-100" in art.title
        assert any(l.target == "DDD-100" and l.role == "verified_by" for l in art.links)

    def test_from_implemented_req_creates_qt(self, project_root):
        body = "# Requirement\n\n## Acceptance Criteria\n\n1. The system shall work.\n2. The system shall be fast."
        _write_artifact(project_root, "requirement", "REQ-100", "Feature", "implemented", body=body)
        args = {"from": "REQ-100", "dry_run": False}
        rc = generate_tests.run(project_root, args)
        assert rc == 0

        qt_dir = project_root / "_specflow" / "specs" / "qualification-tests"
        qt_files = list(qt_dir.glob("QT-*.md"))
        assert len(qt_files) == 1
        art = art_lib.parse_artifact(qt_files[0])
        assert art is not None
        assert art.type == "qualification-test"
        assert "REQ-100" in art.title

    def test_from_not_implemented_returns_1(self, project_root):
        _write_artifact(project_root, "detailed-design", "DDD-100", "Design", "approved")
        args = {"from": "DDD-100", "dry_run": False}
        rc = generate_tests.run(project_root, args)
        assert rc == 1


class TestGenerateTestsDuplicatePrevention:
    def test_existing_verification_skips(self, project_root):
        _write_artifact(project_root, "detailed-design", "DDD-100", "Design", "implemented")
        _write_artifact(project_root, "unit-test", "UT-001", "Test for DDD-100", "draft",
                        links=[{"target": "DDD-100", "role": "verified_by"}])
        args = {"from": "DDD-100", "dry_run": False}
        rc = generate_tests.run(project_root, args)
        assert rc == 0

        ut_files = list((project_root / "_specflow" / "specs" / "unit-tests").glob("UT-*.md"))
        assert len(ut_files) == 1


class TestGenerateTestsDryRun:
    def test_dry_run_no_files_written(self, project_root):
        _write_artifact(project_root, "requirement", "REQ-100", "Feature", "implemented")
        args = {"from": None, "dry_run": True}
        rc = generate_tests.run(project_root, args)
        assert rc == 0

        qt_dir = project_root / "_specflow" / "specs" / "qualification-tests"
        qt_files = list(qt_dir.glob("QT-*.md"))
        assert len(qt_files) == 0


class TestGenerateTestsNoArgs:
    def test_generates_for_all_missing_pairs(self, project_root):
        _write_artifact(project_root, "detailed-design", "DDD-100", "Design A", "implemented")
        _write_artifact(project_root, "architecture", "ARCH-100", "Arch A", "implemented")
        _write_artifact(project_root, "requirement", "REQ-100", "Req A", "implemented")
        args = {"from": None, "dry_run": False}
        rc = generate_tests.run(project_root, args)
        assert rc == 0

        ut_files = list((project_root / "_specflow" / "specs" / "unit-tests").glob("UT-*.md"))
        it_files = list((project_root / "_specflow" / "specs" / "integration-tests").glob("IT-*.md"))
        qt_files = list((project_root / "_specflow" / "specs" / "qualification-tests").glob("QT-*.md"))
        assert len(ut_files) == 1
        assert len(it_files) == 1
        assert len(qt_files) == 1

    def test_skips_already_verified(self, project_root):
        _write_artifact(project_root, "detailed-design", "DDD-100", "Design", "implemented")
        _write_artifact(project_root, "unit-test", "UT-001", "Test", "draft",
                        links=[{"target": "DDD-100", "role": "verified_by"}])
        _write_artifact(project_root, "requirement", "REQ-100", "Req", "implemented")
        args = {"from": None, "dry_run": False}
        rc = generate_tests.run(project_root, args)
        assert rc == 0

        ut_files = list((project_root / "_specflow" / "specs" / "unit-tests").glob("UT-*.md"))
        assert len(ut_files) == 1

    def test_skips_draft_specs(self, project_root):
        _write_artifact(project_root, "detailed-design", "DDD-100", "Design", "draft")
        args = {"from": None, "dry_run": False}
        rc = generate_tests.run(project_root, args)
        assert rc == 0

        ut_files = list((project_root / "_specflow" / "specs" / "unit-tests").glob("UT-*.md"))
        assert len(ut_files) == 0


class TestGenerateTestsAcceptanceCriteria:
    def test_criteria_copied_to_qt_body(self, project_root):
        body = "# Feature\n\n## Acceptance Criteria\n\n1. System starts\n2. System stops\n\nSome text."
        _write_artifact(project_root, "requirement", "REQ-100", "Feature", "implemented", body=body)
        args = {"from": "REQ-100", "dry_run": False}
        rc = generate_tests.run(project_root, args)
        assert rc == 0

        qt_files = list((project_root / "_specflow" / "specs" / "qualification-tests").glob("QT-*.md"))
        art = art_lib.parse_artifact(qt_files[0])
        assert "System starts" in art.body
        assert "System stops" in art.body
