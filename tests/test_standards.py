"""Tests for specflow.lib.standards — loading and gap analysis."""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.lib import standards as standards_lib


def _write_standard(root: Path, name: str, data: dict) -> None:
    d = root / ".specflow" / "standards"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.yaml").write_text(
        yaml.dump(data, default_flow_style=False), encoding="utf-8"
    )


class TestListInstalledStandards:
    def test_no_standards(self, tmp_path: Path):
        result = standards_lib.list_installed_standards(tmp_path)
        assert result == []

    def test_finds_standard(self, tmp_path: Path):
        _write_standard(tmp_path, "iso26262-demo", {
            "standard": "iso26262-demo",
            "title": "Demo",
            "clauses": [],
        })
        result = standards_lib.list_installed_standards(tmp_path)
        assert result == ["iso26262-demo"]


class TestLoadStandard:
    def test_loads_valid(self, tmp_path: Path):
        _write_standard(tmp_path, "my-standard", {
            "standard": "my-standard",
            "title": "My Standard",
            "clauses": [
                {"id": "SEC-1", "title": "Access Control", "description": "Enforce RBAC."},
            ],
        })
        data = standards_lib.load_standard(tmp_path, "my-standard")
        assert data is not None
        assert data["standard"] == "my-standard"
        assert len(data["clauses"]) == 1

    def test_missing_standard(self, tmp_path: Path):
        data = standards_lib.load_standard(tmp_path, "nonexistent")
        assert data is None


class TestCheckCompliance:
    def test_no_standards_installed(self, tmp_path: Path):
        result = standards_lib.check_compliance(tmp_path)
        assert not result["ok"]
        assert "No standards installed" in result["error"]

    def test_gap_analysis(self, tmp_path: Path):
        _write_standard(tmp_path, "my-std", {
            "standard": "my-std",
            "title": "Test Standard",
            "version": "1.0",
            "clauses": [
                {"id": "S1", "title": "Clause 1", "description": "First"},
                {"id": "S2", "title": "Clause 2", "description": "Second"},
            ],
        })
        result = standards_lib.check_compliance(tmp_path, "my-std")
        assert result["ok"]
        assert len(result["covered"]) == 0
        assert len(result["uncovered"]) == 2
        uncovered_ids = [c["clause_id"] for c in result["uncovered"]]
        assert "S1" in uncovered_ids
        assert "S2" in uncovered_ids
