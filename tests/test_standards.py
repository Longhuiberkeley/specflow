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


# ── F-110: malformed standards report the file and parse error ───────────────


def _write_raw_standard(root: Path, name: str, text: str) -> Path:
    d = root / ".specflow" / "standards"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{name}.yaml"
    path.write_text(text, encoding="utf-8")
    return path


class TestLoadStandardChecked:
    def test_valid_returns_data_and_no_error(self, tmp_path: Path):
        _write_standard(tmp_path, "ok", {"standard": "ok", "title": "T", "clauses": []})
        data, error = standards_lib.load_standard_checked(tmp_path, "ok")
        assert data is not None and data["standard"] == "ok"
        assert error is None

    def test_missing_names_the_path(self, tmp_path: Path):
        data, error = standards_lib.load_standard_checked(tmp_path, "nope")
        assert data is None
        assert "not found" in error
        assert "nope.yaml" in error

    def test_malformed_yaml_reports_parse_error_not_not_found(self, tmp_path: Path):
        path = _write_raw_standard(tmp_path, "broken", "standard: broken\nclauses: [unclosed\n")
        data, error = standards_lib.load_standard_checked(tmp_path, "broken")
        assert data is None
        assert "not found" not in error
        assert "unreadable" in error
        # Path is rendered relative to the project root: these errors are copied
        # into evidence packs, which must not become machine-specific.
        assert ".specflow/standards/broken.yaml" in error
        assert str(path) not in error
        # The YAML parser's own diagnostic is carried through.
        assert "line" in error

    def test_non_mapping_reports_shape(self, tmp_path: Path):
        path = _write_raw_standard(tmp_path, "listy", "- just\n- a list\n")
        data, error = standards_lib.load_standard_checked(tmp_path, "listy")
        assert data is None
        assert "YAML mapping" in error
        assert "list" in error
        assert ".specflow/standards/listy.yaml" in error
        assert str(path) not in error

    def test_load_standard_wrapper_still_returns_none(self, tmp_path: Path):
        _write_raw_standard(tmp_path, "broken", "clauses: [unclosed\n")
        assert standards_lib.load_standard(tmp_path, "broken") is None


class TestLoadStandardsChecked:
    def test_errors_are_surfaced_and_good_files_still_load(self, tmp_path: Path):
        _write_standard(tmp_path, "good", {"standard": "good", "title": "G", "clauses": []})
        _write_raw_standard(tmp_path, "bad", "clauses: [unclosed\n")
        loaded, errors = standards_lib.load_standards_checked(tmp_path)
        assert [s["standard"] for s in loaded] == ["good"]
        assert set(errors) == {"bad"}
        assert "unreadable" in errors["bad"]
        # The error-blind wrapper keeps its contract (good ones only).
        assert [s["standard"] for s in standards_lib.load_standards(tmp_path)] == ["good"]


class TestCheckComplianceMalformed:
    def test_single_malformed_standard_names_file_not_not_found(self, tmp_path: Path):
        path = _write_raw_standard(tmp_path, "only", "standard: only\nclauses: [unclosed\n")
        # Auto-picked because it is the only installed standard: the user never
        # typed its name, so "not found" would be a lie.
        result = standards_lib.check_compliance(tmp_path)
        assert not result["ok"]
        assert "not found" not in result["error"]
        assert "unreadable" in result["error"]
        assert ".specflow/standards/only.yaml" in result["error"]
        assert str(path) not in result["error"]
        assert result["available"] == ["only"]

    def test_non_mapping_standard_reported_as_such(self, tmp_path: Path):
        _write_raw_standard(tmp_path, "listy", "- a\n")
        result = standards_lib.check_compliance(tmp_path, "listy")
        assert not result["ok"]
        assert "YAML mapping" in result["error"]

    def test_multiple_with_one_unreadable_lists_it(self, tmp_path: Path):
        _write_standard(tmp_path, "good", {"standard": "good", "title": "G", "clauses": []})
        _write_raw_standard(tmp_path, "bad", "clauses: [unclosed\n")
        result = standards_lib.check_compliance(tmp_path)
        assert not result["ok"]
        assert "specify --standard" in result["error"]
        assert "bad" in result["unreadable"]
        assert "Unreadable" in result["error"]

    def test_gaps_command_prints_parse_error_and_exits_1(self, tmp_path: Path, capsys):
        from specflow.commands import standards_gaps as gaps_cmd

        _write_raw_standard(tmp_path, "only", "clauses: [unclosed\n")
        rc = gaps_cmd.run(tmp_path, {})
        out = capsys.readouterr().out
        assert rc == 1
        assert "only.yaml" in out
        assert "not found" not in out


# ── F-070: no standards installed is neutral, exit 0, no init --preset hint ──


