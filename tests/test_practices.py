"""Regression coverage for the five-section practice spine."""

from __future__ import annotations

import socket
from pathlib import Path

import yaml
from conftest import DOGFOOD_SEED_BP_IDS, shipped_dogfood_seed_bps

from specflow.commands import init as init_cmd
from specflow.commands import practices as practices_cmd
from specflow.commands import refresh as refresh_cmd
from specflow.commands.artifact_lint import _check_status
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
_DOGFOOD_BP_IDS = set(DOGFOOD_SEED_BP_IDS)


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


def _write_legacy_bp_schema(root: Path) -> Path:
    schema_path = root / ".specflow/schema/best-practice.yaml"
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(
        "type: best-practice\n"
        "allowed_status:\n"
        "  draft: []\n"
        "  approved: [draft]\n"
        "  active: [approved]\n"
        "  superseded: [active]\n"
        "custom_field: preserved\n",
        encoding="utf-8",
    )
    return schema_path


def _file_body_bytes(path: Path) -> bytes:
    return path.read_bytes().split(b"---", 2)[2]


def _shipped_dogfood_bps() -> list[art_lib.Artifact]:
    """The seed-generated dogfood BPs (BP-002..BP-007), hard-asserted present.

    Filtered to the known seed ids rather than globbed: learned practices such
    as BP-008 live beside them and must not turn these tests into skips.
    """
    practices = shipped_dogfood_seed_bps(Path(__file__).parents[1])
    assert {practice.id for practice in practices} == _DOGFOOD_BP_IDS
    return practices


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


def test_practices_validate_tolerates_synthesized_legacy_anatomy(tmp_path: Path, capsys):
    # DEC-089 legacy allowance: `practices migrate` stamps provenance but
    # deliberately restores the authored body (_restore_original_body), so a
    # migrated legacy BP can never reach the five-part anatomy retroactively.
    # Enforcement is the create/edit boundary; migrated records pass.
    _write_bp(
        tmp_path,
        "BP-001",
        provenance="synthesized",
        body="## Practice\n\nDo it.\n\n## Rationale\n\nBecause.\n\n"
             "## Verification\n\nCheck it.\n",
    )
    rc = practices_cmd.run(tmp_path, {"practices_subcommand": "validate"})
    output = capsys.readouterr().out
    assert rc == 0
    assert "PASS" in output
    assert "missing section" not in output


def test_practices_validate_still_enforces_anatomy_on_authored_provenance(
    tmp_path: Path, capsys,
):
    # The allowance is migration-only: bundled / standard / learned records
    # (and unstamped legacy records awaiting migrate) still fail.
    _write_bp(
        tmp_path,
        "BP-001",
        provenance="learned",
        body="## Practice\n\nDo it.\n\n## Rationale\n\nBecause.\n",
    )
    rc = practices_cmd.run(tmp_path, {"practices_subcommand": "validate"})
    output = capsys.readouterr().out
    assert rc == 1
    assert "BP-001.md: missing section 'Work products'" in output


