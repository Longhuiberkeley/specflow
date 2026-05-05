"""Tests for standards_lib.get_clause_by_id."""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.lib import standards as standards_lib


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    return root


def _install_standard(root: Path, clauses: list[dict], title: str = "Test Std") -> None:
    std_dir = root / ".specflow" / "standards"
    std = {"title": title, "clauses": clauses}
    (std_dir / "test-standard.yaml").write_text(yaml.dump(std), encoding="utf-8")


class TestGetClauseById:
    def test_empty_clause_id_returns_none(self, project_root: Path):
        assert standards_lib.get_clause_by_id(project_root, "") is None

    def test_not_found_returns_none(self, project_root: Path):
        _install_standard(project_root, [{"id": "C1", "title": "Clause 1"}])
        assert standards_lib.get_clause_by_id(project_root, "NONEXISTENT") is None

    def test_found_returns_enriched_dict(self, project_root: Path):
        _install_standard(project_root, [
            {"id": "C1", "title": "Safety", "category": "security", "severity": "high"},
        ])
        result = standards_lib.get_clause_by_id(project_root, "C1")
        assert result is not None
        assert result["id"] == "C1"
        assert result["title"] == "Safety"
        assert result["category"] == "security"
        assert "_standard" in result
        assert result["_standard"] == "Test Std"

    def test_minimal_clause_without_optional_fields(self, project_root: Path):
        _install_standard(project_root, [
            {"id": "C2", "title": "Minimal Clause"},
        ])
        result = standards_lib.get_clause_by_id(project_root, "C2")
        assert result is not None
        assert result["title"] == "Minimal Clause"
        assert result.get("category") is None

    def test_non_dict_clause_entries_skipped(self, project_root: Path):
        _install_standard(project_root, [
            "not a dict",
            {"id": "C3", "title": "Valid"},
        ])
        result = standards_lib.get_clause_by_id(project_root, "C3")
        assert result is not None
        assert result["id"] == "C3"

    def test_multi_standard_lookup(self, project_root: Path):
        std_dir = project_root / ".specflow" / "standards"
        for name, clauses in [
            ("std-a.yaml", [{"id": "A1", "title": "From A"}]),
            ("std-b.yaml", [{"id": "B1", "title": "From B"}]),
        ]:
            (std_dir / name).write_text(
                yaml.dump({"title": name, "clauses": clauses}), encoding="utf-8"
            )
        assert standards_lib.get_clause_by_id(project_root, "B1")["title"] == "From B"

    def test_standard_without_title_uses_id_fallback(self, project_root: Path):
        std_dir = project_root / ".specflow" / "standards"
        (std_dir / "minimal.yaml").write_text(
            yaml.dump({"id": "my-std", "clauses": [{"id": "C4", "title": "T"}]}),
            encoding="utf-8",
        )
        result = standards_lib.get_clause_by_id(project_root, "C4")
        assert result is not None
        assert result["_standard"] == "my-std"
