"""Regression coverage for the five-section practice spine."""

from __future__ import annotations

from pathlib import Path

from specflow.commands.artifact_lint import _check_status
from specflow.lib import artifacts as art_lib
from specflow.lib import lint as lint_lib
from specflow.lib import practices


_STATUS_MAP_BYTES = (
    b"allowed_status:\n"
    b"  draft: []\n"
    b"  approved: [draft, active]\n"
    b"  superseded: [approved, active]\n"
)


def test_anatomy_renderer_emits_all_sections_in_order():
    rendered = practices.render_practice_body(
        "Do the practice.", "On relevant work.", "A decision record.",
        "Inspect the record.", "It reduces risk.",
    )
    headings = [line for line in rendered.splitlines() if line.startswith("## ")]
    assert headings == [f"## {section}" for section in practices.PRACTICE_SECTIONS]
    assert practices.validate_anatomy(rendered) == []


def test_best_practice_status_map_is_pinned_byte_for_byte():
    schema_path = Path(__file__).parents[1] / "src/specflow/templates/schemas/best-practice.yaml"
    schema = schema_path.read_bytes()
    assert _STATUS_MAP_BYTES in schema


def test_active_legacy_bp_remains_valid_under_collapsed_status_map(tmp_path: Path):
    schema = {
        "type": "best-practice",
        "allowed_status": {
            "draft": [],
            "approved": ["draft", "active"],
            "superseded": ["approved", "active"],
        },
    }
    bp = art_lib.Artifact(
        path=tmp_path / "BP-001.md",
        frontmatter={"id": "BP-001", "type": "best-practice", "status": "active"},
        body="legacy body",
    )
    issues = lint_lib.validate_artifact_schema(bp, schema)
    assert not [issue for issue in issues if 'status' in issue["message"].lower()]
    assert practices.status_is_valid(schema, "active")
    assert not practices.status_is_valid(schema, "cancelled")


def test_artifact_lint_status_check_accepts_transition_only_active(tmp_path: Path):
    schema_dir = tmp_path / ".specflow/schema"
    schema_dir.mkdir(parents=True)
    (schema_dir / "best-practice.yaml").write_text(
        "type: best-practice\n"
        "allowed_status:\n"
        "  draft: []\n"
        "  approved: [draft, active]\n"
        "  superseded: [approved, active]\n",
        encoding="utf-8",
    )
    bp = art_lib.Artifact(
        path=tmp_path / "BP-001.md",
        frontmatter={"id": "BP-001", "type": "best-practice", "status": "active"},
        body="legacy body",
    )
    result = _check_status([bp], schema_dir)
    assert result["blocking_count"] == 0
