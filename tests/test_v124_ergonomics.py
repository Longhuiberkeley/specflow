"""v1.12.4 ergonomics fixes — mined from real agent CLI invocations.

Covers four independent fixes (house doctrine: accounting-not-policing, no new
blocking gates):

  A2 — ``normalize_type()`` + enriched no-schema error in create.
  A4 — central argparse did-you-mean for misspelled subcommands / flags.
  A5 — ``fingerprint-refresh`` accepts artifact IDs and multiple targets.
  A7 — per-type initial status on ``create`` (fixes ``create --type defect``).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from specflow.commands import create as create_cmd
from specflow.commands import fingerprint_refresh as fp_cmd
from specflow.lib import artifacts as art_lib


# ── Fixture ──────────────────────────────────────────────────────────────

@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """A project with core schemas (requirement/architecture/decision/defect/
    qualification-test/experiment) and matching directories."""
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)

    schemas = {
        "requirement": {
            "prefix": "REQ",
            "allowed_status": {"draft": [], "approved": ["draft"],
                               "implemented": ["approved"],
                               "verified": ["implemented"]},
            "directory": "_specflow/specs/requirements",
            "required_fields": ["id", "title", "type", "status", "created"],
            "optional_fields": ["priority", "rationale", "tags"],
        },
        "architecture": {
            "prefix": "ARCH",
            "allowed_status": {"draft": [], "approved": ["draft"]},
            "directory": "_specflow/specs/architecture",
        },
        "decision": {
            "prefix": "DEC",
            "allowed_status": {"draft": [], "approved": ["draft"]},
            "directory": "_specflow/work/decisions",
        },
        "qualification-test": {
            "prefix": "QT",
            "allowed_status": {"draft": [], "approved": ["draft"]},
            "directory": "_specflow/specs/qualification-tests",
        },
        "defect": {
            "prefix": "DEF",
            "allowed_status": {"open": [], "investigating": ["open"],
                               "closed": ["investigating"]},
            "directory": "_specflow/work/defects",
        },
        "experiment": {
            "prefix": "EXPT",
            "allowed_status": {"kept": [], "discarded": [], "crashed": [],
                               "no_op": []},
            "directory": "_specflow/specs/experiments",
        },
    }
    for art_type, spec in schemas.items():
        schema_body: dict = {
            "type": art_type, "prefix": spec["prefix"],
            "allowed_status": spec["allowed_status"],
            "directory": spec["directory"],
        }
        if "required_fields" in spec:
            schema_body["required_fields"] = spec["required_fields"]
            schema_body["optional_fields"] = spec["optional_fields"]
        (schema_dir / f"{art_type}.yaml").write_text(
            yaml.dump(schema_body), encoding="utf-8",
        )

    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump({
            "project": {"name": "t", "created": "2026-01-01"},
            "artifact_types": list(schemas),
            "active_packs": [],
        }),
        encoding="utf-8",
    )
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "idle", "history": []}), encoding="utf-8",
    )

    for spec in schemas.values():
        (root / spec["directory"]).mkdir(parents=True, exist_ok=True)
    return root


def _create_args(**overrides) -> dict:
    args = {
        "type": "requirement", "title": "T", "status": None,
        "priority": None, "rationale": None, "tags": None, "links": None,
        "body": "b", "from_standard": None, "force": False,
        "skip_dedup_check": True, "nfr_category": None, "set_fields": None,
    }
    args.update(overrides)
    return args


# ── A2: normalize_type on create + enriched no-schema error ──────────────

class TestCreateTypeNormalization:
    def test_alias_resolves_through_create(self, project_root: Path):
        # 'def' is an alias/prefix for defect; status omitted -> A7 resolves open.
        rc = create_cmd.run(project_root, _create_args(type="def", title="A defect"))
        assert rc == 0
        defs = list((project_root / "_specflow" / "work" / "defects").glob("DEF-*.md"))
        assert len(defs) == 1
        assert art_lib.parse_artifact(defs[0]).status == "open"

    def test_enriched_no_schema_error_lists_valid_types(self, project_root: Path, capsys):
        rc = create_cmd.run(project_root, _create_args(type="defet", title="Typo"))
        assert rc == 1
        out = capsys.readouterr().out
        assert "No schema found for type 'defet'" in out
        assert "Valid types:" in out
        # close-match suggestion for the typo
        assert "defect" in out

    def test_enriched_error_no_misleading_match(self, project_root: Path, capsys):
        # A token with no close match still lists valid types but no "Did you mean".
        rc = create_cmd.run(project_root, _create_args(type="zzzzzzz", title="Nope"))
        assert rc == 1
        out = capsys.readouterr().out
        assert "Valid types:" in out
        assert "Did you mean" not in out


# ── A7: per-type initial status on create ────────────────────────────────

class TestCreateInitialStatus:
    def test_defect_defaults_to_open(self, project_root: Path):
        # Regression: previously failed with "Invalid status 'draft' for type 'defect'".
        rc = create_cmd.run(project_root, _create_args(type="defect", title="Bug"))
        assert rc == 0
        defs = list((project_root / "_specflow" / "work" / "defects").glob("DEF-*.md"))
        assert art_lib.parse_artifact(defs[0]).status == "open"

    def test_requirement_defaults_to_draft(self, project_root: Path):
        rc = create_cmd.run(project_root, _create_args(type="requirement", title="Need"))
        assert rc == 0
        reqs = list((project_root / "_specflow" / "specs" / "requirements").glob("REQ-*.md"))
        assert art_lib.parse_artifact(reqs[0]).status == "draft"

    def test_experiment_no_status_is_error_listing_statuses(self, project_root: Path, capsys):
        rc = create_cmd.run(project_root, _create_args(type="experiment", title="Expt"))
        assert rc == 1
        out = capsys.readouterr().out
        assert "no unambiguous initial status" in out
        assert "Specify --status" in out
        for s in ("kept", "discarded", "crashed", "no_op"):
            assert s in out

    def test_explicit_status_wins_over_default(self, project_root: Path):
        rc = create_cmd.run(
            project_root, _create_args(type="defect", title="Bug", status="open")
        )
        assert rc == 0
        defs = list((project_root / "_specflow" / "work" / "defects").glob("DEF-*.md"))
        assert art_lib.parse_artifact(defs[0]).status == "open"

    def test_experiment_explicit_status_creates(self, project_root: Path):
        rc = create_cmd.run(
            project_root, _create_args(type="experiment", title="Expt", status="kept")
        )
        assert rc == 0
        expts = list((project_root / "_specflow" / "specs" / "experiments").glob("EXPT-*.md"))
        assert len(expts) == 1
        assert art_lib.parse_artifact(expts[0]).status == "kept"


# ── A4: central argparse did-you-mean ────────────────────────────────────

class TestDidYouMean:
    def test_misspelled_subcommand_suggests_and_exits_2(self, capsys):
        from specflow import cli
        with pytest.raises(SystemExit) as exc:
            cli.main(["creat"])
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "did you mean" in err
        assert "create" in err

    def test_misspelled_flag_suggests_real_flag(self, capsys):
        from specflow import cli
        # --rationel is not a prefix of any option, so argparse rejects it; the
        # hint should point at the create subcommand's --rationale.
        with pytest.raises(SystemExit) as exc:
            cli.main(["create", "--rationel", "x", "--type", "requirement"])
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "did you mean" in err
        assert "--rationale" in err

    def test_unrelated_subcommand_no_hint(self, capsys):
        from specflow import cli
        with pytest.raises(SystemExit) as exc:
            cli.main(["zzzzzz"])
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "did you mean" not in err

    def test_unrelated_flag_no_hint(self, capsys):
        from specflow import cli
        # A truly unrelated flag has no close match -> no misleading hint.
        with pytest.raises(SystemExit) as exc:
            cli.main(["update", "REQ-001", "--zzzzzz", "medium"])
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "did you mean" not in err

    def test_confidence_flag_hints_risk_profile(self, capsys):
        from specflow import cli
        # W2.1: --confidence lives inside the risk_profile map, not as a flag.
        # Non-DEC target: risk_profile is declared only on the decision
        # schema, so the hint explains where confidence lives instead of
        # steering at a --set command that would fail on a REQ
        # (wrong-command erosion).
        with pytest.raises(SystemExit) as exc:
            cli.main(["update", "REQ-001", "--confidence", "medium"])
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "risk_profile.confidence" in err
        assert "decision artifacts" in err

    def test_confidence_flag_hints_set_form_on_dec(self, capsys):
        from specflow import cli
        # DEC target: the actionable did-you-mean points straight at the
        # nested --set form, which succeeds on decision artifacts.
        with pytest.raises(SystemExit) as exc:
            cli.main(["update", "DEC-001", "--confidence", "medium"])
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "did you mean" in err
        assert "--set risk_profile.confidence" in err


# ── A5: fingerprint-refresh accepts IDs + multiple targets ───────────────

class TestFingerprintRefreshMultiTarget:
    def _make(self, root: Path, art_type: str, title: str) -> art_lib.Artifact:
        create_cmd.run(root, _create_args(type=art_type, title=title))
        arts = art_lib.discover_artifacts(root)
        return [a for a in arts if a.title == title][0]

    def test_target_by_artifact_id(self, project_root: Path, capsys):
        art = self._make(project_root, "requirement", "R1")
        rc = fp_cmd.run(project_root, {"targets": [art.id]})
        assert rc == 0
        out = capsys.readouterr().out
        assert art.id in out

    def test_target_by_filepath_still_works(self, project_root: Path, capsys):
        art = self._make(project_root, "requirement", "R2")
        rc = fp_cmd.run(project_root, {"targets": [str(art.path)]})
        assert rc == 0
        out = capsys.readouterr().out
        assert art.id in out

    def test_mixed_targets_partial_success_exits_zero(self, project_root: Path, capsys):
        art = self._make(project_root, "requirement", "R3")
        rc = fp_cmd.run(project_root, {"targets": [art.id, "BOGUS-999"]})
        assert rc == 0  # partial success
        out = capsys.readouterr().out
        assert art.id in out
        assert "Not found: BOGUS-999" in out

    def test_all_targets_unknown_exits_nonzero(self, project_root: Path, capsys):
        rc = fp_cmd.run(project_root, {"targets": ["NOPE-1", "NOPE-2"]})
        assert rc == 1
        out = capsys.readouterr().out
        assert "Not found: NOPE-1" in out
        assert "Not found: NOPE-2" in out

    def test_multi_target_all_valid(self, project_root: Path, capsys):
        a1 = self._make(project_root, "requirement", "A1")
        a2 = self._make(project_root, "defect", "D1")
        rc = fp_cmd.run(project_root, {"targets": [a1.id, a2.id]})
        assert rc == 0
        out = capsys.readouterr().out
        assert a1.id in out
        assert a2.id in out


# ── Shared helper ───────────────────────────────────────────────────────

def _make(root: Path, art_type: str, title: str) -> art_lib.Artifact:
    """Create an artifact and return its parsed Artifact object."""
    create_cmd.run(root, _create_args(type=art_type, title=title))
    arts = art_lib.discover_artifacts(root)
    return [a for a in arts if a.title == title][0]


def _links_of(root: Path, art_id: str) -> list[dict]:
    parsed = art_lib.parse_artifact(art_lib.resolve_link_target(root, art_id))
    return parsed.frontmatter.get("links", []) if parsed else []


# ── A1: link management on update ──────────────────────────────────────

class TestUpdateLinks:
    def test_add_link_appends(self, project_root: Path):
        from specflow.commands import update as update_cmd
        req = _make(project_root, "requirement", "R")
        arch = _make(project_root, "architecture", "A")
        rc = update_cmd.run(project_root, {
            "artifact_id": req.id,
            "add_link": [f"{arch.id}:derives_from"],
        })
        assert rc == 0
        pairs = [(lk["target"], lk["role"]) for lk in _links_of(project_root, req.id)]
        assert (arch.id, "derives_from") in pairs

    def test_add_link_dedups_on_target_and_role(self, project_root: Path):
        from specflow.commands import update as update_cmd
        req = _make(project_root, "requirement", "R")
        arch = _make(project_root, "architecture", "A")
        entry = f"{arch.id}:derives_from"
        # Add the same link three times across two calls — should keep exactly one.
        update_cmd.run(project_root, {"artifact_id": req.id, "add_link": [entry, entry]})
        update_cmd.run(project_root, {"artifact_id": req.id, "add_link": [entry]})
        links = _links_of(project_root, req.id)
        assert sum(1 for lk in links if lk["target"] == arch.id) == 1

    def test_links_replaces_whole_list(self, project_root: Path, capsys):
        # Mined failure: skill taught `update --links '[{...}]'` which argparse
        # rejected before A1. Now it replaces the full list.
        from specflow.commands import update as update_cmd
        import json as _json
        req = _make(project_root, "requirement", "R")
        arch = _make(project_root, "architecture", "A")
        # Seed with one link via --add-link.
        update_cmd.run(project_root, {"artifact_id": req.id,
                                      "add_link": [f"{arch.id}:relates_to"]})
        # Replace with a single derives_from link.
        payload = _json.dumps([{"target": arch.id, "role": "derives_from"}])
        rc = update_cmd.run(project_root, {"artifact_id": req.id, "links": payload})
        assert rc == 0
        links = _links_of(project_root, req.id)
        assert len(links) == 1
        assert (links[0]["target"], links[0]["role"]) == (arch.id, "derives_from")

    def test_remove_link_by_target(self, project_root: Path):
        from specflow.commands import update as update_cmd
        req = _make(project_root, "requirement", "R")
        arch = _make(project_root, "architecture", "A")
        update_cmd.run(project_root, {"artifact_id": req.id,
                                      "add_link": [f"{arch.id}:derives_from"]})
        assert len(_links_of(project_root, req.id)) == 1
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "remove_link": [arch.id]})
        assert rc == 0
        assert _links_of(project_root, req.id) == []

    def test_remove_nonexistent_target_is_noop(self, project_root: Path):
        # Decision: removing a target that isn't linked is an idempotent no-op
        # (clear, no error) — safe to repeat, matches accounting-not-policing.
        from specflow.commands import update as update_cmd
        req = _make(project_root, "requirement", "R")
        arch = _make(project_root, "architecture", "A")
        update_cmd.run(project_root, {"artifact_id": req.id,
                                      "add_link": [f"{arch.id}:derives_from"]})
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "remove_link": ["ARCH-999"]})
        assert rc == 0
        # The real link is untouched.
        assert len(_links_of(project_root, req.id)) == 1

    def test_links_combined_with_add_link_errors(self, project_root: Path, capsys):
        from specflow.commands import update as update_cmd
        req = _make(project_root, "requirement", "R")
        arch = _make(project_root, "architecture", "A")
        rc = update_cmd.run(project_root, {
            "artifact_id": req.id,
            "links": f"{arch.id}:derives_from",
            "add_link": [f"{arch.id}:relates_to"],
        })
        assert rc == 1
        out = capsys.readouterr().out
        assert "cannot be combined" in out


# ── A3: transitions command + transition-error enrichment ──────────────

class TestTransitionsCommand:
    def test_open_defect_legal_next(self, project_root: Path, capsys):
        from specflow.commands import transitions as tr_cmd
        defect = _make(project_root, "defect", "Bug")
        rc = tr_cmd.run(project_root, {"artifact_id": defect.id})
        assert rc == 0
        out = capsys.readouterr().out
        assert "investigating" in out
        assert "Legal next" in out

    def test_approved_requirement_legal_next(self, project_root: Path, capsys):
        from specflow.commands import transitions as tr_cmd
        from specflow.commands import update as update_cmd
        req = _make(project_root, "requirement", "R")
        update_cmd.run(project_root, {"artifact_id": req.id, "status": "approved"})
        rc = tr_cmd.run(project_root, {"artifact_id": req.id})
        assert rc == 0
        out = capsys.readouterr().out
        assert "implemented" in out

    def test_terminal_state_shows_empty(self, project_root: Path, capsys):
        from specflow.commands import transitions as tr_cmd
        from specflow.commands import update as update_cmd
        defect = _make(project_root, "defect", "Bug")
        update_cmd.run(project_root, {"artifact_id": defect.id, "status": "investigating"})
        update_cmd.run(project_root, {"artifact_id": defect.id, "status": "closed"})
        rc = tr_cmd.run(project_root, {"artifact_id": defect.id})
        assert rc == 0
        out = capsys.readouterr().out
        assert "terminal" in out or "(none" in out

    def test_unknown_id_exits_nonzero(self, project_root: Path, capsys):
        from specflow.commands import transitions as tr_cmd
        rc = tr_cmd.run(project_root, {"artifact_id": "BOGUS-999"})
        assert rc == 1
        assert "not found" in capsys.readouterr().out.lower()


class TestTransitionErrorHint:
    def test_bad_transition_message_has_hint(self, project_root: Path, capsys):
        # Closed requires 'investigating'; going open->closed is illegal.
        from specflow.commands import update as update_cmd
        defect = _make(project_root, "defect", "Bug")
        rc = update_cmd.run(project_root, {"artifact_id": defect.id, "status": "closed"})
        assert rc == 1
        out = capsys.readouterr().out
        assert "specflow transitions" in out
        assert "Cannot transition" in out

    def test_invalid_status_on_create_has_hint(self, project_root: Path, capsys):
        rc = create_cmd.run(project_root, _create_args(
            type="defect", title="Bug", status="verified"))
        assert rc == 1
        out = capsys.readouterr().out
        # At create time there is no artifact ID yet — the hint must point at
        # the type-introspection command, not `transitions <ID>`.
        assert "specflow schema defect" in out


# ── A6: list + schema commands ─────────────────────────────────────────

class TestListCommand:
    def test_filter_by_type_and_status(self, project_root: Path, capsys):
        from specflow.commands import list_cmd
        _make(project_root, "defect", "Open bug")
        _make(project_root, "requirement", "A req")
        rc = list_cmd.run(project_root, {
            "type": "defect", "status": "open", "tags": None, "json": False,
        })
        assert rc == 0
        out = capsys.readouterr().out
        assert "Open bug" in out
        assert "A req" not in out

    def test_json_shape(self, project_root: Path, capsys):
        from specflow.commands import list_cmd
        import json as _json
        d = _make(project_root, "defect", "JBug")
        capsys.readouterr()  # flush create output before capturing JSON
        rc = list_cmd.run(project_root, {
            "type": "defect", "status": None, "tags": None, "json": True,
        })
        assert rc == 0
        payload = _json.loads(capsys.readouterr().out)
        assert isinstance(payload, list)
        assert any(e["id"] == d.id for e in payload)
        for key in ("id", "type", "status", "title", "path"):
            assert key in payload[0]

    def test_filter_by_tags_any_overlap(self, project_root: Path, capsys):
        from specflow.commands import list_cmd
        create_cmd.run(project_root, _create_args(
            type="requirement", title="Tagged", tags="alpha,beta"))
        create_cmd.run(project_root, _create_args(
            type="requirement", title="Other", tags="gamma"))
        rc = list_cmd.run(project_root, {
            "type": None, "status": None, "tags": "alpha", "json": False,
        })
        assert rc == 0
        out = capsys.readouterr().out
        assert "Tagged" in out
        assert "Other" not in out


class TestSchemaCommand:
    def test_requirement_shows_fields_and_transitions(self, project_root: Path, capsys):
        from specflow.commands import schema_cmd
        rc = schema_cmd.run(project_root, {"type": "requirement"})
        assert rc == 0
        out = capsys.readouterr().out
        assert "Required fields" in out
        assert "Optional fields" in out
        assert "Transition map" in out
        assert "draft" in out

    def test_alias_dec_resolves(self, project_root: Path, capsys):
        from specflow.commands import schema_cmd
        rc = schema_cmd.run(project_root, {"type": "dec"})
        assert rc == 0
        out = capsys.readouterr().out
        assert "decision" in out

    def test_unknown_type_error_with_valid_list(self, project_root: Path, capsys):
        from specflow.commands import schema_cmd
        rc = schema_cmd.run(project_root, {"type": "zzzzz"})
        assert rc == 1
        out = capsys.readouterr().out
        assert "Valid types" in out


# ── WS-B: regression corpus from mined failures ────────────────────────

class TestMinedFailures:
    def test_add_link_on_defect_to_architecture(self, project_root: Path):
        # Mined: agent invented `update DEF-x --add-link ARCH-y:relates_to`
        # and the flag was rejected by argparse before A1.
        from specflow.commands import update as update_cmd
        defect = _make(project_root, "defect", "Def")
        arch = _make(project_root, "architecture", "Arch")
        rc = update_cmd.run(project_root, {
            "artifact_id": defect.id,
            "add_link": [f"{arch.id}:relates_to"],
        })
        assert rc == 0
        pairs = [(lk["target"], lk["role"]) for lk in _links_of(project_root, defect.id)]
        assert (arch.id, "relates_to") in pairs

    def test_guessed_link_subcommand_rejected(self, capsys):
        # Mined: agent guessed `specflow link A B --role derives_from` (4x).
        # There is no `link` subcommand — argparse must reject it.
        from specflow import cli
        with pytest.raises(SystemExit) as exc:
            cli.main(["link", "REQ-001", "ARCH-001", "--role", "derives_from"])
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "invalid choice" in err
        # difflib suggests the closest real subcommand by string similarity.
        assert "did you mean" in err

    def test_misspelled_schema_suggests_schema(self, capsys):
        # Mined: `specflow shema req` — did-you-mean should point at `schema`.
        from specflow import cli
        with pytest.raises(SystemExit) as exc:
            cli.main(["shema", "req"])
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "did you mean" in err
        assert "schema" in err

    def test_list_defect_open_via_run(self, project_root: Path, capsys):
        from specflow.commands import list_cmd
        _make(project_root, "defect", "Smoky")
        rc = list_cmd.run(project_root, {
            "type": "defect", "status": "open", "tags": None, "json": False,
        })
        assert rc == 0
        assert "Smoky" in capsys.readouterr().out

    def test_bad_transition_hint_present(self, project_root: Path, capsys):
        # Mined: SPIKE-style illegal transition rejected, but with no hint.
        # Now the message must mention `specflow transitions`.
        from specflow.commands import update as update_cmd
        defect = _make(project_root, "defect", "D")
        rc = update_cmd.run(project_root, {"artifact_id": defect.id, "status": "closed"})
        assert rc == 1
        combined = capsys.readouterr()
        assert "specflow transitions" in (combined.out + combined.err)

    def test_transitions_prints_legal_next(self, project_root: Path, capsys):
        from specflow.commands import transitions as tr_cmd
        defect = _make(project_root, "defect", "D")
        rc = tr_cmd.run(project_root, {"artifact_id": defect.id})
        assert rc == 0
        assert "investigating" in capsys.readouterr().out

    def test_create_type_dec_alias(self, project_root: Path):
        rc = create_cmd.run(project_root, _create_args(type="dec", title="A decision"))
        assert rc == 0
        decs = list((project_root / "_specflow" / "work" / "decisions").glob("DEC-*.md"))
        assert len(decs) == 1

    def test_create_type_qt_alias(self, project_root: Path):
        rc = create_cmd.run(project_root, _create_args(type="qt", title="A qual test"))
        assert rc == 0
        qts = list((project_root / "_specflow" / "specs" / "qualification-tests").glob("QT-*.md"))
        assert len(qts) == 1

    def test_create_type_DEF_uppercase_prefix(self, project_root: Path):
        rc = create_cmd.run(project_root, _create_args(type="DEF", title="Upper"))
        assert rc == 0
        defs = list((project_root / "_specflow" / "work" / "defects").glob("DEF-*.md"))
        assert len(defs) == 1


# ── A8: skill / agent-context doc content ──────────────────────────────

class TestSkillAndContextDocs:
    """Guard against the bypass regression: skills must not teach a flag that
    doesn't exist, and agent-context must steer agents toward the new commands.
    """

    _REPO_ROOT = Path(__file__).resolve().parent.parent

    def test_discover_skill_no_json_links_form(self):
        for rel in [
            ".claude/skills/specflow-discover/SKILL.md",
            "src/specflow/templates/skills/shared/specflow-discover/SKILL.md",
        ]:
            text = (self._REPO_ROOT / rel).read_text(encoding="utf-8")
            # The Step-4 update-via-JSON bypass is replaced by --add-link.
            assert "--add-link <prerequisite-REQ>:derives_from" in text
            # No `update` command in the skill teaches the --links JSON form.
            assert "dependent-REQ> --links" not in text

    def test_agent_context_mentions_transitions(self):
        text = (self._REPO_ROOT / "src/specflow/templates/agent-context.md").read_text(encoding="utf-8")
        assert "specflow transitions" in text
        # The old linear status-flow statement must be gone.
        assert "Status Flow:** `draft` → `approved` → `implemented` → `verified`" not in text

    def test_agent_context_distinguishes_specflow_dirs(self):
        text = (self._REPO_ROOT / "src/specflow/templates/agent-context.md").read_text(encoding="utf-8")
        assert "_specflow/" in text
        assert "specflow update" in text

    def test_agent_context_is_lean_and_tldr_default(self):
        text = (self._REPO_ROOT / "src/specflow/templates/agent-context.md").read_text(encoding="utf-8")
        non_empty = [ln for ln in text.splitlines() if ln.strip()]
        assert len(non_empty) <= 40, (
            f"agent-context.md grew to {len(non_empty)} non-empty lines; "
            f"keep the always-on block near 30 lines"
        )
        lowered = text.lower()
        assert "lead with the answer" in lowered
        assert "no preamble" in lowered


# ── Review-fix hardening (pre-release review findings) ─────────────────

class TestLinkInputHardening:
    """Malformed link inputs must fail loudly and leave links untouched.

    Pinned by both pre-release reviewers: a lenient _parse_links used to
    silently wipe links (malformed --links), silently no-op (bare --add-link),
    crash with a traceback (non-dict JSON entries), or write garbage (a JSON
    object instead of array).
    """

    def test_add_link_json_object_rejected(self, project_root: Path, capsys):
        from specflow.commands import update as update_cmd
        art = _make(project_root, "requirement", "R")
        rc = update_cmd.run(project_root, {
            "artifact_id": art.id,
            "add_link": ['{"target": "ARCH-001", "role": "derives_from"}'],
        })
        assert rc == 1
        assert _links_of(project_root, art.id) == []

    def test_links_string_array_rejected_without_traceback(self, project_root: Path, capsys):
        from specflow.commands import update as update_cmd
        art = _make(project_root, "requirement", "R")
        rc = update_cmd.run(project_root, {"artifact_id": art.id, "links": '["a", "b"]'})
        assert rc == 1
        out = capsys.readouterr().out
        assert "target and a role" in out
        assert _links_of(project_root, art.id) == []

    def test_add_link_bare_target_rejected(self, project_root: Path, capsys):
        from specflow.commands import update as update_cmd
        art = _make(project_root, "requirement", "R")
        rc = update_cmd.run(project_root, {"artifact_id": art.id, "add_link": ["ARCH-001"]})
        assert rc == 1
        assert "TARGET:ROLE" in capsys.readouterr().out
        assert _links_of(project_root, art.id) == []

    def test_links_malformed_json_does_not_wipe_existing(self, project_root: Path, capsys):
        from specflow.commands import update as update_cmd
        art = _make(project_root, "requirement", "R")
        rc = update_cmd.run(project_root, {
            "artifact_id": art.id, "add_link": ["ARCH-001:derives_from"],
        })
        assert rc == 0
        # Malformed replace input must error, not write an empty list.
        rc = update_cmd.run(project_root, {"artifact_id": art.id, "links": "{"})
        assert rc == 1
        links = _links_of(project_root, art.id)
        assert len(links) == 1 and links[0]["target"] == "ARCH-001"

    def test_create_links_json_object_rejected(self, project_root: Path, capsys):
        rc = create_cmd.run(project_root, _create_args(
            title="Bad", links='{"target": "ARCH-001", "role": "derives_from"}'))
        assert rc == 1
        assert "--links" in capsys.readouterr().out


class TestListTypeValidation:
    def test_unknown_type_errors_instead_of_listing_everything(self, project_root: Path, capsys):
        from specflow.commands import list_cmd
        _make(project_root, "defect", "Should not appear")
        rc = list_cmd.run(project_root, {
            "type": "bogus", "status": None, "tags": None, "json": False,
        })
        assert rc == 1
        out = capsys.readouterr().out
        assert "No schema found for type 'bogus'" in out
        assert "Valid types:" in out
        assert "Should not appear" not in out


class TestNewCommandWiring:
    """transitions/list/schema must be registered in the cli dispatch dict —
    a dropped entry must fail a test, not just manual smoke."""

    def test_transitions_wired(self):
        from specflow import cli
        with pytest.raises(SystemExit) as exc:
            cli.main(["transitions", "--help"])
        assert exc.value.code == 0

    def test_list_wired(self):
        from specflow import cli
        with pytest.raises(SystemExit) as exc:
            cli.main(["list", "--help"])
        assert exc.value.code == 0

    def test_schema_wired(self):
        from specflow import cli
        with pytest.raises(SystemExit) as exc:
            cli.main(["schema", "--help"])
        assert exc.value.code == 0


# ── Post-release review fixes, exercised through the real CLI (cli.main) ─
# Unlike the classes above (which call ``*_cmd.run`` with hand-built dicts),
# these pass real argv through ``cli.main`` so argparse wiring is covered too.
# They guard the v1.12.4 follow-up fixes (T1.2, T2.1, T2.2, T2.3, T2.5).

class TestReviewFixesViaCli:
    def test_create_malformed_links_rejected(self, project_root, monkeypatch, capsys):
        # T1.2: create --links must validate entries (previously only update did).
        from specflow import cli
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "create", "--type", "requirement", "--title", "Bad links",
            "--body", "b", "--links", '[{"foo":"bar"}]',
        ])
        assert rc == 1
        out = capsys.readouterr().out
        assert "--links" in out
        assert "target and a role" in out
        # No artifact was written.
        arts = art_lib.discover_artifacts(project_root)
        assert not [a for a in arts if a.title == "Bad links"]

    def test_update_set_links_conflicts_with_add_link(self, project_root, monkeypatch, capsys):
        # T2.1: --set links= combined with --add-link must error, not silently
        # drop the --set value.
        from specflow import cli
        req = _make(project_root, "requirement", "R")
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "update", req.id,
            "--set", 'links=[{"target":"ARCH-1","role":"derives_from"}]',
            "--add-link", "ARCH-2:derives_from",
        ])
        assert rc == 1
        assert "cannot be combined" in capsys.readouterr().out

    def test_update_noop_remove_link_does_not_rewrite(self, project_root, monkeypatch, capsys):
        # T2.2: removing a non-linked target is a no-op — no rewrite, no
        # "Updated", the real link untouched.
        from specflow import cli
        from specflow.commands import update as update_cmd
        req = _make(project_root, "requirement", "R")
        arch = _make(project_root, "architecture", "A")
        update_cmd.run(project_root, {"artifact_id": req.id,
                                      "add_link": [f"{arch.id}:derives_from"]})
        monkeypatch.chdir(project_root)
        capsys.readouterr()  # clear seeded output
        rc = cli.main(["update", req.id, "--remove-link", "ARCH-999"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "No link changes" in out          # only printed on the no-op path
        assert "Updated" not in out              # the rewrite path was NOT taken
        # The real link survived.
        assert any(lk["target"] == arch.id for lk in _links_of(project_root, req.id))

    def test_help_epilog_lists_standards_and_defect_from_suspect(self):
        # T2.5: two previously-hidden commands now appear in the phase-grouped
        # epilog. (Asserted on the constant directly — the --help choices list
        # would mask a regression since it lists every registered subcommand.)
        from specflow.cli import _HELP_EPILOG
        assert "standards" in _HELP_EPILOG
        assert "defect-from-suspect" in _HELP_EPILOG

    def test_schema_renders_string_predecessor_without_charsplit(self, project_root, monkeypatch, capsys):
        # T2.3: a schema declaring a bare-string predecessor (hand-edited/pack)
        # renders "reviewed", not "r, e, v, i, e, w, e, d".
        from specflow import cli
        (project_root / ".specflow" / "schema" / "customflow.yaml").write_text(
            "type: customflow\nprefix: CUST\n"
            "allowed_status:\n  open: []\n  approved: reviewed\n"
            "directory: _specflow/work/custom\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(project_root)
        rc = cli.main(["schema", "customflow"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "reviewed" in out
        assert "r, e, v" not in out
