"""Negative artifact-lint fixtures (STORY-736 / REQ-065).

Adapted from poteto/pstack-claude, MIT (tests/invariants.test.mjs):
A check that quietly matches nothing looks identical to a pass. Every rule id gets a fixture that must trip it.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest
import yaml

from conftest import write_artifact
from test_artifact_lint import project_root  # noqa: F401 — reuse scaffold fixture

from specflow.commands import artifact_lint as lint_cmd
from specflow.core.findings import Finding


def _enumerate_rule_ids() -> list[str]:
    """Read distinct literal rule ids directly from lint's _emit calls."""
    source = (
        Path(__file__).resolve().parents[1]
        / "src/specflow/commands/artifact_lint.py"
    )
    tree = ast.parse(source.read_text(encoding="utf-8"))
    return sorted({
        node.args[1].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_emit"
        and len(node.args) >= 2
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "findings"
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
    })


def collect_findings(root: Path) -> list[Finding]:
    """Use run()'s collection path, before rendering and baseline policy."""
    _, findings = lint_cmd.collect(
        root.resolve(), lint_cmd.CHECK_NAMES, as_of=date(2026, 10, 17)
    )
    return findings


def _patch_schema(root: Path, art_type: str, **updates: object) -> None:
    """Merge keys into one temporary schema file. Leaves ``type`` intact."""
    path = root / ".specflow" / "schema" / f"{art_type}.yaml"
    schema = yaml.safe_load(path.read_text(encoding="utf-8"))
    schema.update(updates)
    path.write_text(yaml.dump(schema), encoding="utf-8")


def _hand_write(
    root: Path,
    rel: str,
    artifact_id: str,
    art_type: str,
    *,
    status: str = "draft",
    links: list[dict] | None = None,
    filename: str | None = None,
) -> None:
    """Write an intentionally invalid fixture the production writer would refuse."""
    fm: dict = {
        "id": artifact_id,
        "title": f"Test {artifact_id}",
        "type": art_type,
        "status": status,
        "tags": [],
        "suspect": False,
        "links": links or [],
    }
    target = root / "_specflow" / rel
    target.mkdir(parents=True, exist_ok=True)
    body = yaml.dump(fm, default_flow_style=False, sort_keys=False)
    (target / (filename or f"{artifact_id}.md")).write_text(
        f"---\n{body}---\n\n# Test {artifact_id}\n\nbody\n",
        encoding="utf-8",
    )


def _build_schema_schema_error(root: Path) -> None:
    # A top-level list is not a mapping, so registration records the file.
    (root / ".specflow" / "schema" / "broken-pack.yaml").write_text(
        "- a\n- b\n", encoding="utf-8"
    )


def _build_schema_unknown_type(root: Path) -> None:
    # Discoverable via a registered directory; no schema for this type.
    _hand_write(root, "specs/requirements", "FOO-001", "unknown-type")


def _build_schema_field(root: Path) -> None:
    _patch_schema(root, "requirement", required_fields=["status", "title", "priority"])
    _hand_write(root, "specs/requirements", "REQ-001", "requirement")


def _build_schema_link_role(root: Path) -> None:
    _patch_schema(root, "story", allowed_link_roles=["implements", "specified_by"])
    _hand_write(
        root,
        "work/stories",
        "STORY-001",
        "story",
        links=[{"target": "REQ-001", "role": "totally_bogus"}],
    )


def _build_ids_format(root: Path) -> None:
    _patch_schema(root, "requirement", id_format=r"^REQ-[0-9]{3}$")
    _hand_write(
        root, "specs/requirements", "REQ-bad", "requirement", filename="bad.md"
    )


def _build_ids_depth(root: Path) -> None:
    _hand_write(root, "specs/requirements", "REQ-001.1.1.1", "requirement")


def _build_ids_duplicate(root: Path) -> None:
    _hand_write(
        root, "specs/requirements", "REQ-001", "requirement", filename="a.md"
    )
    _hand_write(
        root, "specs/requirements", "REQ-001", "requirement", filename="b.md"
    )


def _build_status_invalid(root: Path) -> None:
    _hand_write(root, "specs/requirements", "REQ-001", "requirement", status="foobar")


def _build_role_target_type(root: Path) -> None:
    # UT prefix resolves to unit-test, which ``implements`` does not allow.
    _hand_write(
        root,
        "work/stories",
        "STORY-001",
        "story",
        links=[{"target": "UT-001", "role": "implements"}],
    )


