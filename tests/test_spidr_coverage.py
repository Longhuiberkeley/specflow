"""Tests for SPIDR dimension coverage lint check."""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.commands import artifact_lint as lint_cmd
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


class TestSpidrCoverage:
    def test_all_dimensions_covered(self):
        stories = [
            _make_art("STORY-001", "story", extra_fm={"tags": ["spidr-spike", "spidr-path"]}),
            _make_art("STORY-002", "story", extra_fm={"tags": ["spidr-interface"]}),
            _make_art("STORY-003", "story", extra_fm={"tags": ["spidr-data"]}),
            _make_art("STORY-004", "story", extra_fm={"tags": ["spidr-rules"]}),
        ]
        result = lint_cmd._check_spidr_coverage(stories)
        assert result["warning_count"] == 0
        assert "covered" in result["detail"].lower()

    def test_missing_dimension(self):
        stories = [
            _make_art("STORY-001", "story", extra_fm={"tags": ["spidr-path"]}),
        ]
        result = lint_cmd._check_spidr_coverage(stories)
        assert result["warning_count"] == 4
        assert "spidr-spike" in result["detail"]
        assert "spidr-interface" in result["detail"]
        assert "spidr-data" in result["detail"]
        assert "spidr-rules" in result["detail"]

    def test_no_spidr_tags(self):
        stories = [
            _make_art("STORY-001", "story", extra_fm={"tags": ["feature"]}),
        ]
        result = lint_cmd._check_spidr_coverage(stories)
        assert result["warning_count"] == 5
        assert "no SPIDR dimension tags" in result["detail"]

    def test_no_stories(self):
        result = lint_cmd._check_spidr_coverage([])
        assert result["warning_count"] == 0
        assert "no stories" in result["detail"].lower() or "skipped" in result["detail"].lower()

    def test_only_path_covered(self):
        stories = [
            _make_art("STORY-001", "story", extra_fm={"tags": ["spidr-path"]}),
            _make_art("STORY-002", "story", extra_fm={"tags": ["spidr-path"]}),
        ]
        result = lint_cmd._check_spidr_coverage(stories)
        assert result["warning_count"] == 4
