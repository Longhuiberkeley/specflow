"""STORY-683: malformed schema files fail loud.

Pre-STORY-683 ``_load_active_packs`` (and ``lint.load_schemas``) swallowed a
malformed ``.specflow/schema/*.yaml`` with ``try/except: continue`` — a pack
type silently vanished and its artifacts degraded to "Unknown type" warnings.
Now the registration pass records the error and ``check_schema`` emits a
BLOCKING ``schema-error`` naming the file, so ``artifact-lint --type schema``
(and project-audit's consistency lens) exit non-zero.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.commands import artifact_lint as lint_cmd
from specflow.commands import project_audit as audit_cmd
from specflow.lib import artifacts as art_lib


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True)
    (schema_dir / "requirement.yaml").write_text(
        yaml.dump({"type": "requirement", "prefix": "REQ",
                   "allowed_status": {"draft": [], "approved": ["draft"]}}),
        encoding="utf-8",
    )
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump({"project": {"name": "t"}}), encoding="utf-8"
    )
    req_dir = root / "_specflow" / "specs" / "requirements"
    req_dir.mkdir(parents=True)
    (req_dir / "REQ-001.md").write_text(
        "---\nid: REQ-001\ntitle: T\ntype: requirement\nstatus: draft\n"
        "tags: []\nsuspect: false\nlinks: []\n---\n\n# T\n\n"
        "## Acceptance Criteria\n\n1. Given X\n",
        encoding="utf-8",
    )
    return root


def _break(root: Path, name: str = "broken-pack.yaml",
           text: str = "type: experiment\nprefix: [EXPT\n") -> Path:
    p = root / ".specflow" / "schema" / name
    p.write_text(text, encoding="utf-8")
    return p


class TestSchemaRegistrationErrors:
    def test_malformed_yaml_is_recorded_with_file(self, tmp_path):
        root = _project(tmp_path)
        _break(root)
        errs = art_lib.schema_registration_errors(root / ".specflow" / "schema")
        assert len(errs) == 1
        path, msg = errs[0]
        assert path.name == "broken-pack.yaml"
        assert msg

    def test_non_mapping_schema_is_recorded(self, tmp_path):
        root = _project(tmp_path)
        _break(root, "list.yaml", "- a\n- b\n")
        errs = art_lib.schema_registration_errors(root / ".specflow" / "schema")
        assert [p.name for p, _ in errs] == ["list.yaml"]
        assert "mapping" in errs[0][1]

    def test_clean_schema_dir_has_no_errors(self, tmp_path):
        root = _project(tmp_path)
        assert art_lib.schema_registration_errors(root / ".specflow" / "schema") == []

    def test_discover_still_loads_valid_types(self, tmp_path):
        # Registration continues past the bad file (errors are surfaced, not
        # fatal to discovery), so every other command keeps working.
        root = _project(tmp_path)
        _break(root)
        arts = art_lib.discover_artifacts(root)
        assert [a.id for a in arts] == ["REQ-001"]


class TestCheckSchemaSurfacesError:
    def test_blocking_schema_error_names_file(self, tmp_path):
        root = _project(tmp_path)
        _break(root)
        arts = art_lib.discover_artifacts(root)
        result = lint_cmd.check_schema(arts, root / ".specflow" / "schema")
        assert result["blocking_count"] >= 1
        assert "schema-error" in result["detail"]
        assert "broken-pack.yaml" in result["detail"]
        assert "✗" in result["detail"]

    def test_cli_schema_check_exits_nonzero(self, tmp_path, capsys):
        root = _project(tmp_path)
        assert lint_cmd.run(root, {"type": "schema"}) == 0
        capsys.readouterr()
        _break(root)
        rc = lint_cmd.run(root, {"type": "schema"})
        out = capsys.readouterr().out
        assert rc != 0
        assert "broken-pack.yaml" in out

    def test_project_audit_consistency_errors(self, tmp_path, capsys):
        root = _project(tmp_path)
        _break(root)
        rc = audit_cmd.run(root, {"dry_run": True})
        capsys.readouterr()
        assert rc == 3