def _build_story_size_no_ac(root: Path) -> None:
    write_artifact(root, "STORY-001", "story", "Missing AC section", body="no section")


def _build_story_size_ac_min(root: Path) -> None:
    write_artifact(
        root, "STORY-001", "story", "Too few criteria",
        body="## Acceptance Criteria\n- first\n",
    )


def _build_story_size_ac_max(root: Path) -> None:
    write_artifact(
        root, "STORY-001", "story", "Too many criteria",
        body="## Acceptance Criteria\n" + "\n".join(
            f"{i}. criterion {i}" for i in range(1, 10)
        ),
    )


def _build_story_size_subsystems(root: Path) -> None:
    # Paths are textual references; no source files are needed.
    write_artifact(
        root, "STORY-001", "story", "Too many subsystems",
        body=(
            "## Acceptance Criteria\n- first\n- second\n\n"
            "## Notes\nsrc/a src/b src/c src/d src/e src/f\n"
        ),
    )


def _build_story_linkage_draft(root: Path) -> None:
    write_artifact(root, "STORY-001", "story", "Draft without spec link")


def _build_story_linkage_beyond_draft(root: Path) -> None:
    write_artifact(
        root, "STORY-001", "story", "Approved without spec link", status="approved",
    )


def _build_acceptance_missing(root: Path) -> None:
    write_artifact(
        root, "REQ-001", "requirement", "Basic behavior",
        body="The system shall work.",
    )


def _build_acceptance_empty(root: Path) -> None:
    write_artifact(
        root, "REQ-001", "requirement", "Empty acceptance criteria",
        body="## Acceptance Criteria\n\n## Notes\n",
    )


def _build_acceptance_nfr_threshold(root: Path) -> None:
    # The list number is stripped before checking for a numeric threshold.
    write_artifact(
        root, "REQ-001", "requirement", "Unmeasurable performance",
        body="## Acceptance Criteria\n1. respond quickly\n",
        extra_fm={"non_functional_category": "performance"},
    )


def _build_coverage_no_arch(root: Path) -> None:
    # Approved REQ with neither a refined_by ARCH nor any ARCH derives_from it.
    write_artifact(
        root, "REQ-001", "requirement", "Unrefined feature", status="approved",
    )


def _build_coverage_no_story(root: Path) -> None:
    # ARCH refines the REQ (legacy shape, so no-arch stays quiet) but no
    # STORY implements/derives_from it.
    write_artifact(
        root, "REQ-001", "requirement", "Unimplemented feature",
        status="approved",
    )
    write_artifact(
        root, "ARCH-001", "architecture", "Refining architecture",
        links=[{"target": "REQ-001", "role": "derives_from"}],
    )


def _build_coverage_no_test(root: Path) -> None:
    # Approved REQ implemented by an approved STORY with no UT/IT/QT linked
    # via verified_by in either direction.
    write_artifact(
        root, "REQ-001", "requirement", "Covered feature", status="approved",
    )
    write_artifact(
        root, "STORY-001", "story", "Implement the feature", status="approved",
        links=[{"target": "REQ-001", "role": "implements"}],
    )


def _build_links_broken(root: Path) -> None:
    # Dangling target the discovery index never sees — intentionally invalid,
    # so the fixture is hand-written rather than writer-scaffolded.
    _hand_write(
        root,
        "work/stories",
        "STORY-001",
        "story",
        links=[{"target": "REQ-999", "role": "implements"}],
    )


def _build_links_orphan(root: Path) -> None:
    # No outgoing links, nothing inbound, non-SPIKE prefix.
    write_artifact(root, "REQ-001", "requirement", "Orphan requirement")


def _build_links_missing_v_pair(root: Path) -> None:
    # Approved REQ (past draft, not terminal) with no QT verified_by edge in
    # either direction.
    write_artifact(
        root, "REQ-001", "requirement", "Unverified requirement",
        status="approved",
    )


def _build_backfilled_links_unlinked(root: Path) -> None:
    # Backfilled tag with zero links in either direction — adoption noise.
    write_artifact(
        root, "REQ-001", "requirement", "Backfilled nothing",
        tags=["backfilled"],
    )


def _build_conflicts_numeric(root: Path) -> None:
    # Identical titles and tags → same element key; same metric and unit with
    # the upper bound strictly below the lower bound.
    write_artifact(
        root, "REQ-001", "requirement", "Latency", body="latency < 10 ms",
    )
    write_artifact(
        root, "REQ-002", "requirement", "Latency", body="latency > 20 ms",
    )


