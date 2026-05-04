"""Tests for reverse impact analysis: output file index, glob matching, suspect flagging."""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.commands import artifact_lint as lint_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import impact as impact_lib


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
    (root / ".specflow" / "cache" / "backups").mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "impact-log").mkdir(parents=True, exist_ok=True)

    for art_type, prefix in _SCHEMA_TYPES:
        schema = {
            "type": art_type,
            "prefix": prefix,
            "allowed_status": dict(_STATUS_FLOW),
            "optional_fields": ["output_files"],
        }
        (schema_dir / f"{art_type}.yaml").write_text(
            yaml.dump(schema), encoding="utf-8"
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


class TestBuildOutputFileIndex:
    def test_literal_match(self, project_root: Path):
        _write_artifact(
            project_root, "ARCH-001", "architecture", "Test Arch",
            extra_fm={"output_files": ["src/specflow/lib/impact.py"]},
        )
        index = impact_lib.build_output_file_index(project_root)
        assert "src/specflow/lib/impact.py" in index
        entries = index["src/specflow/lib/impact.py"]
        assert any(e[0] == "ARCH-001" and e[1] == "literal" for e in entries)

    def test_glob_pattern(self, project_root: Path):
        _write_artifact(
            project_root, "ARCH-002", "architecture", "Data Arch",
            extra_fm={"output_files": ["output/YY_MM_DD_*.json"]},
        )
        index = impact_lib.build_output_file_index(project_root)
        assert "output/YY_MM_DD_*.json" in index
        entries = index["output/YY_MM_DD_*.json"]
        assert any(e[0] == "ARCH-002" and e[1] == "glob" for e in entries)

    def test_no_output_files(self, project_root: Path):
        _write_artifact(project_root, "ARCH-003", "architecture", "No Files Arch")
        index = impact_lib.build_output_file_index(project_root)
        assert len(index) == 0

    def test_multiple_artifacts_same_file(self, project_root: Path):
        _write_artifact(
            project_root, "ARCH-010", "architecture", "Arch A",
            extra_fm={"output_files": ["src/shared.py"]},
        )
        _write_artifact(
            project_root, "DDD-010", "detailed-design", "DDD A",
            extra_fm={"output_files": ["src/shared.py"]},
        )
        index = impact_lib.build_output_file_index(project_root)
        entries = index.get("src/shared.py", [])
        art_ids = {e[0] for e in entries}
        assert "ARCH-010" in art_ids
        assert "DDD-010" in art_ids


class TestIsGlobPattern:
    def test_literal(self):
        assert not impact_lib.is_glob_pattern("src/foo.py")

    def test_star(self):
        assert impact_lib.is_glob_pattern("output/*.json")

    def test_question_mark(self):
        assert impact_lib.is_glob_pattern("file_?.txt")

    def test_bracket(self):
        assert impact_lib.is_glob_pattern("file_[0-9].txt")


class TestReverseImpact:
    def test_flags_suspect_on_literal_match(self, project_root: Path):
        _write_artifact(
            project_root, "ARCH-020", "architecture", "Impact Arch",
            extra_fm={"output_files": ["src/specflow/lib/impact.py"]},
        )
        matches = impact_lib.reverse_impact(
            project_root, ["src/specflow/lib/impact.py"]
        )
        assert len(matches) == 1
        assert matches[0].artifact_id == "ARCH-020"
        assert matches[0].match_type == "literal"

        art = art_lib.parse_artifact(
            project_root / "_specflow" / "specs" / "architecture" / "ARCH-020.md"
        )
        assert art is not None
        assert art.suspect is True

    def test_flags_suspect_on_glob_match(self, project_root: Path):
        _write_artifact(
            project_root, "ARCH-021", "architecture", "Glob Arch",
            extra_fm={"output_files": ["output/*_report.json"]},
        )
        matches = impact_lib.reverse_impact(
            project_root, ["output/2026_report.json"]
        )
        assert len(matches) == 1
        assert matches[0].artifact_id == "ARCH-021"
        assert matches[0].match_type == "glob"

    def test_no_false_positives(self, project_root: Path):
        _write_artifact(
            project_root, "ARCH-022", "architecture", "Safe Arch",
            extra_fm={"output_files": ["src/specific_file.py"]},
        )
        matches = impact_lib.reverse_impact(
            project_root, ["src/other_file.py", "README.md"]
        )
        assert len(matches) == 0

    def test_empty_changed_files(self, project_root: Path):
        matches = impact_lib.reverse_impact(project_root, [])
        assert len(matches) == 0

    def test_deduplication(self, project_root: Path):
        _write_artifact(
            project_root, "ARCH-023", "architecture", "Dedup Arch",
            extra_fm={"output_files": ["src/foo.py"]},
        )
        matches = impact_lib.reverse_impact(
            project_root, ["src/foo.py", "src/foo.py"]
        )
        assert len(matches) == 1

    def test_propagates_downstream(self, project_root: Path):
        _write_artifact(
            project_root, "ARCH-030", "architecture", "Upstream Arch",
            extra_fm={"output_files": ["src/lib.py"]},
        )
        _write_artifact(
            project_root, "DDD-030", "detailed-design", "Downstream DDD",
            links=[{"target": "ARCH-030", "role": "refined_by"}],
        )
        impact_lib.reverse_impact(project_root, ["src/lib.py"])

        ddd = art_lib.parse_artifact(
            project_root / "_specflow" / "specs" / "detailed-design" / "DDD-030.md"
        )
        assert ddd is not None
        assert ddd.suspect is True