class TestNoStandardsInstalledIsNeutral:
    def test_check_compliance_flags_none_installed(self, tmp_path: Path):
        result = standards_lib.check_compliance(tmp_path)
        assert not result["ok"]
        assert result["none_installed"] is True
        assert "No standards installed" in result["error"]
        assert "init --preset" not in result["error"]
        assert "/specflow-pack-author" in result["error"]

    def test_gaps_command_exits_0_with_neutral_message(self, tmp_path: Path, capsys):
        from specflow.commands import standards_gaps as gaps_cmd

        rc = gaps_cmd.run(tmp_path, {})
        out = capsys.readouterr().out
        assert rc == 0
        assert "No standards installed" in out
        assert "✗" not in out
        assert "init --preset" not in out

    def test_gaps_command_json_exits_0(self, tmp_path: Path, capsys):
        import json

        from specflow.commands import standards_gaps as gaps_cmd

        rc = gaps_cmd.run(tmp_path, {"json": True})
        payload = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert payload["standard"] is None
        assert payload["gaps"] == []
        assert "No standards installed" in payload["message"]


# ── F-113: every uncovered clause carries a create --from-standard hint ──────


class TestRemediationCommandHint:
    def test_suggest_remediation_appends_command(self):
        clause = {"id": "SEC-9", "category": "security", "severity": "medium"}
        result = standards_lib.suggest_remediation(clause)
        assert result.endswith("→ specflow create --from-standard SEC-9")
        assert "threat-model" in result

    def test_no_id_no_command(self):
        result = standards_lib.suggest_remediation({"category": "safety"})
        assert "--from-standard" not in result

    def test_uncovered_entries_and_dashboard_show_command(self, tmp_path: Path, capsys):
        from specflow.commands import standards_gaps as gaps_cmd

        _write_standard(tmp_path, "s1", {
            "standard": "s1",
            "title": "T",
            "clauses": [
                {"id": "C1", "title": "A", "severity": "high"},
                {"id": "C2", "title": "B"},
            ],
        })
        result = standards_lib.check_compliance(tmp_path, "s1")
        hints = [c["remediation"] for c in result["uncovered"]]
        assert any("specflow create --from-standard C1" in h for h in hints)
        assert any("specflow create --from-standard C2" in h for h in hints)

        assert all(c["command"] == f"specflow create --from-standard {c['clause_id']}"
                   for c in result["uncovered"])

        rc = gaps_cmd.run(tmp_path, {})
        out = capsys.readouterr().out
        assert rc == 0
        assert "run: specflow create --from-standard C1" in out
        assert "run: specflow create --from-standard C2" in out
        # The command sits on its own line, not behind a second arrow.
        for line in out.splitlines():
            assert line.count("→") <= 1, line
            if "--from-standard" in line:
                assert "→" not in line, line

    def test_json_remediation_keeps_command_inline(self, tmp_path: Path, capsys):
        import json

        from specflow.commands import standards_gaps as gaps_cmd

        _write_standard(tmp_path, "s1", {
            "standard": "s1", "title": "T",
            "clauses": [{"id": "C1", "title": "A"}],
        })
        rc = gaps_cmd.run(tmp_path, {"json": True})
        payload = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert payload["gaps"][0]["remediation"].endswith(
            "→ specflow create --from-standard C1"
        )

    def test_advertised_command_runs_clean_through_the_real_handler(
        self, tmp_path: Path, capsys
    ):
        """`specflow create --from-standard <id>` must exit 0 and link the clause.

        Runs the real `create` handler with the argparse shape of
        `specflow create --from-standard C1` (type=None, title=None). The hint
        printed by `standards gaps` is only honest if this path has no
        traceback; a crash after the file is written makes agents retry and
        mint duplicate REQs.
        """
        from specflow.commands import create as create_cmd

        root = tmp_path / "project"
        schema_dir = root / ".specflow" / "schema"
        schema_dir.mkdir(parents=True)
        schema_dir.joinpath("requirement.yaml").write_text(yaml.dump({
            "type": "requirement", "prefix": "REQ",
            "allowed_status": {"draft": [], "approved": ["draft"]},
        }), encoding="utf-8")
        (root / ".specflow" / "config.yaml").write_text(yaml.dump({
            "project": {"name": "t", "created": "2026-01-01"},
            "artifact_types": ["requirement"], "active_packs": [],
        }), encoding="utf-8")
        (root / ".specflow" / "state.yaml").write_text(
            yaml.dump({"current": "idle", "history": []}), encoding="utf-8"
        )
        (root / "_specflow" / "specs" / "requirements").mkdir(parents=True)
        _write_standard(root, "s1", {
            "standard": "s1", "title": "T",
            "clauses": [{"id": "C1", "title": "Clause one", "description": "Shall."}],
        })

        rc = create_cmd.run(root, {
            "type": None, "title": None, "status": None, "priority": None,
            "rationale": None, "tags": None, "links": None, "body": None,
            "from_standard": "C1", "force": False, "skip_dedup_check": True,
            "nfr_category": None, "set_fields": None,
        })
        out = capsys.readouterr().out
        assert rc == 0, out
        assert "Traceback" not in out
        assert "✓ Created REQ-001" in out

        from specflow.lib import artifacts as art_lib

        reqs = art_lib.discover_artifacts(root, artifact_type="requirement")
        assert len(reqs) == 1
        links = reqs[0].frontmatter.get("links", [])
        assert {"target": "C1", "role": "complies_with"} in links
