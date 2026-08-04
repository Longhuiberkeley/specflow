"""STORY-ADDAUXIL-c7bd: optional ``auxiliary_metrics`` field on the EXPT schema.

Dedicated coverage of the story's three binding acceptance criteria:

  AC1 — EXPT schema YAML accepts an optional ``auxiliary_metrics`` field
        (freeform YAML dict), and the expected shape is documented.
  AC2 — EXPT artifacts carrying ``auxiliary_metrics`` pass ``specflow
        artifact-lint`` without warnings (the field is a recognized optional
        field, never flagged "Unknown field").
  AC3 — creation and round-trip of EXPT artifacts with ``auxiliary_metrics``
        populated: field absent (still valid), field present (valid +
        round-trips through read), field malformed (behavior documented).

The field itself has shipped in the schema since v1.6.0; these tests formally
close the story by exercising the full lint path and the on-disk round-trip
that the prior in-memory ``_check_status``-only test did not cover.
"""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.commands import artifact_lint
from specflow.lib import artifacts as art_lib
from specflow.lib import lint as lint_lib

PACKS_DIR = Path(__file__).parent.parent / "src" / "specflow" / "packs"
EXPT_SCHEMA_SRC = PACKS_DIR / "autoresearch" / "schemas" / "experiment.yaml"

