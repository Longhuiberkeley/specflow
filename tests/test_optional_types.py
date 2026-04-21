"""Tests for optional artifact type schemas and init integration."""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.commands import init as init_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import lint as lint_lib
from specflow.lib import scaffold as scaffold_lib
from specflow.lib import config as config_lib


_SCHEMA_DIR = Path(__file__).parent.parent / "src" / "specflow" / "templates" / "schemas"
_OPTIONAL_DIR = _SCHEMA_DIR / "optional"

_OPTIONAL_TYPES = ["hazard", "risk", "control"]


class TestOptionalSchemas:
    def test_all_optional_schemas_exist(self):
        for type_name in _OPTIONAL_TYPES:
            path = _OPTIONAL_DIR / f"{type_name}.yaml"
            assert path.exists(), f"Schema {type_name}.yaml not found"

    def test_schema_structure(self):
        required_keys = {"type", "prefix", "id_format", "required_fields", "allowed_status", "allowed_link_roles", "directory"}
        for type_name in _OPTIONAL_TYPES:
            path = _OPTIONAL_DIR / f"{type_name}.yaml"
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            assert isinstance(data, dict)
            assert required_keys.issubset(set(data.keys())), f"{type_name} missing keys: {required_keys - set(data.keys())}"

    def test_hazard_schema(self):
        data = yaml.safe_load((_OPTIONAL_DIR / "hazard.yaml").read_text(encoding="utf-8"))
        assert data["type"] == "hazard"
        assert data["prefix"] == "HAZ"
        assert "draft" in data["allowed_status"]

    def test_risk_schema(self):
        data = yaml.safe_load((_OPTIONAL_DIR / "risk.yaml").read_text(encoding="utf-8"))
        assert data["type"] == "risk"
        assert data["prefix"] == "RISK"

    def test_control_schema(self):
        data = yaml.safe_load((_OPTIONAL_DIR / "control.yaml").read_text(encoding="utf-8"))
        assert data["type"] == "control"
        assert data["prefix"] == "CTRL"


def _scaffold_project(root: Path) -> None:
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)

    for schema_file in _SCHEMA_DIR.glob("*.yaml"):
        (schema_dir / schema_file.name).write_text(schema_file.read_text(encoding="utf-8"), encoding="utf-8")

    config = config_lib.default_config(root.name)
    config_lib.write_config(root, config)

    state = config_lib.default_state()
    config_lib.write_state(root, state)

    scaffold_lib.create_spec_dirs(root)


class TestInstallOptionalTypes:
    def test_install_hazard(self, tmp_path: Path):
        _scaffold_project(tmp_path)
        result = init_cmd._install_optional_types(tmp_path, ["hazard"])
        assert result == 0
        assert (tmp_path / ".specflow" / "schema" / "hazard.yaml").exists()
        assert (tmp_path / "_specflow" / "specs" / "hazards").exists()

    def test_install_multiple(self, tmp_path: Path):
        _scaffold_project(tmp_path)
        result = init_cmd._install_optional_types(tmp_path, ["hazard", "risk", "control"])
        assert result == 0
        assert (tmp_path / ".specflow" / "schema" / "hazard.yaml").exists()
        assert (tmp_path / ".specflow" / "schema" / "risk.yaml").exists()
        assert (tmp_path / ".specflow" / "schema" / "control.yaml").exists()
        assert (tmp_path / "_specflow" / "specs" / "hazards").exists()
        assert (tmp_path / "_specflow" / "specs" / "risks").exists()
        assert (tmp_path / "_specflow" / "specs" / "controls").exists()

    def test_idempotent_no_duplicates(self, tmp_path: Path):
        _scaffold_project(tmp_path)
        init_cmd._install_optional_types(tmp_path, ["hazard"])
        init_cmd._install_optional_types(tmp_path, ["hazard"])
        assert (tmp_path / ".specflow" / "schema" / "hazard.yaml").exists()

    def test_unknown_type_returns_error(self, tmp_path: Path):
        _scaffold_project(tmp_path)
        result = init_cmd._install_optional_types(tmp_path, ["nonexistent"])
        assert result == 1


class TestCreateWithOptionalType:
    def test_create_hazard_artifact(self, tmp_path: Path):
        _scaffold_project(tmp_path)
        init_cmd._install_optional_types(tmp_path, ["hazard"])

        result = art_lib.create_artifact(
            tmp_path,
            artifact_type="hazard",
            title="Identify brake failure",
            status="draft",
        )
        assert result["ok"], result.get("error", "")
        assert "HAZ-001" in result.get("path", "")

        art = art_lib.parse_artifact(Path(result["path"]))
        assert art is not None
        assert art.type == "hazard"
        assert art.id == "HAZ-001"

    def test_create_control_artifact(self, tmp_path: Path):
        _scaffold_project(tmp_path)
        init_cmd._install_optional_types(tmp_path, ["control"])

        result = art_lib.create_artifact(
            tmp_path,
            artifact_type="control",
            title="Access control policy",
            status="draft",
        )
        assert result["ok"], result.get("error", "")
        assert "CTRL-001" in result.get("path", "")


class TestTraceWithOptionalType:
    def test_trace_hazard(self, tmp_path: Path):
        _scaffold_project(tmp_path)
        init_cmd._install_optional_types(tmp_path, ["hazard"])

        art_lib.create_artifact(tmp_path, artifact_type="hazard", title="Brake failure", status="draft")
        art_lib.create_artifact(
            tmp_path, artifact_type="requirement", title="Mitigate brake failure", status="draft",
            links=[{"target": "HAZ-001", "role": "derives_from"}],
        )

        artifacts = art_lib.discover_artifacts(tmp_path)
        id_index = art_lib.build_id_index(artifacts)
        assert "HAZ-001" in id_index
        assert "REQ-001" in id_index

        chain = art_lib.trace_chain("HAZ-001", id_index, direction="downstream")
        downstream_ids = [n["id"] for n in chain["downstream"]]
        assert "REQ-001" in downstream_ids


class TestLintWithOptionalType:
    def test_lint_validates_hazard_schema(self, tmp_path: Path):
        _scaffold_project(tmp_path)
        init_cmd._install_optional_types(tmp_path, ["hazard"])

        art_lib.create_artifact(tmp_path, artifact_type="hazard", title="Valid hazard", status="draft")
        artifacts = art_lib.discover_artifacts(tmp_path)
        id_index = art_lib.build_id_index(artifacts)
        haz = id_index.get("HAZ-001")
        assert haz is not None

        schemas = lint_lib.load_schemas(tmp_path / ".specflow" / "schema")
        assert "hazard" in schemas
        issues = lint_lib.validate_artifact_schema(haz, schemas["hazard"])
        blocking = [i for i in issues if i.get("severity") == "blocking"]
        assert len(blocking) == 0
