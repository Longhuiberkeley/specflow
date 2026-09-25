"""Regression coverage for the five-section practice spine."""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.commands.artifact_lint import _check_status
from specflow.commands import practices as practices_cmd
from specflow.commands import init as init_cmd
from specflow.commands import refresh as refresh_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import lint as lint_lib
from specflow.lib import practices
from specflow.lib import scaffold as scaffold_lib


_STATUS_MAP_BYTES = (
    b"allowed_status:\n"
    b"  draft: []\n"
    b"  approved: [draft, active]\n"
    b"  superseded: [approved, active]\n"
)


def _write_bp(
    root: Path,
    artifact_id: str,
    *,
    title: str | None = None,
    status: str = "approved",
    body: str | None = None,
    **fields,
) -> Path:
    bp_dir = root / "_specflow/specs/best-practices"
    bp_dir.mkdir(parents=True, exist_ok=True)
    path = bp_dir / f"{artifact_id}.md"
    frontmatter = {
        "id": artifact_id,
        "title": title or artifact_id,
        "type": "best-practice",
        "status": status,
        "created": "2026-01-01",
        **fields,
    }
    content = body if body is not None else practices.render_practice_body(
        "Do the practice.", "For relevant work.", "A decision record.",
        "Inspect the record.", "It avoids ambiguity.",
    )
    path.write_text(
        "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---\n\n" + content + "\n",
        encoding="utf-8",
    )
    return path


def _old_loader(root: Path, artifact: art_lib.Artifact) -> list[str]:
    """The pre-rewrite applies_to-or-tag matcher, for fixture equivalence."""
    result = []
    for bp_file in sorted((root / "_specflow/specs/best-practices").glob("*.md")):
        bp = art_lib.parse_artifact(bp_file)
        if not bp or bp.status not in ("active", "approved"):
            continue
        applies_to = {link.target for link in bp.links if link.role == "applies_to"}
        if artifact.id in applies_to or set(artifact.tags) & set(bp.tags):
            result.append(bp.id)
    return result


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
    start = schema.index(b"allowed_status:\n")
    end = schema.index(b"allowed_link_roles:", start)
    assert schema[start:end] == _STATUS_MAP_BYTES


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


def test_legacy_active_bp_keeps_both_transitional_edges_reachable(tmp_path: Path):
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
    for artifact_id in ("BP-001", "BP-002"):
        _write_bp(tmp_path, artifact_id, status="active")

    approved = art_lib.update_artifact(tmp_path, "BP-001", status="approved")
    superseded = art_lib.update_artifact(tmp_path, "BP-002", status="superseded")
    assert approved["ok"] and superseded["ok"]

    blocked_schema = {
        "type": "best-practice",
        "allowed_status": {
            "draft": [], "approved": ["draft"], "superseded": ["approved"],
        },
    }
    assert not practices.status_is_valid(blocked_schema, "active")


def test_practices_validate_reports_malformed_artifacts_deterministically(
    tmp_path: Path, capsys,
):
    _write_bp(
        tmp_path,
        "BP-001",
        body="## Practice\n\nDo it.\n\n## Applies when\n\nAlways.\n\n"
        "## Work products\n\nA record.\n\n## Verification\n\nCheck it.\n",
    )
    _write_bp(tmp_path, "BP-002", verification_method="telepathy")
    _write_bp(
        tmp_path, "BP-003", provenance="standard", source="ISO9999-9.9",
    )
    _write_bp(tmp_path, "BP-004", status="superseded")

    first_rc = practices_cmd.run(tmp_path, {"practices_subcommand": "validate"})
    first_output = capsys.readouterr().out
    second_rc = practices_cmd.run(tmp_path, {"practices_subcommand": "validate"})
    second_output = capsys.readouterr().out

    assert first_rc == second_rc == 1
    assert first_output == second_output
    assert "BP-001.md: missing section 'Rationale'" in first_output
    assert "BP-002.md: verification_method 'telepathy'" in first_output
    assert "BP-003.md: source 'ISO9999-9.9' does not resolve locally" in first_output
    assert "BP-004.md: superseded best-practice has no successor lineage" in first_output


def test_practices_validate_accepts_resolvable_complete_artifact(tmp_path: Path, capsys):
    _write_bp(
        tmp_path, "BP-001", provenance="bundled", source="SEED-GENERIC-01",
        verification_method="inspection", strength="recommended",
    )
    rc = practices_cmd.run(tmp_path, {"practices_subcommand": "validate"})
    output = capsys.readouterr().out
    assert rc == 0
    assert "Validated 1 best-practice artifact(s): PASS" in output


def test_practices_migrate_is_idempotent_and_dry_run_is_write_free(
    tmp_path: Path, capsys,
):
    legacy_seed_body = (
        "## Practice\n\nUse the practice.\n\n"
        "## Rationale\n\nIt helps.\n\n## Verification\n\nCheck it.\n"
    )
    _write_bp(
        tmp_path, "BP-001", title="Separation of Concerns", status="active",
        body=legacy_seed_body,
    )
    _write_bp(
        tmp_path, "BP-002", title="Hand-authored legacy", body="## Practice\n\nDo it.\n",
    )
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    dry_rc = practices_cmd.run(
        tmp_path, {"practices_subcommand": "migrate", "dry_run": True},
    )
    dry_output = capsys.readouterr().out
    after_dry = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert dry_rc == 0
    assert "Would stamp provenance on 2" in dry_output
    assert "source=SEED-GENERIC-01" in dry_output
    assert "Dry run complete; no files written." in dry_output
    assert before == after_dry

    first_rc = practices_cmd.run(tmp_path, {"practices_subcommand": "migrate"})
    first_output = capsys.readouterr().out
    assert first_rc == 0
    assert "legacy anatomy is incomplete; provenance stamped synthesized" in first_output
    seed = art_lib.parse_artifact(tmp_path / "_specflow/specs/best-practices/BP-001.md")
    hand_authored = art_lib.parse_artifact(tmp_path / "_specflow/specs/best-practices/BP-002.md")
    assert seed.frontmatter["provenance"] == "bundled"
    assert seed.frontmatter["source"] == "SEED-GENERIC-01"
    assert hand_authored.frontmatter["provenance"] == "synthesized"

    after_first = {
        path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()
    }
    second_rc = practices_cmd.run(tmp_path, {"practices_subcommand": "migrate"})
    second_output = capsys.readouterr().out
    after_second = {
        path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()
    }
    assert second_rc == 0
    assert "Stamped provenance on 0" in second_output
    assert after_first == after_second


