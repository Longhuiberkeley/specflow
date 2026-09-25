"""Coverage for guided_by practice bindings and bp-application evidence."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from specflow.commands import artifact_lint as lint_cmd
from specflow.commands import trace as trace_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import role_targets


_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_TYPES = (
    "requirement", "architecture", "story", "best-practice", "decision",
    "unit-test", "integration-test", "qualification-test",
)


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True)
    for art_type in _SCHEMA_TYPES:
        source = _REPO_ROOT / "src/specflow/templates/schemas" / f"{art_type}.yaml"
        (schema_dir / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (root / ".specflow/config.yaml").write_text(
        yaml.safe_dump({"project": {"name": "bp-test"}, "active_packs": []}),
        encoding="utf-8",
    )
    for art_type in _SCHEMA_TYPES:
        (root / "_specflow" / art_lib.TYPE_TO_DIR[art_type]).mkdir(
            parents=True, exist_ok=True
        )
    return root


def _write_artifact(
    root: Path,
    artifact_id: str,
    art_type: str,
    *,
    status: str = "approved",
    links: list[dict[str, str]] | None = None,
    extra: dict | None = None,
    body: str = "Artifact body.",
) -> Path:
    path = root / "_specflow" / art_lib.TYPE_TO_DIR[art_type] / f"{artifact_id}.md"
    frontmatter = {
        "id": artifact_id,
        "title": artifact_id,
        "type": art_type,
        "status": status,
        "created": "2026-01-01",
        "links": links or [],
    }
    frontmatter.update(extra or {})
    path.write_text(
        f"---\n{yaml.safe_dump(frontmatter, sort_keys=False)}---\n\n{body}\n",
        encoding="utf-8",
    )
    return path


def _bp(root: Path, bp_id: str = "BP-001", **extra) -> Path:
    fields = {
        "provenance": "learned",
        "applicability": {"always": True},
        "strength": "recommended",
        "verification_method": "inspection",
    }
    fields.update(extra)
    return _write_artifact(
        root,
        bp_id,
        "best-practice",
        extra=fields,
        body=(
            "## Practice\nDo the thing.\n\n"
            "## Applies when\nAlways.\n\n"
            "## Work products\nThe artifact.\n\n"
            "## Verification\nInspect the result.\n\n"
            "## Rationale\nIt helps."
        ),
    )


@pytest.mark.parametrize("art_type,artifact_id", [
    ("requirement", "REQ-001"),
    ("architecture", "ARCH-001"),
    ("story", "STORY-001"),
])
def test_guided_by_bp_is_schema_and_role_target_legal(
    project_root: Path, art_type: str, artifact_id: str
):
    _bp(project_root)
    source = _write_artifact(
        project_root,
        artifact_id,
        art_type,
        links=[{"target": "BP-001", "role": "guided_by"}],
    )
    artifacts = [art_lib.parse_artifact(source)]
    bp = art_lib.parse_artifact(
        project_root / "_specflow/specs/best-practices/BP-001.md"
    )
    artifacts.append(bp)

    schema_result = lint_cmd.check_schema(
        artifacts, project_root / ".specflow/schema"
    )
    assert schema_result["blocking_count"] == 0
    assert not role_targets.check_role_targets(artifacts)


def test_trace_renders_guided_by_bp_edge(project_root: Path, capsys):
    _bp(project_root)
    _write_artifact(
        project_root,
        "REQ-001",
        "requirement",
        links=[{"target": "BP-001", "role": "guided_by"}],
    )
    assert trace_cmd.run(project_root, {"artifact_id": "REQ-001"}) == 0
    output = capsys.readouterr().out
    assert "BP-001" in output
    assert "(guided_by)" in output


def test_guided_by_does_not_inflate_chain_depth():
    bp = art_lib.Artifact(
        path=Path("BP-001.md"),
        frontmatter={"id": "BP-001", "type": "best-practice", "status": "approved"},
        body="",
    )
    req = art_lib.Artifact(
        path=Path("REQ-001.md"),
        frontmatter={"id": "REQ-001", "type": "requirement", "status": "approved"},
        body="",
        links=[art_lib.Link(target="BP-001", role="guided_by")],
    )
    index = art_lib.build_id_index([bp, req])
    assert art_lib.compute_chain_depth("BP-001", index) == ["BP-001"]


def test_dangling_guided_by_bp_edge_is_reported_by_links_check(project_root: Path):
    source = _write_artifact(
        project_root,
        "REQ-001",
        "requirement",
        links=[{"target": "BP-999", "role": "guided_by"}],
    )
    result = lint_cmd._check_links([art_lib.parse_artifact(source)], project_root)
    assert result["blocking_count"] == 1
    assert "BP-999 (not found)" in result["detail"]