def test_shipped_dogfood_bps_pass_practices_validate():
    root = Path(__file__).parents[1]
    shipped = _shipped_dogfood_bps()
    assert len(shipped) == len(_DOGFOOD_BP_IDS)
    assert practices.validate_practices(root) == []


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
    from specflow.lib.practices_seed import get_seed_practices

    seed_entry = next(
        practice for practice in get_seed_practices()
        if practice.title == "Separation of Concerns"
    )
    legacy_seed_body = seed_entry.to_body()
    _write_bp(
        tmp_path, "BP-001", title="Separation of Concerns", status="active",
        body=legacy_seed_body,
    )
    _write_bp(
        tmp_path, "BP-002", title="Hand-authored legacy", body="## Practice\n\nDo it.\n",
    )
    schema_path = _write_legacy_bp_schema(tmp_path)
    index_path = tmp_path / "_specflow/specs/best-practices/_index.yaml"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("artifacts: {}\nnext_id: 3\n", encoding="utf-8")
    hand_authored_path = tmp_path / "_specflow/specs/best-practices/BP-002.md"
    hand_authored_body = _file_body_bytes(hand_authored_path)
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    before_mtimes = {
        path: path.stat().st_mtime_ns for path in tmp_path.rglob("*") if path.is_file()
    }

    dry_rc = practices_cmd.run(
        tmp_path, {"practices_subcommand": "migrate", "dry_run": True},
    )
    dry_output = capsys.readouterr().out
    after_dry = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert dry_rc == 0
    assert "Would stamp provenance on 2" in dry_output
    assert "Would repair best-practice status map" in dry_output
    assert "source=SEED-GENERIC-01" in dry_output
    assert "Dry run complete; no files written." in dry_output
    assert before == after_dry
    assert before_mtimes == {
        path: path.stat().st_mtime_ns for path in tmp_path.rglob("*") if path.is_file()
    }
    assert index_path.read_bytes() == before[index_path]
    assert schema_path.read_bytes() == before[schema_path]

    first_rc = practices_cmd.run(tmp_path, {"practices_subcommand": "migrate"})
    first_output = capsys.readouterr().out
    assert first_rc == 0
    assert "legacy anatomy is incomplete; provenance stamped synthesized" in first_output
    assert "Repaired best-practice status map" in first_output
    seed = art_lib.parse_artifact(tmp_path / "_specflow/specs/best-practices/BP-001.md")
    hand_authored = art_lib.parse_artifact(tmp_path / "_specflow/specs/best-practices/BP-002.md")
    assert seed.frontmatter["provenance"] == "bundled"
    assert seed.frontmatter["source"] == "SEED-GENERIC-01"
    assert hand_authored.frontmatter["provenance"] == "synthesized"
    assert _file_body_bytes(hand_authored_path) == hand_authored_body
    assert yaml.safe_load(schema_path.read_text(encoding="utf-8"))["allowed_status"] == {
        "draft": [],
        "approved": ["draft", "active"],
        "superseded": ["approved", "active"],
    }

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
    assert "Repaired best-practice status map" not in second_output
    assert after_first == after_second


def test_migrate_does_not_call_a_seed_title_match_bundled_when_body_differs(
    tmp_path: Path, capsys,
):
    _write_bp(
        tmp_path,
        "BP-001",
        title="Separation of Concerns",
        body=practices.render_practice_body(
            "A hand-authored decomposition rule.",
            "For components with overlapping ownership.",
            "An ownership map.",
            "Review component responsibilities.",
            "Clear ownership reduces accidental coupling.",
        ),
    )

    rc = practices_cmd.run(tmp_path, {"practices_subcommand": "migrate"})
    output = capsys.readouterr().out
    migrated = art_lib.parse_artifact(
        tmp_path / "_specflow/specs/best-practices/BP-001.md"
    )

    assert rc == 0
    assert "title matches bundled seed 'SEED-GENERIC-01' but body differs" in output
    assert migrated.frontmatter["provenance"] == "synthesized"
    assert "source" not in migrated.frontmatter


def test_practices_validate_does_not_open_network_sockets(
    tmp_path: Path, monkeypatch, capsys,
):
    _write_bp(tmp_path, "BP-001", provenance="learned")

    def deny_network(*_args, **_kwargs):
        raise AssertionError("practices validate attempted network access")

    monkeypatch.setattr(socket, "socket", deny_network)
    monkeypatch.setattr(socket, "create_connection", deny_network)
    monkeypatch.setattr(socket, "getaddrinfo", deny_network)

    rc = practices_cmd.run(tmp_path, {"practices_subcommand": "validate"})

    assert rc == 0
    assert "Validated 1 best-practice artifact(s): PASS" in capsys.readouterr().out


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


def test_new_loader_matches_old_path_on_shipped_dogfood_bps():
    root = Path(__file__).parents[1]
    for bp in _shipped_dogfood_bps():
        target = art_lib.Artifact(
            path=root / "_specflow/specs/requirements/REQ-dogfood.md",
            frontmatter={
                "id": "REQ-DOGFOOD",
                "type": "requirement",
                "status": "approved",
                "tags": list(bp.tags),
            },
            body="",
        )
        old_ids = _old_loader(root, target)
        new_ids = [
            practice.id
            for practice in practices.load_active_best_practices(root, target)
        ]
        assert new_ids == old_ids


