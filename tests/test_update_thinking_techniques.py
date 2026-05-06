"""Tests for specflow update --thinking-techniques flag."""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.commands import update as update_cmd
from specflow.lib import artifacts as art_lib


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)

    for art_type, prefix in [
        ("requirement", "REQ"), ("architecture", "ARCH"),
        ("detailed-design", "DDD"), ("story", "STORY"),
    ]:
        schema = {
            "type": art_type,
            "prefix": prefix,
            "id_format": f"{prefix}-" + r"\d{3}",
            "required_fields": ["id", "title", "type", "status", "created"],
            "optional_fields": ["thinking_techniques", "tags", "fingerprint", "links"],
            "allowed_status": {"draft": [], "approved": ["draft"]},
        }
        (schema_dir / f"{art_type}.yaml").write_text(
            yaml.dump(schema), encoding="utf-8"
        )

    config = {
        "project": {"name": "test-project"},
        "artifact_types": ["requirement", "architecture", "detailed-design", "story"],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump(config), encoding="utf-8"
    )
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "idle"}), encoding="utf-8"
    )

    for subdir in [
        "_specflow/specs/requirements", "_specflow/specs/architecture",
        "_specflow/specs/detailed-design", "_specflow/work/stories",
    ]:
        (root / subdir).mkdir(parents=True, exist_ok=True)

    return root


def _create_artifact(root: Path, art_id: str = "REQ-001") -> Path:
    req_dir = root / "_specflow" / "specs" / "requirements"
    index_path = req_dir / "_index.yaml"
    if not index_path.exists():
        index_path.write_text(yaml.dump({"artifacts": {}, "next_id": 2}), encoding="utf-8")

    fm = {
        "id": art_id,
        "title": f"Test {art_id}",
        "type": "requirement",
        "status": "draft",
        "created": "2026-01-01",
        "suspect": False,
        "links": [],
    }
    content = f"---\n{yaml.dump(fm, default_flow_style=False, sort_keys=False)}---\n\n# Test\n\nBody\n"
    path = req_dir / f"{art_id}.md"
    path.write_text(content, encoding="utf-8")

    index_data = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    index_data["artifacts"][art_id] = {"id": art_id, "title": f"Test {art_id}", "status": "draft", "tags": [], "fingerprint": "sha256:abc", "children": []}
    index_path.write_text(yaml.dump(index_data, default_flow_style=False, sort_keys=False), encoding="utf-8")

    return path


def test_thinking_techniques_appends_to_empty(project_root: Path):
    _create_artifact(project_root)
    rc = update_cmd.run(project_root, {
        "artifact_id": "REQ-001",
        "thinking_techniques": "premortem,devils_advocate",
    })
    assert rc == 0

    art = art_lib.parse_artifact(project_root / "_specflow" / "specs" / "requirements" / "REQ-001.md")
    assert art is not None
    techniques = art.frontmatter.get("thinking_techniques", [])
    assert "premortem" in techniques
    assert "devils_advocate" in techniques


def test_thinking_techniques_appends_to_existing(project_root: Path):
    _create_artifact(project_root)

    rc1 = update_cmd.run(project_root, {
        "artifact_id": "REQ-001",
        "thinking_techniques": "premortem",
    })
    assert rc1 == 0

    rc2 = update_cmd.run(project_root, {
        "artifact_id": "REQ-001",
        "thinking_techniques": "devils_advocate,stress_scale",
    })
    assert rc2 == 0

    art = art_lib.parse_artifact(project_root / "_specflow" / "specs" / "requirements" / "REQ-001.md")
    techniques = art.frontmatter.get("thinking_techniques", [])
    assert techniques == ["premortem", "devils_advocate", "stress_scale"]


def test_thinking_techniques_deduplicates(project_root: Path):
    _create_artifact(project_root)

    update_cmd.run(project_root, {"artifact_id": "REQ-001", "thinking_techniques": "premortem"})
    update_cmd.run(project_root, {"artifact_id": "REQ-001", "thinking_techniques": "premortem,devils_advocate"})

    art = art_lib.parse_artifact(project_root / "_specflow" / "specs" / "requirements" / "REQ-001.md")
    techniques = art.frontmatter.get("thinking_techniques", [])
    assert techniques == ["premortem", "devils_advocate"]


def test_thinking_techniques_not_in_args_is_noop(project_root: Path):
    _create_artifact(project_root)
    rc = update_cmd.run(project_root, {"artifact_id": "REQ-001", "status": "approved"})
    assert rc == 0

    art = art_lib.parse_artifact(project_root / "_specflow" / "specs" / "requirements" / "REQ-001.md")
    assert "thinking_techniques" not in art.frontmatter
