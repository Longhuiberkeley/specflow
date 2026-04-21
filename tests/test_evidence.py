"""Tests for specflow.lib.evidence — compliance evidence report generation."""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.lib import evidence as evidence_lib
from specflow.lib import baselines as baseline_lib


def _scaffold_project(root: Path) -> None:
    (root / ".specflow" / "baselines").mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    (root / "_specflow" / "specs" / "requirements").mkdir(parents=True, exist_ok=True)
    (root / "_specflow" / "specs" / "architecture").mkdir(parents=True, exist_ok=True)
    (root / "_specflow" / "specs" / "detailed-design").mkdir(parents=True, exist_ok=True)
    (root / "_specflow" / "specs" / "unit-tests").mkdir(parents=True, exist_ok=True)
    (root / "_specflow" / "specs" / "integration-tests").mkdir(parents=True, exist_ok=True)
    (root / "_specflow" / "specs" / "qualification-tests").mkdir(parents=True, exist_ok=True)


def _write_artifact(root: Path, directory: str, filename: str, frontmatter: dict, body: str = "") -> Path:
    d = root / "_specflow" / directory
    d.mkdir(parents=True, exist_ok=True)
    p = d / filename
    fm_yaml = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    p.write_text(f"---\n{fm_yaml}---\n\n# {frontmatter['title']}\n\n{body}\n", encoding="utf-8")
    return p


class TestGenerateEvidenceReport:
    def test_basic_report_generation(self, tmp_path: Path):
        _scaffold_project(tmp_path)
        baseline_lib.create_baseline(tmp_path, "v1.0")
        result = evidence_lib.generate_evidence_report(tmp_path, "v1.0")
        assert result["ok"]
        assert result["path"].endswith("v1.0-evidence.md")
        report = Path(result["path"]).read_text(encoding="utf-8")
        assert "Compliance Evidence Report" in report
        assert "v1.0" in report

    def test_missing_baseline(self, tmp_path: Path):
        _scaffold_project(tmp_path)
        result = evidence_lib.generate_evidence_report(tmp_path, "nonexistent")
        assert not result["ok"]
        assert "not found" in result["error"]

    def test_traceability_section(self, tmp_path: Path):
        _scaffold_project(tmp_path)
        _write_artifact(tmp_path, "specs/requirements", "REQ-001.md", {
            "id": "REQ-001", "type": "requirement", "title": "Login", "status": "approved",
            "links": [],
        })
        _write_artifact(tmp_path, "specs/architecture", "ARCH-001.md", {
            "id": "ARCH-001", "type": "architecture", "title": "Auth Arch", "status": "approved",
            "links": [{"target": "REQ-001", "role": "derives_from"}],
        })
        baseline_lib.create_baseline(tmp_path, "v1.0")
        result = evidence_lib.generate_evidence_report(tmp_path, "v1.0")
        assert result["ok"]
        report = Path(result["path"]).read_text(encoding="utf-8")
        assert "Traceability Matrix" in report
        assert "REQ-001" in report
        assert "ARCH-001" in report

    def test_test_results_section(self, tmp_path: Path):
        _scaffold_project(tmp_path)
        _write_artifact(tmp_path, "specs/unit-tests", "UT-001.md", {
            "id": "UT-001", "type": "unit-test", "title": "Unit Test", "status": "verified",
        })
        baseline_lib.create_baseline(tmp_path, "v1.0")
        result = evidence_lib.generate_evidence_report(tmp_path, "v1.0")
        assert result["ok"]
        report = Path(result["path"]).read_text(encoding="utf-8")
        assert "Test Results Summary" in report
        assert "UT-001" in report

    def test_standards_compliance_section(self, tmp_path: Path):
        _scaffold_project(tmp_path)
        std_dir = tmp_path / ".specflow" / "standards"
        (std_dir / "demo.yaml").write_text(
            yaml.dump({
                "standard": "demo",
                "title": "Demo Standard",
                "version": "1.0",
                "clauses": [{"id": "C1", "title": "Clause 1", "severity": "high", "category": "safety"}],
            }),
            encoding="utf-8",
        )
        baseline_lib.create_baseline(tmp_path, "v1.0")
        result = evidence_lib.generate_evidence_report(tmp_path, "v1.0")
        assert result["ok"]
        report = Path(result["path"]).read_text(encoding="utf-8")
        assert "Standards Compliance" in report
        assert "Demo Standard" in report

    def test_baseline_diff_section(self, tmp_path: Path):
        _scaffold_project(tmp_path)
        baseline_lib.create_baseline(tmp_path, "v0.1")
        _write_artifact(tmp_path, "specs/requirements", "REQ-001.md", {
            "id": "REQ-001", "type": "requirement", "title": "New", "status": "draft",
        })
        baseline_lib.create_baseline(tmp_path, "v0.2")
        result = evidence_lib.generate_evidence_report(tmp_path, "v0.2")
        assert result["ok"]
        report = Path(result["path"]).read_text(encoding="utf-8")
        assert "Baseline Snapshot" in report
        assert "Changes from v0.1" in report
