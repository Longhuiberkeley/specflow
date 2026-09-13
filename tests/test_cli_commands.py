"""Tests for specflow CLI commands — create, update, status."""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.commands import create as create_cmd
from specflow.commands import update as update_cmd
from specflow.commands import status as status_cmd
from specflow.commands import artifact_lint as lint_cmd

_SCHEMA_TYPES = [
    ("requirement", "REQ"), ("architecture", "ARCH"), ("detailed-design", "DDD"),
    ("unit-test", "UT"), ("integration-test", "IT"), ("qualification-test", "QT"),
    ("story", "STORY"), ("spike", "SPIKE"), ("decision", "DEC"),
    ("defect", "DEF"), ("challenge", "CHL"), ("audit", "AUD"),
]

_STATUS_FLOW = {
    "draft": [], "approved": ["draft"], "implemented": ["approved"], "verified": ["implemented"],
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
        (schema_dir / f"{art_type}.yaml").write_text(yaml.dump(schema), encoding="utf-8")

    config = {
        "project": {"name": "test-project", "created": "2026-01-01"},
        "impact_analysis": {"auto_flag": True, "auto_resolve": False, "remind_after": "7d"},
        "artifact_types": [t for t, _ in _SCHEMA_TYPES],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")

    state = {"current": "idle", "history": []}
    (root / ".specflow" / "state.yaml").write_text(yaml.dump(state), encoding="utf-8")

    for subdir in [
        "_specflow/specs/requirements", "_specflow/specs/architecture",
        "_specflow/specs/detailed-design", "_specflow/specs/unit-tests",
        "_specflow/specs/integration-tests", "_specflow/specs/qualification-tests",
        "_specflow/specs/challenges", "_specflow/specs/audits",
        "_specflow/work/stories", "_specflow/work/spikes",
        "_specflow/work/decisions", "_specflow/work/defects",
    ]:
        (root / subdir).mkdir(parents=True, exist_ok=True)

    return root


class TestCreateCommand:
    def test_creates_requirement(self, project_root: Path):
        rc = create_cmd.run(project_root, {
            "type": "requirement", "title": "Test requirement",
            "status": "draft", "priority": "high", "rationale": "Testing",
            "tags": "test, smoke", "links": None,
            "body": "The system shall do X.",
            "from_standard": None, "force": False,
            "skip_dedup_check": True, "nfr_category": None,
        })
        assert rc == 0
        req_dir = project_root / "_specflow" / "specs" / "requirements"
        files = list(req_dir.glob("REQ-*.md"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "Test requirement" in content
        assert "status: draft" in content

    def test_creates_story(self, project_root: Path):
        rc = create_cmd.run(project_root, {
            "type": "story", "title": "Implement feature",
            "status": "draft", "priority": None, "rationale": None,
            "tags": None, "links": None,
            "body": "As a user I want X.",
            "from_standard": None, "force": False,
            "skip_dedup_check": True, "nfr_category": None,
        })
        assert rc == 0
        story_dir = project_root / "_specflow" / "work" / "stories"
        files = list(story_dir.glob("STORY-*.md"))
        assert len(files) == 1

    def test_blocking_duplicate_renders_warning(self, project_root: Path, capsys):
        """Regression: the duplicate-warning header must not crash on a missing
        YELLOW import. A title+tags identical to an existing REQ trips the
        high-confidence dedup heuristic; with --force the create proceeds after
        printing the warning header (which previously raised NameError: YELLOW)."""
        common = {
            "type": "requirement", "status": "draft", "priority": "high",
            "rationale": "Testing", "links": None,
            "body": "The system shall authenticate users.",
            "from_standard": None, "nfr_category": None,
        }
        # Two distinct REQs first (IDF needs >1 doc with discriminating tokens).
        create_cmd.run(project_root, {
            **common, "title": "User login flow", "tags": "auth, login",
            "force": False, "skip_dedup_check": True,
        })
        create_cmd.run(project_root, {
            **common, "title": "Payment gateway integration", "tags": "billing",
            "force": False, "skip_dedup_check": True,
        })

        # Third create duplicates the first: hits the blocking-duplicate display
        # path that previously raised NameError: name 'YELLOW'.
        rc = create_cmd.run(project_root, {
            **common, "title": "User login flow", "tags": "auth, login",
            "force": True, "skip_dedup_check": False,
        })
        assert rc == 0
        out = capsys.readouterr().out
        assert "Possible duplicate" in out
        req_dir = project_root / "_specflow" / "specs" / "requirements"
        assert len(list(req_dir.glob("REQ-*.md"))) == 3

    def test_missing_type_returns_error(self, project_root: Path):
        rc = create_cmd.run(project_root, {
            "type": "", "title": "No type",
            "status": "draft", "priority": None, "rationale": None,
            "tags": None, "links": None, "body": "",
            "from_standard": None, "force": False,
            "skip_dedup_check": True, "nfr_category": None,
        })
        assert rc == 1

    def test_missing_title_returns_error(self, project_root: Path):
        rc = create_cmd.run(project_root, {
            "type": "requirement", "title": "",
            "status": "draft", "priority": None, "rationale": None,
            "tags": None, "links": None, "body": "",
            "from_standard": None, "force": False,
            "skip_dedup_check": True, "nfr_category": None,
        })
        assert rc == 1


class TestUpdateCommand:
    def test_updates_status(self, project_root: Path):
        create_cmd.run(project_root, {
            "type": "requirement", "title": "Test REQ",
            "status": "draft", "priority": None, "rationale": None,
            "tags": None, "links": None, "body": "Body.",
            "from_standard": None, "force": False,
            "skip_dedup_check": True, "nfr_category": None,
        })
        req_file = list((project_root / "_specflow" / "specs" / "requirements").glob("REQ-*.md"))[0]
        rc = update_cmd.run(project_root, {
            "artifact_id": req_file.stem,
            "status": "approved", "priority": None,
            "rationale": None, "tags": None, "title": None,
        })
        assert rc == 0
        assert "status: approved" in req_file.read_text()

    def test_updates_title(self, project_root: Path):
        create_cmd.run(project_root, {
            "type": "requirement", "title": "Original title",
            "status": "draft", "priority": None, "rationale": None,
            "tags": None, "links": None, "body": "Body.",
            "from_standard": None, "force": False,
            "skip_dedup_check": True, "nfr_category": None,
        })
        req_id = list((project_root / "_specflow" / "specs" / "requirements").glob("REQ-*.md"))[0].stem
        rc = update_cmd.run(project_root, {
            "artifact_id": req_id,
            "status": None, "priority": None,
            "rationale": None, "tags": None, "title": "Updated title",
        })
        assert rc == 0

    def test_nonexistent_artifact_returns_error(self, project_root: Path):
        rc = update_cmd.run(project_root, {
            "artifact_id": "REQ-999",
            "status": "approved", "priority": None,
            "rationale": None, "tags": None, "title": None,
        })
        assert rc == 1

    def test_no_fields_returns_error(self, project_root: Path):
        rc = update_cmd.run(project_root, {
            "artifact_id": "REQ-001",
            "status": None, "priority": None,
            "rationale": None, "tags": None, "title": None,
        })
        assert rc == 1


class TestStatusCommand:
    def test_runs_on_empty_project(self, project_root: Path):
        rc = status_cmd.run(project_root, {})
        assert rc == 0

    def test_runs_with_artifacts(self, project_root: Path):
        create_cmd.run(project_root, {
            "type": "requirement", "title": "Test REQ",
            "status": "draft", "priority": None, "rationale": None,
            "tags": None, "links": None, "body": "Body.",
            "from_standard": None, "force": False,
            "skip_dedup_check": True, "nfr_category": None,
        })
        rc = status_cmd.run(project_root, {})
        assert rc == 0


class TestLintPublicAPI:
    def test_check_schema_public(self):
        assert callable(lint_cmd.check_schema)

    def test_check_coverage_public(self):
        assert callable(lint_cmd.check_coverage)


# ── STORY-663: specflow pack-validate ──────────────────────────────────────

PACKS_SRC_DIR = Path(__file__).parent.parent / "src" / "specflow" / "packs"


class TestPackValidate:
    """`specflow pack-validate` is the deterministic backstop the pack-author
    skill's validate-pack.sh forwards to (STORY-663): pack.yaml schema,
    referenced skill files exist, and no 'uv run' in shipped skill scripts."""

    def _make_pack(self, tmp_path: Path, name: str = "demo") -> Path:
        pack_dir = tmp_path / name
        pack_dir.mkdir(parents=True)
        (pack_dir / "pack.yaml").write_text(
            yaml.dump({
                "name": name,
                "version": "0.1.0",
                "description": "demo pack",
                "adds_skills": ["demo-skill"],
            }),
            encoding="utf-8",
        )
        skill = pack_dir / "skills" / "demo-skill"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("# demo skill\n", encoding="utf-8")
        return pack_dir

    def test_valid_pack_passes(self, tmp_path: Path, capsys):
        from specflow.commands import pack_validate as pv
        pack_dir = self._make_pack(tmp_path)
        rc = pv.run(tmp_path, {"pack_dir": str(pack_dir)})
        assert rc == 0
        out = capsys.readouterr().out
        assert "Success: Pack validation passed" in out

    def test_missing_pack_dir_fails(self, tmp_path: Path, capsys):
        from specflow.commands import pack_validate as pv
        rc = pv.run(tmp_path, {"pack_dir": str(tmp_path / "nope")})
        assert rc == 1
        assert "Not a directory" in capsys.readouterr().out

    def test_missing_pack_yaml_fails(self, tmp_path: Path, capsys):
        from specflow.commands import pack_validate as pv
        empty = tmp_path / "empty-pack"
        empty.mkdir()
        rc = pv.run(tmp_path, {"pack_dir": str(empty)})
        assert rc == 1
        assert "pack.yaml" in capsys.readouterr().out

    def test_missing_required_field_fails(self, tmp_path: Path, capsys):
        from specflow.commands import pack_validate as pv
        pack_dir = self._make_pack(tmp_path)
        manifest = yaml.safe_load((pack_dir / "pack.yaml").read_text())
        del manifest["version"]
        (pack_dir / "pack.yaml").write_text(yaml.dump(manifest), encoding="utf-8")
        rc = pv.run(tmp_path, {"pack_dir": str(pack_dir)})
        assert rc == 1
        assert "version" in capsys.readouterr().out

    def test_referenced_skill_missing_fails(self, tmp_path: Path, capsys):
        from specflow.commands import pack_validate as pv
        pack_dir = self._make_pack(tmp_path)
        (pack_dir / "skills" / "demo-skill" / "SKILL.md").unlink()
        rc = pv.run(tmp_path, {"pack_dir": str(pack_dir)})
        assert rc == 1
        out = capsys.readouterr().out
        assert "Referenced skill missing" in out
        assert "demo-skill" in out

    def test_standards_missing_clauses_fails(self, tmp_path: Path, capsys):
        from specflow.commands import pack_validate as pv
        pack_dir = self._make_pack(tmp_path)
        std = pack_dir / "standards"
        std.mkdir()
        (std / "demo.yaml").write_text(
            yaml.dump({"standard": "demo", "title": "Demo"}), encoding="utf-8"
        )
        rc = pv.run(tmp_path, {"pack_dir": str(pack_dir)})
        assert rc == 1
        assert "clauses" in capsys.readouterr().out

    def test_schema_missing_directory_field_fails(self, tmp_path: Path, capsys):
        from specflow.commands import pack_validate as pv
        pack_dir = self._make_pack(tmp_path)
        schemas = pack_dir / "schemas"
        schemas.mkdir()
        (schemas / "demo.yaml").write_text(
            yaml.dump({
                "type": "demo", "prefix": "DEM", "id_format": "DEM-###",
                "required_fields": ["id"], "allowed_status": {"draft": []},
            }),
            encoding="utf-8",
        )
        rc = pv.run(tmp_path, {"pack_dir": str(pack_dir)})
        assert rc == 1
        assert "directory" in capsys.readouterr().out

    def test_uv_run_in_shipped_script_fails(self, tmp_path: Path, capsys):
        from specflow.commands import pack_validate as pv
        pack_dir = self._make_pack(tmp_path)
        scripts = pack_dir / "skills" / "demo-skill" / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "check.sh").write_text(
            "#!/usr/bin/env bash\nuv run python3 -c 'pass'\n", encoding="utf-8"
        )
        rc = pv.run(tmp_path, {"pack_dir": str(pack_dir)})
        assert rc == 1
        out = capsys.readouterr().out
        assert "uv run" in out
        assert "check.sh" in out

    def test_cli_parser_routes_pack_validate(self, tmp_path: Path, monkeypatch, capsys):
        from specflow import cli
        pack_dir = self._make_pack(tmp_path)
        monkeypatch.chdir(tmp_path)
        rc = cli.main(["pack-validate", str(pack_dir)])
        assert rc == 0
        assert "Success: Pack validation passed" in capsys.readouterr().out

    @pytest.mark.parametrize("pack_name", [
        "autoresearch", "adoption", "ops", "tldr-communication", "iso26262-demo",
    ])
    def test_builtin_packs_validate(self, tmp_path: Path, pack_name: str, capsys):
        from specflow.commands import pack_validate as pv
        rc = pv.run(tmp_path, {"pack_dir": str(PACKS_SRC_DIR / pack_name)})
        assert rc == 0, capsys.readouterr().out

    def test_shipped_validate_pack_shells_forward_without_uv_run(self):
        """Both shipped copies of validate-pack.sh forward to
        `specflow pack-validate` and contain no 'uv run' (STORY-663)."""
        repo_root = Path(__file__).parent.parent
        copies = [
            repo_root / ".claude" / "skills" / "specflow-pack-author" / "scripts" / "validate-pack.sh",
            repo_root / "src" / "specflow" / "templates" / "skills" / "shared"
            / "specflow-pack-author" / "scripts" / "validate-pack.sh",
        ]
        for path in copies:
            text = path.read_text(encoding="utf-8")
            assert "uv run" not in text, f"{path} still contains 'uv run'"
            assert "pack-validate" in text, f"{path} must forward to specflow pack-validate"
