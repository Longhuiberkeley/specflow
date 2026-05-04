"""Tests for story dependency cycle detection lint check."""

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


class TestWaveCycleDetection:
    def test_no_cycles(self, project_root: Path):
        stories = [
            _make_art("STORY-001", "story", status="approved"),
            _make_art("STORY-002", "story", status="approved",
                      links=[art_lib.Link(target="STORY-001", role="depends_on")]),
        ]
        result = lint_cmd._check_wave_cycles(stories, project_root)
        assert result["warning_count"] == 0
        assert "2 stories" in result["detail"]
        assert "wave" in result["detail"].lower()

    def test_detects_cycle(self, project_root: Path):
        stories = [
            _make_art("STORY-001", "story", status="approved",
                      links=[art_lib.Link(target="STORY-002", role="depends_on")]),
            _make_art("STORY-002", "story", status="approved",
                      links=[art_lib.Link(target="STORY-001", role="depends_on")]),
        ]
        result = lint_cmd._check_wave_cycles(stories, project_root)
        assert result["warning_count"] >= 1
        assert "circular" in result["detail"].lower()

    def test_excessive_dependencies(self, project_root: Path):
        links = [art_lib.Link(target=f"STORY-00{i}", role="depends_on") for i in range(1, 5)]
        stories = [
            _make_art("STORY-001", "story"),
            _make_art("STORY-002", "story"),
            _make_art("STORY-003", "story"),
            _make_art("STORY-004", "story"),
            _make_art("STORY-005", "story", links=links),
        ]
        result = lint_cmd._check_wave_cycles(stories, project_root)
        assert result["warning_count"] >= 1
        assert "4 dependencies" in result["detail"]

    def test_no_stories(self, project_root: Path):
        result = lint_cmd._check_wave_cycles([], project_root)
        assert result["warning_count"] == 0
        assert "no stories" in result["detail"].lower() or "skipped" in result["detail"].lower()

    def test_wave_report(self, project_root: Path):
        stories = [
            _make_art("STORY-001", "story", status="approved"),
            _make_art("STORY-002", "story", status="approved"),
            _make_art("STORY-003", "story", status="approved",
                      links=[art_lib.Link(target="STORY-001", role="depends_on")]),
        ]
        result = lint_cmd._check_wave_cycles(stories, project_root)
        assert result["warning_count"] == 0
        assert "wave 1" in result["detail"]
        assert "wave 2" in result["detail"]
