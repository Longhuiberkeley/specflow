"""v1.13.2 ergonomics — Wave 2: discoverability + lint guidance.

Covers (house doctrine: accounting-not-policing, no new blocking gates,
advisory hints only):

  W2.2 — artifact-lint appends a deterministic one-command ``→ fix:`` hint to
         findings that already fire (typo status, missing/empty acceptance
         criteria). Zero new warnings; exit codes unchanged.
  W2.3 — ``update --ac`` replaces/inserts the Acceptance Criteria section
         (other sections preserved); ``create --add-link`` append-style parity.

Review hardening (adversarial release review):
  - ``--ac`` mutation is heading-anchored + fence-aware + level-aware; prose
    mentions, fenced examples, and h4 headings are never touched.
  - ``--ac`` is REQ/STORY-only, fails loudly on >1 AC heading, and conflicts
    loudly with ``--body`` / ``--set body=``.
  - ``--body``/stdin never silently replace the body alongside other updates;
    empty ``--set body=`` is a no-op, never a wipe.
  - flat ``--set`` never rejects an established custom field; invalid current
    statuses stay repairable via ``--status`` (so lint's fix hint works).
  - ``brief --next`` DEC blast radius is a union (shared downstream counted
    once) computed in one discover pass.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
import yaml

from specflow.commands import create as create_cmd
from specflow.commands import update as update_cmd
from specflow.commands import artifact_lint as lint_cmd
from specflow.lib import artifacts as art_lib


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)

    schemas = {
        "requirement": {
            "prefix": "REQ",
            "allowed_status": {"draft": [], "approved": ["draft"],
                               "implemented": ["approved"]},
            "directory": "_specflow/specs/requirements",
            "required_fields": ["id", "title", "type", "status", "created"],
            "optional_fields": ["priority", "rationale", "tags"],
        },
        "architecture": {
            "prefix": "ARCH",
            "allowed_status": {"draft": [], "approved": ["draft"]},
            "directory": "_specflow/specs/architecture",
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


def _make_req(root: Path, title: str = "T", body: str = "b") -> art_lib.Artifact:
    create_cmd.run(root, _create_args(title=title, body=body))
    arts = art_lib.discover_artifacts(root, artifact_type="requirement")
    return [a for a in arts if a.title == title][0]


# ── W2.3: update --ac replaces/inserts the AC section ───────────────────

class TestUpdateAcSection:
    def test_ac_inserts_when_absent(self, project_root: Path):
        req = _make_req(project_root, body="description only")
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "ac": "1. Given A when B then C"})
        assert rc == 0
        art = art_lib.parse_artifact(art_lib.resolve_link_target(project_root, req.id))
        assert "## Acceptance Criteria" in art.body
        assert "Given A" in art.body
        assert "description only" in art.body  # rest of body preserved

    def test_ac_replaces_existing_section_keeps_others(self, project_root: Path):
        body = ("Intro.\n\n## Acceptance Criteria\n\nold criteria\n\n"
                "## Notes\n\nkeep me")
        req = _make_req(project_root, body=body)
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "ac": "new criteria here"})
        assert rc == 0
        art = art_lib.parse_artifact(art_lib.resolve_link_target(project_root, req.id))
        assert "new criteria here" in art.body
        assert "old criteria" not in art.body
        assert "keep me" in art.body

    def test_body_and_ac_conflict(self, project_root: Path, capsys):
        req = _make_req(project_root)
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "ac": "x", "body": "y"})
        assert rc == 1
        assert "cannot be combined" in capsys.readouterr().out

    # ── Review hardening: mutation precision ──────────────────────────

    def test_ac_prose_mention_survives(self, project_root: Path):
        # Prose containing "acceptance criteria:" must never be treated as a
        # section marker by the mutation path (it truncated the paragraph).
        body = ("Some intro.\n\n"
                "We define acceptance criteria: here is what matters.\n")
        req = _make_req(project_root, body=body)
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "ac": "1. Given X when Y then Z"})
        assert rc == 0
        art = art_lib.parse_artifact(art_lib.resolve_link_target(project_root, req.id))
        assert "acceptance criteria: here is what matters" in art.body
        assert "Some intro." in art.body
        assert "## Acceptance Criteria" in art.body
        assert "Given X" in art.body

    def test_ac_fenced_heading_untouched(self, project_root: Path):
        body = ("Intro.\n\n```markdown\n## Acceptance Criteria\nold example\n"
                "```\n\n## Acceptance Criteria\nreal AC\n")
        req = _make_req(project_root, body=body)
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "ac": "new AC"})
        assert rc == 0
        art = art_lib.parse_artifact(art_lib.resolve_link_target(project_root, req.id))
        assert "old example" in art.body          # fenced example survives
        assert "real AC" not in art.body          # real section replaced
        assert "new AC" in art.body

    def test_ac_h3_sibling_preserved(self, project_root: Path):
        # A ### AC section must not swallow the following ### sibling.
        body = ("Intro.\n\n### Acceptance Criteria\n\nold criteria\n\n"
                "### Notes\n\nkeep me")
        req = _make_req(project_root, body=body)
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "ac": "new criteria"})
        assert rc == 0
        art = art_lib.parse_artifact(art_lib.resolve_link_target(project_root, req.id))
        assert "### Notes" in art.body
        assert "keep me" in art.body
        assert "old criteria" not in art.body
        assert "new criteria" in art.body

    def test_ac_annotated_single_heading_replaced(self, project_root: Path):
        # A single annotated heading ("… (Performance)") IS the AC section:
        # anchored matching replaces it cleanly (no stray prefix, no demote).
        body = ("Intro.\n\n## Acceptance Criteria (Performance)\n\n"
                "- latency < 100ms\n")
        req = _make_req(project_root, body=body)
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "ac": "- functional criterion"})
        assert rc == 0
        art = art_lib.parse_artifact(art_lib.resolve_link_target(project_root, req.id))
        assert "- functional criterion" in art.body
        assert "latency" not in art.body
        assert art.body.count("## Acceptance Criteria") == 1

    def test_ac_h4_heading_never_demoted(self, project_root: Path):
        # h4 is not an AC heading for mutation: append instead of matching a
        # substring inside "####" (which demoted it and corrupted the line).
        body = "Intro.\n\n#### Acceptance Criteria\n\nold deep\n"
        req = _make_req(project_root, body=body)
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "ac": "new criteria"})
        assert rc == 0
        art = art_lib.parse_artifact(art_lib.resolve_link_target(project_root, req.id))
        assert "#### Acceptance Criteria" in art.body
        assert "old deep" in art.body
        assert "new criteria" in art.body

    def test_ac_multiple_headings_fail_loudly(self, project_root: Path, capsys):
        # Two genuine AC headings = ambiguous target. "Earliest wins" would be
        # silent corruption of the other section; fail loudly instead.
        body = ("Intro.\n\n## Acceptance Criteria\n\nfirst\n\n"
                "## Acceptance Criteria (NFR)\n\nsecond\n")
        req = _make_req(project_root, body=body)
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "ac": "new"})
        assert rc == 1
        assert "cannot choose" in capsys.readouterr().out
        art = art_lib.parse_artifact(art_lib.resolve_link_target(project_root, req.id))
        assert "first" in art.body and "second" in art.body  # untouched

    def test_ac_set_body_conflict(self, project_root: Path, capsys):
        req = _make_req(project_root)
        rc = update_cmd.run(project_root, {"artifact_id": req.id, "ac": "x",
                                           "set_fields": ["body=y"]})
        assert rc == 1
        assert "cannot be combined" in capsys.readouterr().out

    def test_body_flag_set_body_conflict(self, project_root: Path, capsys):
        req = _make_req(project_root)
        rc = update_cmd.run(project_root, {"artifact_id": req.id, "body": "y",
                                           "set_fields": ["body=z"]})
        assert rc == 1
        assert "cannot be combined" in capsys.readouterr().out

    def test_ac_type_guard_rejects_arch(self, project_root: Path, capsys):
        create_cmd.run(project_root, _create_args(type="architecture",
                                                  title="A", body="b"))
        arts = art_lib.discover_artifacts(project_root, artifact_type="architecture")
        arch = arts[0]
        rc = update_cmd.run(project_root, {"artifact_id": arch.id, "ac": "x"})
        assert rc == 1
        assert "only valid for REQ and STORY" in capsys.readouterr().out

    def test_ac_fingerprint_matches_after_update(self, project_root: Path):
        from specflow.lib import lint as lint_lib
        req = _make_req(project_root, body="description only")
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "ac": "1. Given A when B then C"})
        assert rc == 0
        art = art_lib.parse_artifact(art_lib.resolve_link_target(project_root, req.id))
        assert lint_lib.validate_fingerprint(art)["match"]


# ── Review hardening: body-writer semantics (--body / --set body= / stdin) ──

class TestBodyWriterSemantics:
    def test_set_body_empty_is_noop_not_wipe(self, project_root: Path):
        req = _make_req(project_root, body="precious content")
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "set_fields": ["body="],
                                           "status": "approved"})
        assert rc == 0
        art = art_lib.parse_artifact(art_lib.resolve_link_target(project_root, req.id))
        assert "precious content" in art.body
        assert art.status == "approved"

    def test_stdin_not_read_when_other_fields_updated(
            self, project_root: Path, capsys, monkeypatch):
        # Piped stdin must never replace the body as a side effect of an
        # unrelated update — advisory instead.
        req = _make_req(project_root, body="precious content")
        monkeypatch.setattr(sys, "stdin", io.StringIO("PIPED BODY"))
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "status": "approved"})
        assert rc == 0
        assert "Stdin data ignored" in capsys.readouterr().out
        art = art_lib.parse_artifact(art_lib.resolve_link_target(project_root, req.id))
        assert "precious content" in art.body
        assert "PIPED BODY" not in art.body

    def test_stdin_replaces_body_when_no_other_updates(
            self, project_root: Path, monkeypatch):
        req = _make_req(project_root, body="old body")
        monkeypatch.setattr(sys, "stdin", io.StringIO("NEW BODY"))
        rc = update_cmd.run(project_root, {"artifact_id": req.id})
        assert rc == 0
        art = art_lib.parse_artifact(art_lib.resolve_link_target(project_root, req.id))
        assert "NEW BODY" in art.body


# ── Review hardening: --set escape hatch honors established custom fields ──

class TestSetEstablishedCustomField:
    def test_existing_near_miss_field_passes_through(self, project_root: Path):
        # 'tagss' is a near-miss of the declared 'tags' field. Written by a
        # pack directly into frontmatter it is established — updating it must
        # not trip the typo did-you-mean (the verification_gate regression).
        req = _make_req(project_root)
        path = art_lib.resolve_link_target(project_root, req.id)
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("status: draft", "status: draft\ntagss: x"),
                        encoding="utf-8")
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "set_fields": ["tagss=y"]})
        assert rc == 0
        art = art_lib.parse_artifact(path)
        assert art.frontmatter.get("tagss") == "y"

    def test_new_near_miss_key_still_rejected(self, project_root: Path, capsys):
        # The typo trap still fires for keys NOT already in the frontmatter.
        req = _make_req(project_root)
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "set_fields": ["tagss=y"]})
        assert rc == 1
        assert "Did you mean 'tags'?" in capsys.readouterr().out


# ── Review hardening: invalid current status stays repairable ─────────────

class TestStatusRepairPath:
    def test_invalid_current_status_repairable(self, project_root: Path):
        # The artifact-lint fix hint (update --status <legal>) must actually
        # succeed on a typo'd status — repair path in the transition gate.
        req = _make_req(project_root)
        path = art_lib.resolve_link_target(project_root, req.id)
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("status: draft", "status: draftt"),
                        encoding="utf-8")
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "status": "approved"})
        assert rc == 0
        art = art_lib.parse_artifact(path)
        assert art.status == "approved"

    def test_transition_gate_still_enforced(self, project_root: Path, capsys):
        # Legal current status + illegal transition = still rejected.
        req = _make_req(project_root)  # status: draft
        rc = update_cmd.run(project_root, {"artifact_id": req.id,
                                           "status": "implemented"})
        assert rc == 1
        assert "Cannot transition" in capsys.readouterr().out


# ── W2.3: create --add-link append-style parity ──────────────────────────

class TestCreateAddLink:
    def test_add_link_appends(self, project_root: Path):
        target = _make_req(project_root, title="Target")
        rc = create_cmd.run(project_root, _create_args(
            title="Linked", add_link=[f"{target.id}:derives_from"]))
        assert rc == 0
        arts = art_lib.discover_artifacts(project_root, artifact_type="requirement")
        linked = [a for a in arts if a.title == "Linked"][0]
        assert any(l.target == target.id and l.role == "derives_from"
                   for l in linked.links)

    def test_add_link_dedups(self, project_root: Path):
        target = _make_req(project_root, title="Target")
        rc = create_cmd.run(project_root, _create_args(
            title="Linked",
            add_link=[f"{target.id}:derives_from", f"{target.id}:derives_from"]))
        assert rc == 0
        arts = art_lib.discover_artifacts(project_root, artifact_type="requirement")
        linked = [a for a in arts if a.title == "Linked"][0]
        matching = [l for l in linked.links
                    if l.target == target.id and l.role == "derives_from"]
        assert len(matching) == 1

    def test_add_link_malformed_errors(self, project_root: Path, capsys):
        rc = create_cmd.run(project_root, _create_args(
            title="Linked", add_link=["no-colon-here"]))
        assert rc == 1
        assert "--add-link expects TARGET:ROLE" in capsys.readouterr().out


# ── W2.2: artifact-lint appends deterministic fix hints ──────────────────

class TestLintFixHints:
    def test_typo_status_gets_fix_hint(self, project_root: Path):
        req = _make_req(project_root)
        # Force an invalid-but-near-miss status directly in frontmatter.
        path = art_lib.resolve_link_target(project_root, req.id)
        text = path.read_text(encoding="utf-8")
        text = text.replace("status: draft", "status: draftt")
        path.write_text(text, encoding="utf-8")

        result = lint_cmd._check_status(
            [art_lib.parse_artifact(path)],
            project_root / ".specflow" / "schema",
        )
        assert "→ fix: specflow update" in result["detail"]
        assert "--status draft" in result["detail"]

    def test_genuinely_invalid_status_gets_no_fix_hint(self, project_root: Path):
        req = _make_req(project_root)
        path = art_lib.resolve_link_target(project_root, req.id)
        text = path.read_text(encoding="utf-8")
        text = text.replace("status: draft", "status: zzzzz")
        path.write_text(text, encoding="utf-8")

        result = lint_cmd._check_status(
            [art_lib.parse_artifact(path)],
            project_root / ".specflow" / "schema",
        )
        assert "invalid status 'zzzzz'" in result["detail"]
        assert "→ fix" not in result["detail"]

    def test_stale_fingerprint_gets_fix_hint(self, project_root: Path):
        req = _make_req(project_root)
        path = art_lib.resolve_link_target(project_root, req.id)
        text = path.read_text(encoding="utf-8")
        # Corrupt the stored fingerprint so it mismatches the body.
        text = text.replace("fingerprint: sha256:", "fingerprint: sha256:deadbeef00")
        path.write_text(text, encoding="utf-8")

        result = lint_cmd._check_fingerprints([art_lib.parse_artifact(path)])
        assert "→ fix: specflow fingerprint-refresh" in result["detail"]
        assert req.id in result["detail"]

    def test_missing_ac_gets_fix_hint(self, project_root: Path):
        req = _make_req(project_root, body="no acceptance criteria here")
        result = lint_cmd._check_acceptance(
            [art_lib.parse_artifact(art_lib.resolve_link_target(project_root, req.id))])
        assert "→ fix: specflow update" in result["detail"]
        assert "--ac" in result["detail"]


# ── W3.1: fingerprint-refresh bare run → report-only ────────────────────

class TestFingerprintRefreshBareRun:
    def _corrupt(self, root: Path, art_id: str) -> None:
        path = art_lib.resolve_link_target(root, art_id)
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace("fingerprint: sha256:", "fingerprint: sha256:deadbeef00"),
            encoding="utf-8",
        )

    def test_bare_run_lists_stale_exit_zero_no_write(self, project_root: Path, capsys):
        from specflow.commands import fingerprint_refresh as fp_cmd
        from specflow.lib import lint as lint_lib
        req = _make_req(project_root)
        self._corrupt(project_root, req.id)

        rc = fp_cmd.run(project_root, {"targets": []})
        out = capsys.readouterr().out
        assert rc == 0
        assert req.id in out
        # Report-only: the artifact is still stale (nothing was written).
        art = art_lib.parse_artifact(art_lib.resolve_link_target(project_root, req.id))
        assert not lint_lib.validate_fingerprint(art)["match"]

    def test_bare_run_clean_project(self, project_root: Path, capsys):
        from specflow.commands import fingerprint_refresh as fp_cmd
        _make_req(project_root)
        rc = fp_cmd.run(project_root, {"targets": []})
        assert rc == 0
        assert "No stale fingerprints" in capsys.readouterr().out

    def test_targeted_refresh_still_mutates(self, project_root: Path):
        from specflow.commands import fingerprint_refresh as fp_cmd
        from specflow.lib import lint as lint_lib
        req = _make_req(project_root)
        self._corrupt(project_root, req.id)
        rc = fp_cmd.run(project_root, {"targets": [req.id]})
        assert rc == 0
        art = art_lib.parse_artifact(art_lib.resolve_link_target(project_root, req.id))
        assert lint_lib.validate_fingerprint(art)["match"]


# ── W3.2: brief --next surfaces unreviewed DEC blast radius ─────────────

class TestBriefDecConeNote:
    def test_unreviewed_dec_noted(self, project_root: Path):
        from specflow.commands import brief as brief_cmd
        # Manually author a DEC artifact with review_status: unreviewed.
        dec_dir = project_root / "_specflow" / "work" / "decisions"
        dec_dir.mkdir(parents=True, exist_ok=True)
        (dec_dir / "DEC-001.md").write_text(
            "---\nid: DEC-001\ntitle: A decision\ntype: decision\nstatus: draft\n"
            "review_status: unreviewed\nlinks: []\n---\n\n# A decision\n",
            encoding="utf-8",
        )
        artifacts = art_lib.discover_artifacts(project_root)
        note = brief_cmd._next_skill_recommendation(
            "idle", artifacts, [], [], None, root=project_root,
        )
        assert "unreviewed DEC" in note
        assert "DEC-001" in note

    def test_no_note_when_no_unreviewed_dec(self, project_root: Path):
        from specflow.commands import brief as brief_cmd
        _make_req(project_root)
        artifacts = art_lib.discover_artifacts(project_root)
        note = brief_cmd._next_skill_recommendation(
            "idle", artifacts, [], [], None, root=project_root,
        )
        assert "unreviewed DEC" not in note

    def test_shared_downstream_counted_once(self, project_root: Path):
        # Blast radius is a UNION across unreviewed DECs: an artifact
        # downstream of two DECs counts once (summing per-DEC cones reported
        # 116 where the true unique count was 5 on dogfood data).
        from specflow.commands import brief as brief_cmd
        dec_dir = project_root / "_specflow" / "work" / "decisions"
        dec_dir.mkdir(parents=True, exist_ok=True)
        for n in ("001", "002"):
            links = ("[{target: DEC-001, role: derives_from}]"
                     if n == "002" else "[]")
            (dec_dir / f"DEC-{n}.md").write_text(
                f"---\nid: DEC-{n}\ntitle: D{n}\ntype: decision\nstatus: draft\n"
                f"review_status: unreviewed\nlinks: {links}\n---\n\n# D\n",
                encoding="utf-8",
            )
        req = _make_req(project_root)
        rc = update_cmd.run(project_root, {
            "artifact_id": req.id,
            "links": '[{"target": "DEC-001", "role": "derives_from"}, '
                     '{"target": "DEC-002", "role": "derives_from"}]',
        })
        assert rc == 0
        artifacts = art_lib.discover_artifacts(project_root)
        note = brief_cmd._next_skill_recommendation(
            "idle", artifacts, [], [], None, root=project_root,
        )
        assert "2 unreviewed DEC(s)" in note
        # REQ is shared downstream (counted once); DEC-002 is also downstream
        # of DEC-001 and must remain in the union even though it is itself one
        # of the unreviewed source nodes.
        assert "blast radius 2 downstream artifact(s)" in note