def _build_quality_text(root: Path) -> None:
    write_artifact(
        root, "REQ-001", "requirement", "Ambiguous behavior",
        body="The system **shall** be fast and user-friendly.",
    )


def _build_spec_body_word_count(root: Path) -> None:
    write_artifact(
        root, "ARCH-001", "architecture", "Brief architecture",
        body="## Components\nThis is too short.",
    )


def _build_spec_body_headers(root: Path) -> None:
    # Exceed the word-count minimum without any structural headings.
    write_artifact(
        root, "ARCH-001", "architecture", "Unstructured architecture",
        body=" ".join(["The component receives input and returns validated output."] * 8),
    )


def _build_nfr_category_vocabulary(root: Path) -> None:
    write_artifact(
        root, "REQ-001", "requirement", "Misspelled category",
        extra_fm={"non_functional_category": "perfomance"},
    )


def _build_dead_oracle_missing_path(root: Path) -> None:
    # Slash paths are checked only when their first directory exists.
    (root / "tests").mkdir()
    write_artifact(
        root, "QT-001", "qualification-test", "Missing test oracle",
        extra_fm={"verify_command": "uv run pytest tests/test_missing_oracle.py -q"},
    )


def _build_output_files_missing(root: Path) -> None:
    write_artifact(
        root, "ARCH-001", "architecture", "Missing implementation output",
        extra_fm={"output_files": ["src/nonexistent.py"]},
    )


def _build_output_files_glob_empty(root: Path) -> None:
    write_artifact(
        root, "ARCH-001", "architecture", "Unmatched output pattern",
        extra_fm={"output_files": ["output/YY_MM_DD_*.json"]},
    )


def _build_dec_risk_profile_missing(root: Path) -> None:
    write_artifact(
        root, "DEC-001", "decision", "Approved without risk profile",
        status="approved",
    )


def _build_spidr_coverage_dimension(root: Path) -> None:
    # Five stories enable findings; only the path dimension is represented.
    for index in range(1, 6):
        write_artifact(
            root, f"STORY-{index:03}", "story", f"Feature {index}",
            tags=["spidr-path"] if index == 1 else ["feature"],
        )


def _build_status_cascade_draft_spec(root: Path) -> None:
    # Implemented STORY linked to a discoverable draft REQ. Role is ignored.
    write_artifact(root, "REQ-001", "requirement", "Draft spec", status="draft")
    write_artifact(
        root, "STORY-001", "story", "Implemented against draft",
        status="implemented",
        links=[{"target": "REQ-001", "role": "implements"}],
    )


def _build_status_cascade_lagging(root: Path) -> None:
    # Verified STORY so include_req is on; derives_from an approved REQ.
    write_artifact(
        root, "REQ-001", "requirement", "Approved spec", status="approved",
    )
    write_artifact(
        root, "STORY-001", "story", "Verified story", status="verified",
        links=[{"target": "REQ-001", "role": "derives_from"}],
    )


def _build_status_hierarchy(root: Path) -> None:
    # Same base id: verified root, non-terminal draft child.
    write_artifact(
        root, "REQ-001", "requirement", "Verified parent", status="verified",
    )
    write_artifact(
        root, "REQ-001.1", "requirement", "Draft child", status="draft",
    )


def _build_spike_lifecycle_stale(root: Path) -> None:
    # collect_findings fixes as-of at 2026-10-17. The writer stamps created
    # today, then extra frontmatter overwrites it; rewrite again so a later
    # stamp order cannot hide the age. 120 days > timebox 30.
    path = write_artifact(
        root, "SPIKE-100", "spike", "Aged research", status="draft",
        extra_fm={"created": "2026-06-19", "timebox": 30},
    )
    text = path.read_text(encoding="utf-8")
    stamped = yaml.safe_load(text.split("---", 2)[1])
    stamped["created"] = "2026-06-19"
    stamped["timebox"] = 30
    body = text.split("---", 2)[2]
    path.write_text(
        "---\n" + yaml.dump(stamped, default_flow_style=False, sort_keys=False) + "---" + body,
        encoding="utf-8",
    )