def test_applicability_precedence_with_shipped_dogfood_bp(tmp_path: Path):
    dogfood = _shipped_dogfood_bps()
    source_bp = dogfood[0]
    bp_dir = tmp_path / "_specflow/specs/best-practices"
    bp_dir.mkdir(parents=True)
    for bp in dogfood:
        frontmatter = dict(bp.frontmatter)
        if bp.id == source_bp.id:
            frontmatter["applicability"] = {"domains": ["embedded"]}
        target_path = bp_dir / f"{bp.id}.md"
        target_path.write_text(
            "---\n"
            + yaml.safe_dump(frontmatter, sort_keys=False)
            + "---\n\n"
            + bp.body
            + "\n",
            encoding="utf-8",
        )

    target = art_lib.Artifact(
        path=tmp_path / "STORY-001.md",
        frontmatter={
            "id": "STORY-001",
            "type": "story",
            "status": "approved",
            "domain": "web-app",
            "tags": list(source_bp.tags),
        },
        body="",
    )
    matched = practices.load_active_best_practices(tmp_path, target)
    assert source_bp.id not in {bp.id for bp in matched}

    target.frontmatter["domain"] = "embedded"
    matched = practices.load_active_best_practices(tmp_path, target)
    assert source_bp.id in {bp.id for bp in matched}


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


def test_normal_refresh_repairs_legacy_status_map_without_force(tmp_path: Path):
    schema_path = _write_legacy_bp_schema(tmp_path)
    _write_bp(tmp_path, "BP-001", title="Refresh migration")
    (tmp_path / "_specflow/specs/best-practices/_index.yaml").write_text(
        "artifacts: {}\nnext_id: 2\n", encoding="utf-8",
    )

    assert refresh_cmd.run(
        tmp_path, {"no_skills": True, "no_context": True},
    ) == 0
    repaired = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    assert repaired["allowed_status"] == {
        "draft": [],
        "approved": ["draft", "active"],
        "superseded": ["approved", "active"],
    }
    assert repaired["custom_field"] == "preserved"
    after_first = schema_path.read_bytes()

    assert refresh_cmd.run(
        tmp_path, {"no_skills": True, "no_context": True},
    ) == 0
    assert schema_path.read_bytes() == after_first


def test_init_path_stamps_preexisting_practices(tmp_path: Path):
    schema_path = _write_legacy_bp_schema(tmp_path)
    bp = _write_bp(tmp_path, "BP-001", title="Init migration")
    assert init_cmd.run(tmp_path, {"platform": "opencode", "no_ci": True}) == 0
    migrated = art_lib.parse_artifact(bp)
    assert migrated.frontmatter["provenance"] == "learned"
    assert yaml.safe_load(schema_path.read_text(encoding="utf-8"))["allowed_status"] == {
        "draft": [],
        "approved": ["draft", "active"],
        "superseded": ["approved", "active"],
    }


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
    schema_path = _write_legacy_bp_schema(tmp_path)
    first_bp = _write_bp(tmp_path, "BP-001", title="Pack apply migration")

    applied = scaffold_lib.apply_pack(tmp_path, "example", tmp_path / "packs")
    assert applied["ok"]
    assert art_lib.parse_artifact(first_bp).frontmatter["provenance"] == "learned"
    assert yaml.safe_load(schema_path.read_text(encoding="utf-8"))["allowed_status"] == {
        "draft": [],
        "approved": ["draft", "active"],
        "superseded": ["approved", "active"],
    }

    second_bp = _write_bp(tmp_path, "BP-002", title="Pack refresh migration")
    schema_path.write_text(
        "type: best-practice\n"
        "allowed_status:\n"
        "  draft: []\n"
        "  approved: [draft]\n"
        "  active: [approved]\n"
        "  superseded: [active]\n"
        "custom_field: preserved\n",
        encoding="utf-8",
    )
    refreshed = scaffold_lib.refresh_pack(
        tmp_path, "example", tmp_path / "packs", [], force=True,
    )
    assert refreshed["ok"]
    assert art_lib.parse_artifact(second_bp).frontmatter["provenance"] == "learned"
    assert yaml.safe_load(schema_path.read_text(encoding="utf-8"))["allowed_status"] == {
        "draft": [],
        "approved": ["draft", "active"],
        "superseded": ["approved", "active"],
    }
