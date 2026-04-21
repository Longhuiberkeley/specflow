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

    def test_coverage_score_zero(self, tmp_path: Path):
        _write_standard(tmp_path, "s1", {
            "standard": "s1",
            "title": "T",
            "clauses": [{"id": "C1", "title": "A"}],
        })
        result = standards_lib.check_compliance(tmp_path, "s1")
        assert result["ok"]
        assert result["score"] == 0.0

    def test_coverage_score_full(self, tmp_path: Path):
        _write_standard(tmp_path, "s1", {
            "standard": "s1",
            "title": "T",
            "clauses": [{"id": "C1", "title": "A"}],
        })
        spec_dir = tmp_path / "_specflow" / "specs" / "requirements"
        spec_dir.mkdir(parents=True, exist_ok=True)
        (spec_dir / "REQ-001.md").write_text(
            "---\nid: REQ-001\ntype: requirement\ntitle: T\nstatus: draft\nlinks:\n"
            "  - target: C1\n    role: complies_with\n---\n\n# T\n",
            encoding="utf-8",
        )
        result = standards_lib.check_compliance(tmp_path, "s1")
        assert result["ok"]
        assert result["score"] == 100.0
        assert len(result["covered"]) == 1
        assert len(result["uncovered"]) == 0

    def test_coverage_score_partial(self, tmp_path: Path):
        _write_standard(tmp_path, "s1", {
            "standard": "s1",
            "title": "T",
            "clauses": [
                {"id": "C1", "title": "A"},
                {"id": "C2", "title": "B"},
                {"id": "C3", "title": "C"},
                {"id": "C4", "title": "D"},
                {"id": "C5", "title": "E"},
            ],
        })
        spec_dir = tmp_path / "_specflow" / "specs" / "requirements"
        spec_dir.mkdir(parents=True, exist_ok=True)
        (spec_dir / "REQ-001.md").write_text(
            "---\nid: REQ-001\ntype: requirement\ntitle: T\nstatus: draft\nlinks:\n"
            "  - target: C1\n    role: complies_with\n  - target: C3\n    role: complies_with\n---\n\n# T\n",
            encoding="utf-8",
        )
        result = standards_lib.check_compliance(tmp_path, "s1")
        assert result["ok"]
        assert result["score"] == 40.0


class TestSeveritySorting:
    def test_sorted_by_severity(self, tmp_path: Path):
        _write_standard(tmp_path, "s1", {
            "standard": "s1",
            "title": "T",
            "clauses": [
                {"id": "C1", "title": "Low", "severity": "low"},
                {"id": "C2", "title": "High", "severity": "high"},
                {"id": "C3", "title": "Medium", "severity": "medium"},
            ],
        })
        result = standards_lib.check_compliance(tmp_path, "s1")
        assert result["ok"]
        severities = [c["severity"] for c in result["uncovered"]]
        assert severities == ["high", "medium", "low"]

    def test_severity_tiebreak_by_priority(self, tmp_path: Path):
        _write_standard(tmp_path, "s1", {
            "standard": "s1",
            "title": "T",
            "clauses": [
                {"id": "C1", "title": "B", "severity": "high", "priority": 5},
                {"id": "C2", "title": "A", "severity": "high", "priority": 1},
            ],
        })
        result = standards_lib.check_compliance(tmp_path, "s1")
        assert result["ok"]
        ids = [c["clause_id"] for c in result["uncovered"]]
        assert ids == ["C2", "C1"]


class TestRemediation:
    def test_safety_category(self):
        clause = {"category": "safety", "severity": "medium"}
        result = standards_lib.suggest_remediation(clause)
        assert "hazard" in result
        assert "safety" in result

    def test_security_category(self):
        clause = {"category": "security", "severity": "medium"}
        result = standards_lib.suggest_remediation(clause)
        assert "security" in result
        assert "threat-model" in result

    def test_high_severity_priority(self):
        clause = {"category": "safety", "severity": "high"}
        result = standards_lib.suggest_remediation(clause)
        assert "prioritize" in result

    def test_unknown_category_falls_back(self):
        clause = {"category": "unknown-cat", "severity": "medium"}
        result = standards_lib.suggest_remediation(clause)
        assert "requirement" in result

    def test_uncovered_have_remediation(self, tmp_path: Path):
        _write_standard(tmp_path, "s1", {
            "standard": "s1",
            "title": "T",
            "clauses": [
                {"id": "C1", "title": "Safety", "category": "safety", "severity": "high"},
            ],
        })
        result = standards_lib.check_compliance(tmp_path, "s1")
        assert result["ok"]
        assert len(result["uncovered"]) == 1
        assert "remediation" in result["uncovered"][0]
        assert "hazard" in result["uncovered"][0]["remediation"]