def _build_spike_lifecycle_zombie(root: Path) -> None:
    # The fixture schema has no completed status; the shipped spike schema does.
    schema_path = root / ".specflow" / "schema" / "spike.yaml"
    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    allowed = dict(schema.get("allowed_status") or {})
    allowed["completed"] = ["approved"]
    schema["allowed_status"] = allowed
    schema_path.write_text(yaml.dump(schema), encoding="utf-8")
    write_artifact(
        root, "SPIKE-200", "spike", "Unconsumed findings", status="completed",
        body=" ".join(["finding"] * 120),
    )


def _build_wave_cycles_cycle(root: Path) -> None:
    # Mutual depends_on between two existing stories. specified_by is not a cycle.
    write_artifact(
        root, "STORY-001", "story", "Cycle A",
        links=[{"target": "STORY-002", "role": "depends_on"}],
    )
    write_artifact(
        root, "STORY-002", "story", "Cycle B",
        links=[{"target": "STORY-001", "role": "depends_on"}],
    )


def _build_wave_cycles_fan_in(root: Path) -> None:
    # Draft story; four STORY-prefix deps. Targets need not exist.
    write_artifact(
        root, "STORY-005", "story", "Too many dependencies",
        links=[
            {"target": f"STORY-{index:03}", "role": "depends_on"}
            for index in range(1, 5)
        ],
    )


def _build_fingerprints_stale(root: Path) -> None:
    path = write_artifact(
        root, "REQ-001", "requirement", "Body changed after fingerprinting",
        body="Original requirement body.",
    )
    # Keep the writer's non-empty fingerprint, then invalidate it with a body edit.
    with path.open("a", encoding="utf-8") as stream:
        stream.write("\nChanged requirement body.\n")


def _build_source_drift_changed(root: Path) -> None:
    from specflow.lib import source_drift

    target = root / "src" / "module.py"
    target.parent.mkdir(parents=True)
    target.write_text("# initial\n", encoding="utf-8")
    write_artifact(
        root, "REQ-501", "requirement", "Changed source output",
        extra_fm={"output_files": ["src/module.py"]},
    )
    source_drift.seed(root)
    target.write_text("# changed content\n", encoding="utf-8")


def _register_autoresearch_schemas(root: Path) -> None:
    # Pack types must be registered for both the writer and discovery harness.
    schemas = (
        Path(__file__).resolve().parents[1]
        / "src/specflow/packs/autoresearch/schemas"
    )
    for source in sorted(schemas.glob("*.yaml")):
        (root / ".specflow" / "schema" / source.name).write_bytes(source.read_bytes())


def _build_fingerprint_drift_evaluator(root: Path) -> None:
    _register_autoresearch_schemas(root)
    write_artifact(
        root, "COMP-001", "competition", "Frozen evaluator", status="active",
        extra_fm={
            "verify_command": "python scripts/eval.py",
            "metric_name": "score",
            "metric_direction": "higher_is_better",
            "evaluator_fingerprint": "sha256:original",
        },
    )
    write_artifact(
        root, "EXPT-001", "experiment", "Changed evaluator", status="kept",
        extra_fm={
            "competition": "COMP-001",
            "evaluator_fingerprint": "sha256:changed",
        },
    )


def _build_autoresearch_comp_closure_no_confirmed_find(root: Path) -> None:
    _register_autoresearch_schemas(root)
    write_artifact(
        root, "COMP-001", "competition", "Closed without findings",
        status="completed",
        extra_fm={
            "verify_command": "python scripts/eval.py",
            "metric_name": "score",
            "metric_direction": "higher_is_better",
        },
    )


def _build_autoresearch_comp_closure_no_disposition(root: Path) -> None:
    _build_autoresearch_comp_closure_no_confirmed_find(root)
    write_artifact(
        root, "FIND-001", "finding", "Confirmed competition finding",
        status="confirmed", extra_fm={"competition": "COMP-001"},
    )


def _build_thinking_techniques_unchallenged(root: Path) -> None:
    # Approved requirement with no thinking_techniques list.
    write_artifact(
        root, "REQ-001", "requirement", "Unchallenged requirement",
        status="approved",
    )