def test_new_loader_matches_old_tag_and_link_path_for_legacy_bps(tmp_path: Path):
    _write_bp(tmp_path, "BP-001", status="approved", tags=["architecture"])
    _write_bp(tmp_path, "BP-002", status="active", tags=["architecture"])
    _write_bp(tmp_path, "BP-003", status="draft", tags=["architecture"])
    _write_bp(tmp_path, "BP-004", status="superseded", tags=["architecture"])
    _write_bp(
        tmp_path, "BP-005", status="approved",
        links=[{"target": "STORY-001", "role": "applies_to"}],
    )
    _write_bp(tmp_path, "BP-006", status="approved", tags=["unrelated"])
    target = art_lib.Artifact(
        path=tmp_path / "STORY-001.md",
        frontmatter={
            "id": "STORY-001", "type": "story", "status": "approved",
            "tags": ["architecture"],
        },
        body="",
    )

    old_ids = _old_loader(tmp_path, target)
    new_ids = [bp.id for bp in practices.load_active_best_practices(tmp_path, target)]
    assert old_ids == new_ids == ["BP-001", "BP-002", "BP-005"]


def test_applicability_predicate_is_authoritative_before_tag_fallback(tmp_path: Path):
    _write_bp(
        tmp_path, "BP-001", tags=["architecture"],
        applicability={"domains": ["embedded"]},
    )
    _write_bp(
        tmp_path, "BP-002", tags=[],
        applicability={"artifact_types": ["story"]},
    )
    _write_bp(
        tmp_path, "BP-003", tags=[],
        applicability={"domains": ["web-app"], "moments": ["execution"]},
    )
    target = art_lib.Artifact(
        path=tmp_path / "STORY-001.md",
        frontmatter={
            "id": "STORY-001", "type": "story", "status": "approved",
            "domain": "web-app", "phase": "execution", "tags": ["architecture"],
        },
        body="",
    )

    matched = practices.load_active_best_practices(tmp_path, target)
    assert [bp.id for bp in matched] == ["BP-002", "BP-003"]


def test_practices_cli_registers_seed_validate_and_migrate():
    from specflow.cli import build_parser

    parser = build_parser()
    seed_args = parser.parse_args(["practices", "seed", "--create"])
    validate_args = parser.parse_args(["practices", "validate"])
    migrate_args = parser.parse_args(["practices", "migrate", "--dry-run"])
    assert seed_args.command == "practices" and seed_args.create
    assert validate_args.practices_subcommand == "validate"
    assert migrate_args.practices_subcommand == "migrate" and migrate_args.dry_run


def test_schema_refresh_stamps_legacy_practice_provenance(tmp_path: Path):
    (tmp_path / ".specflow/schema").mkdir(parents=True)
    bp = _write_bp(tmp_path, "BP-001", title="Refresh migration")
    summary = refresh_cmd._refresh_shared(
        tmp_path,
        Path(__file__).parents[1] / "src/specflow/templates",
        dry_run=False,
        do_schemas=True,
        do_checklists=False,
        force_schemas=False,
    )
    assert any(label == "practices" for label, _ in summary)
    migrated = art_lib.parse_artifact(bp)
    assert migrated.frontmatter["provenance"] == "learned"


def test_init_path_stamps_preexisting_practices(tmp_path: Path):
    bp = _write_bp(tmp_path, "BP-001", title="Init migration")
    assert init_cmd.run(tmp_path, {"platform": "opencode", "no_ci": True}) == 0
    migrated = art_lib.parse_artifact(bp)
    assert migrated.frontmatter["provenance"] == "learned"


def test_apply_pack_and_refresh_pack_stamp_provenance(tmp_path: Path):
    pack_root = tmp_path / "packs/example"
    (pack_root / "schemas").mkdir(parents=True)
    (pack_root / "schemas/example.yaml").write_text(
        "type: example\nprefix: EXAMPLE\ndirectory: _specflow/specs/examples/\n",
        encoding="utf-8",
    )
    (pack_root / "pack.yaml").write_text(
        "name: example\nadds_directories: []\nadds_artifact_types: []\n",
        encoding="utf-8",
    )
    (tmp_path / ".specflow/schema").mkdir(parents=True)
    first_bp = _write_bp(tmp_path, "BP-001", title="Pack apply migration")

    applied = scaffold_lib.apply_pack(tmp_path, "example", tmp_path / "packs")
    assert applied["ok"]
    assert art_lib.parse_artifact(first_bp).frontmatter["provenance"] == "learned"

    second_bp = _write_bp(tmp_path, "BP-002", title="Pack refresh migration")
    refreshed = scaffold_lib.refresh_pack(
        tmp_path, "example", tmp_path / "packs", [], force=True,
    )
    assert refreshed["ok"]
    assert art_lib.parse_artifact(second_bp).frontmatter["provenance"] == "learned"