# Required EXPT frontmatter per the shipped schema (experiment.yaml). A complete
# record keeps the schema check focused on auxiliary_metrics instead of tripping
# "Missing required field" blockers.
_REQUIRED_EXPT_FM = {
    "id": "EXPT-001",
    "title": "Auxiliary-metrics EXPT",
    "type": "experiment",
    "status": "kept",
    "created": "2026-08-04",
    "loop": "LOOP-001",
    "metric_value": 1.23,
    "change_category": "features",
    "summary": "EXPT exercising the auxiliary_metrics field",
}


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Temp project with the autoresearch EXPT schema installed.

    Minimal scaffold: only the experiment schema is registered, so lint runs
    against exactly the type under test. Module-level type dicts are cleaned up
    on teardown so the registration does not leak into sibling test modules.
    """
    root = tmp_path / "project"
    root.mkdir()
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True)
    (root / ".specflow" / "standards").mkdir(parents=True)

    (schema_dir / "experiment.yaml").write_text(
        EXPT_SCHEMA_SRC.read_text(encoding="utf-8"), encoding="utf-8"
    )

    config = {
        "project": {"name": "aux-metrics-test", "created": "2026-08-04"},
        "artifact_types": ["experiment"],
        "active_packs": ["autoresearch"],
    }
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump(config), encoding="utf-8"
    )
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "idle", "history": []}), encoding="utf-8"
    )

    (root / "_specflow" / "specs" / "experiments").mkdir(parents=True)

    art_lib._load_active_packs(root)
    yield root

    # Teardown: unregister the experiment type so other tests start clean.
    art_lib.TYPE_TO_DIR.pop("experiment", None)
    art_lib.TYPE_TO_PREFIX.pop("experiment", None)
    art_lib.PREFIX_TO_TYPE.pop("EXPT", None)


def _make_expt(
    extra_fm: dict | None = None,
    art_id: str = "EXPT-001",
    status: str = "kept",
    body: str = "Experiment body.",
) -> art_lib.Artifact:
    """Build an in-memory EXPT artifact with all required fields populated."""
    fm = dict(_REQUIRED_EXPT_FM)
    fm["id"] = art_id
    fm["status"] = status
    if extra_fm:
        fm.update(extra_fm)
    return art_lib.Artifact(
        path=Path(f"{art_id}.md"),
        frontmatter=fm,
        body=body,
        links=[],
    )


def _write_expt(
    root: Path,
    art_id: str = "EXPT-001",
    extra_fm: dict | None = None,
    body: str = "Experiment body.",
) -> Path:
    """Write an EXPT markdown file under _specflow/specs/experiments/."""
    fm = dict(_REQUIRED_EXPT_FM)
    fm["id"] = art_id
    if extra_fm:
        fm.update(extra_fm)
    fm_yaml = yaml.dump(fm, default_flow_style=False, sort_keys=False)
    rel_dir = art_lib.TYPE_TO_DIR.get("experiment", "specs/experiments")
    target_dir = root / "_specflow" / rel_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{art_id}.md"
    path.write_text(f"---\n{fm_yaml}---\n\n# {fm['title']}\n\n{body}\n", encoding="utf-8")
    return path


# ── AC1: schema accepts + documents the field ─────────────────────────────


class TestAC1SchemaAcceptsField:
    def test_auxiliary_metrics_is_optional_not_required(self):
        schema = yaml.safe_load(EXPT_SCHEMA_SRC.read_text(encoding="utf-8"))
        assert "auxiliary_metrics" in schema.get("optional_fields", [])
        assert "auxiliary_metrics" not in schema.get("required_fields", []), (
            "auxiliary_metrics must be optional so an EXPT without it is valid"
        )

    def test_schema_documents_expected_shape(self):
        """AC1: the expected dict shape is documented in the schema file."""
        text = EXPT_SCHEMA_SRC.read_text(encoding="utf-8")
        assert "auxiliary_metrics" in text
        # Documentation must convey "mapping / metric-name -> value" shape.
        assert ("mapping" in text.lower() or "metric-name" in text.lower()
                or "->" in text), (
            "schema should document auxiliary_metrics as a metric-name -> value dict"
        )

    def test_optional_fields_list_is_well_formed(self):
        """The schema YAML parses cleanly with the documented field present."""
        schema = yaml.safe_load(EXPT_SCHEMA_SRC.read_text(encoding="utf-8"))
        opts = schema.get("optional_fields", [])
        assert isinstance(opts, list)
        # No accidental duplicate entries that would muddy "known field" logic.
        assert len(opts) == len(set(opts)), "optional_fields must not contain duplicates"


# ── AC2: artifacts with auxiliary_metrics pass lint without warnings ──────


class TestAC2LintPassesWithAuxMetrics:
    def test_validate_schema_does_not_flag_auxiliary_metrics_unknown(self, project_root: Path):
        """The field is recognized, so never produces an 'Unknown field' issue."""
        schema = lint_lib.load_schemas(
            project_root / ".specflow" / "schema"
        )["experiment"]
        art = _make_expt(
            extra_fm={"auxiliary_metrics": {"max_drawdown": 0.12, "total_trades": 340}}
        )
        issues = lint_lib.validate_artifact_schema(art, schema)
        unknown_aux = [
            i for i in issues
            if "auxiliary_metrics" in i.get("message", "")
            and "Unknown" in i.get("message", "")
        ]
        assert unknown_aux == [], (
            "auxiliary_metrics is a recognized optional field; must not be flagged Unknown"
        )

    def test_check_schema_clean_with_auxiliary_metrics(self, project_root: Path):
        """Full schema check (incl. unknown-field detection) is clean."""
        art = _make_expt(
            extra_fm={
                "auxiliary_metrics": {
                    "max_drawdown": 0.12,
                    "total_trades": 340,
                    "f1_score": 0.87,
                    "runtime_seconds": 12.4,
                }
            }
        )
        result = artifact_lint.check_schema(
            [art], project_root / ".specflow" / "schema"
        )
        assert result["blocking_count"] == 0
        assert result["warning_count"] == 0, (
            f"EXPT with auxiliary_metrics must be schema-clean: {result['detail']}"
        )

    def test_full_artifact_lint_clean_with_auxiliary_metrics(
        self, project_root: Path, capsys
    ):
        """AC2 end-to-end: a clean EXPT with auxiliary_metrics passes the whole
        `specflow artifact-lint` pipeline with zero warnings."""
        _write_expt(
            project_root,
            art_id="EXPT-010",
            extra_fm={
                "metric_value": 1.45,
                "change_category": "features",
                "summary": "Clean EXPT with auxiliary_metrics",
                "hypothesis": "adding feature X lifts the primary metric",
                "hypothesis_outcome": "supported",
                "auxiliary_metrics": {
                    "max_drawdown": 0.12,
                    "total_trades": 340,
                    "f1_score": 0.87,
                },
            },
        )
        rc = artifact_lint.run(project_root, {})
        out = capsys.readouterr().out
        assert rc == 0, f"artifact-lint should PASS, got rc={rc}:\n{out}"
        # "all checks clean" is the zero-warning summary line; PASS-with-warnings
        # (also rc 0) prints a different summary, so this asserts warning-free.
        assert "all checks clean" in out, (
            f"artifact-lint should be warning-free with auxiliary_metrics:\n{out}"
        )
        # Sanity: the auxiliary field is actually present on the discovered EXPT.
        expts = [
            a for a in art_lib.discover_artifacts(project_root)
            if art_lib.get_prefix_from_id(a.id) == "EXPT"
        ]
        assert len(expts) == 1
        assert expts[0].frontmatter["auxiliary_metrics"] == {
            "max_drawdown": 0.12, "total_trades": 340, "f1_score": 0.87,
        }


# ── AC3: creation + round-trip (absent / present / malformed) ─────────────


class TestAC3RoundTrip:
    def test_field_absent_is_valid(self, project_root: Path):
        """AC3 (absent): an EXPT without auxiliary_metrics is schema-valid."""
        art = _make_expt()  # no auxiliary_metrics
        schema = lint_lib.load_schemas(
            project_root / ".specflow" / "schema"
        )["experiment"]
        issues = lint_lib.validate_artifact_schema(art, schema)
        aux_issues = [i for i in issues if "auxiliary_metrics" in i.get("message", "")]
        assert aux_issues == [], (
            "absent optional field must not produce any issue"
        )

    def test_field_present_round_trips_through_read(self, project_root: Path):
        """AC3 (present): the dict survives an on-disk write → parse round-trip."""
        aux = {
            "max_drawdown": 0.12,
            "total_trades": 340,
            "f1_score": 0.87,
            "runtime_seconds": 12.4,
        }
        _write_expt(
            project_root,
            art_id="EXPT-020",
            extra_fm={"auxiliary_metrics": aux},
        )
        expts = [
            a for a in art_lib.discover_artifacts(project_root)
            if a.id == "EXPT-020"
        ]
        assert len(expts) == 1
        assert expts[0].frontmatter["auxiliary_metrics"] == aux, (
            "auxiliary_metrics dict must round-trip through YAML read exactly"
        )

    def test_create_set_auxiliary_metrics_round_trips(
        self, project_root: Path, monkeypatch
    ):
        """AC3 (creation via CLI): `create --set auxiliary_metrics=...` round-trips."""
        from specflow import cli

        monkeypatch.chdir(project_root)
        rc = cli.main([
            "create", "--type", "experiment", "--title", "CLI aux EXPT",
            "--status", "kept", "--skip-dedup-check", "--body", "created via --set",
            "--set", "loop=LOOP-200",
            "--set", "metric_value=1.5",
            "--set", "change_category=features",
            "--set", "summary=aux via create --set",
            "--set", 'auxiliary_metrics={"max_drawdown": 0.12, "total_trades": 340, "f1_score": 0.87}',
        ])
        assert rc == 0, "create with --set auxiliary_metrics must succeed"

        expts = [
            a for a in art_lib.discover_artifacts(project_root)
            if art_lib.get_prefix_from_id(a.id) == "EXPT"
        ]
        assert len(expts) == 1
        fm = expts[0].frontmatter
        # JSON-parsed values: 0.12 -> float, 340 -> int, 0.87 -> float.
        assert fm["auxiliary_metrics"] == {
            "max_drawdown": 0.12, "total_trades": 340, "f1_score": 0.87,
        }
        assert isinstance(fm["auxiliary_metrics"], dict)

    def test_malformed_non_dict_matches_sibling_freeform_fields(
        self, project_root: Path
    ):
        """AC3 (malformed): the EXPT schema is name-only — it does not enforce
        that auxiliary_metrics is a dict, consistent with every sibling freeform
        field (e.g. ``parameters``). A non-dict value is therefore accepted by
        schema validation with no warning, matching the pack's convention for
        other freeform fields; type/value guidance is advisory
        (autoresearch-logging), not schema-enforced.
        """
        schema = lint_lib.load_schemas(
            project_root / ".specflow" / "schema"
        )["experiment"]

        # auxiliary_metrics populated with a non-dict (malformed shape).
        aux_art = _make_expt(extra_fm={"auxiliary_metrics": "not-a-dict"})
        aux_issues = lint_lib.validate_artifact_schema(aux_art, schema)

        # Sibling freeform field for parity comparison.
        par_art = _make_expt(extra_fm={"parameters": "not-a-dict"})
        par_issues = lint_lib.validate_artifact_schema(par_art, schema)

        # Neither known field name is flagged; no type enforcement exists, so
        # neither produces an issue that mentions the field.
        assert not any("auxiliary_metrics" in i.get("message", "") for i in aux_issues), (
            "name-only schema must not type-check auxiliary_metrics; "
            f"got issues: {aux_issues}"
        )
        assert not any("parameters" in i.get("message", "") for i in par_issues), (
            "sibling freeform field `parameters` behaves the same way "
            "(no type enforcement); got issues: " + str(par_issues)
        )
