"""Tests for best_practices.py helpers: _learned_patterns_text, _recent_chl_summaries, compose_review_prefix."""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.lib import artifacts as art_lib
from specflow.lib import best_practices as bp_lib


_PKG_SCHEMAS = Path(__file__).parent.parent / "src" / "specflow" / "templates" / "schemas"


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "checklists" / "learned").mkdir(parents=True, exist_ok=True)

    for name in ("requirement.yaml", "challenge.yaml"):
        src = _PKG_SCHEMAS / name
        assert src.exists(), f"missing template schema: {src}"
        (schema_dir / name).write_text(src.read_text(), encoding="utf-8")

    config = {
        "project": {"name": "test-project", "created": "2026-01-01"},
        "artifact_types": ["requirement", "challenge"],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump(config), encoding="utf-8"
    )
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "idle", "history": []}), encoding="utf-8"
    )

    for subdir in [
        "_specflow/specs/requirements",
        "_specflow/specs/challenges",
    ]:
        d = root / subdir
        d.mkdir(parents=True, exist_ok=True)
        (d / "_index.yaml").write_text(
            "artifacts: {}\nnext_id: 1\n", encoding="utf-8"
        )

    return root


def _write_prev_pattern(learned_dir: Path, prev_id: str, name: str, source: str = "") -> Path:
    pattern = {
        "id": prev_id,
        "name": name,
        "discovered_from": source,
        "mode": "reactive",
        "pattern": name,
        "applies_to": {"tags": []},
        "items": [],
    }
    path = learned_dir / f"{prev_id}.yaml"
    path.write_text(
        yaml.dump(pattern, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _write_chl(
    root: Path,
    chl_id: str,
    title: str = "Test challenge",
    status: str = "open",
    severity: str = "warn",
    technique: str = "premortem",
    body: str = "Some rationale text.",
) -> Path:
    chl_dir = root / "_specflow" / "specs" / "challenges"
    chl_dir.mkdir(parents=True, exist_ok=True)
    fm = {
        "id": chl_id,
        "title": title,
        "type": "challenge",
        "status": status,
        "severity": severity,
        "technique": technique,
        "created": "2026-01-01",
        "tags": [],
        "links": [],
    }
    content = f"---\n{yaml.dump(fm, default_flow_style=False, sort_keys=False)}---\n\n{body}\n"
    path = chl_dir / f"{chl_id}.md"
    path.write_text(content, encoding="utf-8")
    return path


class TestLearnedPatternsText:
    def test_reads_name_field(self, project_root: Path):
        learned_dir = project_root / ".specflow" / "checklists" / "learned"
        _write_prev_pattern(learned_dir, "PREV-001", "Prevent null deref", "STORY-001")
        result = bp_lib._learned_patterns_text(project_root)
        assert "PREV-001" in result
        assert "Prevent null deref" in result
        assert "STORY-001" in result

    def test_multiple_patterns(self, project_root: Path):
        learned_dir = project_root / ".specflow" / "checklists" / "learned"
        _write_prev_pattern(learned_dir, "PREV-001", "Pattern A")
        _write_prev_pattern(learned_dir, "PREV-002", "Pattern B")
        result = bp_lib._learned_patterns_text(project_root)
        assert "PREV-001" in result
        assert "PREV-002" in result
        assert "Pattern A" in result
        assert "Pattern B" in result

    def test_empty_when_no_dir(self, tmp_path: Path):
        root = tmp_path / "no-learned"
        root.mkdir()
        assert bp_lib._learned_patterns_text(root) == ""

    def test_caps_at_ten(self, project_root: Path):
        learned_dir = project_root / ".specflow" / "checklists" / "learned"
        for i in range(1, 16):
            _write_prev_pattern(learned_dir, f"PREV-{i:03d}", f"Pattern {i}")
        result = bp_lib._learned_patterns_text(project_root)
        assert "PREV-010" in result
        assert "PREV-015" not in result

    def test_pattern_without_source_omits_trigger(self, project_root: Path):
        learned_dir = project_root / ".specflow" / "checklists" / "learned"
        _write_prev_pattern(learned_dir, "PREV-001", "Orphan pattern", source="")
        result = bp_lib._learned_patterns_text(project_root)
        assert "PREV-001" in result
        assert "source" not in result


class TestRecentChlSummaries:
    def test_excludes_accepted_stale_resolved(self, project_root: Path):
        _write_chl(project_root, "CHL-001", status="open", severity="warn")
        _write_chl(project_root, "CHL-002", status="accepted", severity="warn")
        _write_chl(project_root, "CHL-003", status="stale", severity="warn")
        _write_chl(project_root, "CHL-004", status="resolved", severity="warn")
        result = bp_lib._recent_chl_summaries(project_root)
        assert "CHL-001" in result
        assert "CHL-002" not in result
        assert "CHL-003" not in result
        assert "CHL-004" not in result

    def test_sorts_by_severity_weight(self, project_root: Path):
        _write_chl(project_root, "CHL-001", severity="info", title="Info finding")
        _write_chl(project_root, "CHL-002", severity="error", title="Error finding")
        _write_chl(project_root, "CHL-003", severity="warn", title="Warn finding")
        result = bp_lib._recent_chl_summaries(project_root)
        lines = [l for l in result.split("\n") if l.strip().startswith("- ")]
        assert len(lines) == 3
        assert "CHL-002" in lines[0]
        assert "CHL-003" in lines[1]
        assert "CHL-001" in lines[2]

    def test_includes_rationale_from_body(self, project_root: Path):
        body = "X" * 300
        _write_chl(project_root, "CHL-001", body=body)
        result = bp_lib._recent_chl_summaries(project_root)
        assert "Rationale:" in result
        assert "X" * 200 in result

    def test_defaults_max_items_to_ten(self, project_root: Path):
        for i in range(1, 16):
            _write_chl(project_root, f"CHL-{i:03d}", severity="warn")
        result = bp_lib._recent_chl_summaries(project_root)
        count = result.count("CHL-")
        assert count == 10

    def test_empty_when_no_challenges(self, project_root: Path):
        assert bp_lib._recent_chl_summaries(project_root) == ""

    def test_includes_technique_and_severity(self, project_root: Path):
        _write_chl(project_root, "CHL-001", technique="premortem", severity="error")
        result = bp_lib._recent_chl_summaries(project_root)
        assert "technique: premortem" in result
        assert "error" in result


class TestComposeReviewPrefixExistingTechniques:
    def test_section_appears_when_techniques_set(self, tmp_path: Path):
        root = tmp_path / "project"
        (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
        result = bp_lib.compose_review_prefix(
            root, "", [], "review", [],
            existing_techniques=["premortem", "devils_advocate"],
        )
        assert "Previously applied thinking techniques" in result
        assert "premortem" in result
        assert "devils_advocate" in result

    def test_no_section_when_none(self, tmp_path: Path):
        root = tmp_path / "project"
        (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
        result = bp_lib.compose_review_prefix(
            root, "", [], "review", [],
            existing_techniques=None,
        )
        assert "Previously applied thinking techniques" not in result

    def test_no_section_when_empty_list(self, tmp_path: Path):
        root = tmp_path / "project"
        (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
        result = bp_lib.compose_review_prefix(
            root, "", [], "review", [],
            existing_techniques=[],
        )
        assert "Previously applied thinking techniques" not in result