# Registry extension convention (STORY-736):
# - Name builders _build_<rule_id_with_slashes_and_hyphens_as_underscores>.
# - Signature: builder(root: Path) -> None; mutate only the temporary project.
# - Put builders and reusable setup helpers above this registry. Use the shared
#   write_artifact helper for valid artifacts; hand-write intentionally invalid
#   fixture files only inside the temporary tree.
# - Set required schema/config/state/pack inputs inside the builder. All checks
#   are enabled by collect_findings (no --type or --fix flag); as-of is fixed there,
#   so date-sensitive builders must arrange dates relative to 2026-10-17.
# - Register the exact emitted rule id. Other findings may coexist, but the test
#   must observe this exact id through the single shared collection harness.
FIXTURES: dict[str, Callable[[Path], None]] = {
    "fingerprints/stale": _build_fingerprints_stale,
    "source-drift/changed": _build_source_drift_changed,
    "fingerprint-drift/evaluator": _build_fingerprint_drift_evaluator,
    "autoresearch-comp-closure/no-confirmed-find": _build_autoresearch_comp_closure_no_confirmed_find,
    "autoresearch-comp-closure/no-disposition": _build_autoresearch_comp_closure_no_disposition,
    "schema/schema-error": _build_schema_schema_error,
    "schema/unknown-type": _build_schema_unknown_type,
    "schema/field": _build_schema_field,
    "schema/link-role": _build_schema_link_role,
    "ids/format": _build_ids_format,
    "ids/depth": _build_ids_depth,
    "ids/duplicate": _build_ids_duplicate,
    "status/invalid": _build_status_invalid,
    "role-target/type": _build_role_target_type,
    "story-size/no-ac": _build_story_size_no_ac,
    "story-size/ac-min": _build_story_size_ac_min,
    "story-size/ac-max": _build_story_size_ac_max,
    "story-size/subsystems": _build_story_size_subsystems,
    "story-linkage/draft": _build_story_linkage_draft,
    "story-linkage/beyond-draft": _build_story_linkage_beyond_draft,
    "acceptance/missing": _build_acceptance_missing,
    "acceptance/empty": _build_acceptance_empty,
    "acceptance/nfr-threshold": _build_acceptance_nfr_threshold,
    "coverage/no-arch": _build_coverage_no_arch,
    "coverage/no-story": _build_coverage_no_story,
    "coverage/no-test": _build_coverage_no_test,
    "links/broken": _build_links_broken,
    "links/orphan": _build_links_orphan,
    "links/missing-v-pair": _build_links_missing_v_pair,
    "backfilled-links/unlinked": _build_backfilled_links_unlinked,
    "conflicts/numeric": _build_conflicts_numeric,
    "quality/text": _build_quality_text,
    "spec-body/word-count": _build_spec_body_word_count,
    "spec-body/headers": _build_spec_body_headers,
    "nfr-category/vocabulary": _build_nfr_category_vocabulary,
    "dead-oracle/missing-path": _build_dead_oracle_missing_path,
    "output-files/missing": _build_output_files_missing,
    "output-files/glob-empty": _build_output_files_glob_empty,
    "dec-risk-profile/missing": _build_dec_risk_profile_missing,
    "spidr-coverage/dimension": _build_spidr_coverage_dimension,
    "status-cascade/draft-spec": _build_status_cascade_draft_spec,
    "status-cascade/lagging": _build_status_cascade_lagging,
    "status/hierarchy": _build_status_hierarchy,
    "spike-lifecycle/stale": _build_spike_lifecycle_stale,
    "spike-lifecycle/zombie": _build_spike_lifecycle_zombie,
    "wave-cycles/cycle": _build_wave_cycles_cycle,
    "wave-cycles/fan-in": _build_wave_cycles_fan_in,
    "thinking-techniques/unchallenged": _build_thinking_techniques_unchallenged,
}


def test_every_rule_id_has_a_fixture():
    expected = set(_enumerate_rule_ids())
    registered = set(FIXTURES)
    missing = sorted(expected - registered)
    stale = sorted(registered - expected)
    assert expected == registered, (
        f"Missing fixture ids ({len(missing)}): {', '.join(missing)}\n"
        f"Stale fixture ids ({len(stale)}): {', '.join(stale)}"
    )


@pytest.mark.parametrize(
    "rule_id,builder",
    [
        pytest.param(rule_id, builder, id=rule_id.replace("/", "-"))
        for rule_id, builder in sorted(FIXTURES.items())
    ],
)
def test_fixture_trips_its_rule(
    project_root: Path, rule_id: str, builder: Callable[[Path], None]
):
    builder(project_root)
    observed = {finding.rule_id for finding in collect_findings(project_root)}
    assert rule_id in observed, (
        f"Fixture did not trip {rule_id}; observed ids: {', '.join(sorted(observed))}"
    )
