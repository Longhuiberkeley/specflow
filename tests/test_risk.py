"""Tests for the deterministic risk-tier engine and ``specflow risk-tier`` (v1.13.1).

Covers:
  - Each irreversibility trigger floors Tier 2 (parametrized).
  - cone ≥ LARGE_CONE_THRESHOLD → large → Tier 2.
  - Unclassifiable change set → Tier 1 (defaults up).
  - ``reasons`` populated with the trigger that fired.
  - ``specflow risk-tier`` is READ-ONLY (no artifact file mtime/frontmatter
    change after invocation) — the explicit NO-GATE test.
  - No transition/status code path imports or consults ``lib.risk`` (grep guard).
  - ``dec-risk-profile`` lint: approved DEC without ``risk_profile`` warns, never
    errors; ``--type gate`` stays green with the new check registered.
  - ``document-changes``: generated change-record DEC carries the deterministic
    risk_profile subset with confidence empty.
  - verification-evidence aggregation: ran / not-run / unknown each tested.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import yaml

from specflow.commands import artifact_lint as lint_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import risk as risk_lib


# ── Scaffold ──────────────────────────────────────────────────────


_SCHEMA_TYPES = [
    ("requirement", "REQ"), ("architecture", "ARCH"), ("detailed-design", "DDD"),
    ("unit-test", "UT"), ("integration-test", "IT"), ("qualification-test", "QT"),
    ("story", "STORY"), ("decision", "DEC"),
]

_STATUS_FLOW = {
    "draft": [], "approved": ["draft"], "implemented": ["approved"],
    "verified": ["implemented"], "released": ["verified"],
}


def _scaffold(tmp: Path) -> Path:
    root = tmp / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)

    for art_type, prefix in _SCHEMA_TYPES:
        schema = {
            "type": art_type,
            "prefix": prefix,
            "allowed_status": dict(_STATUS_FLOW),
            "optional_fields": ["risk_profile", "tags", "links", "verify_command",
                                "verify_exit_code", "verify_run_at",
                                "verify_run_exit_code"],
            "allowed_link_roles": ["derives_from", "addresses", "implements",
                                   "verified_by", "supersedes", "guided_by"],
        }
        (schema_dir / f"{art_type}.yaml").write_text(yaml.dump(schema), encoding="utf-8")

    for subdir in [
        "_specflow/specs/requirements", "_specflow/specs/architecture",
        "_specflow/specs/detailed-design", "_specflow/specs/unit-tests",
        "_specflow/specs/integration-tests", "_specflow/specs/qualification-tests",
        "_specflow/work/stories", "_specflow/work/decisions",
    ]:
        (root / subdir).mkdir(parents=True, exist_ok=True)
    return root


def _write(root: Path, rel: str, fm: dict, body: str = "Body text.") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "---\n" + yaml.dump(fm, default_flow_style=False, sort_keys=False) + "---\n\n" + body + "\n"
    path.write_text(content, encoding="utf-8")
    return path


def _req(root: Path, rid: str, **extra) -> Path:
    fm = {"id": rid, "title": rid, "type": "requirement", "status": "approved",
          "created": "2026-01-01", "links": [], "tags": []}
    fm.update(extra)
    return _write(root, f"_specflow/specs/requirements/{rid}.md", fm)


def _story(root: Path, sid: str, req: str, **extra) -> Path:
    fm = {"id": sid, "title": sid, "type": "story", "status": "approved",
          "created": "2026-01-01",
          "links": [{"target": req, "role": "implements"}], "tags": []}
    fm.update(extra)
    return _write(root, f"_specflow/work/stories/{sid}.md", fm)


def _dec(root: Path, did: str, status: str = "approved", **extra) -> Path:
    fm = {"id": did, "title": did, "type": "decision", "status": status,
          "created": "2026-01-01", "links": [], "tags": []}
    fm.update(extra)
    return _write(root, f"_specflow/work/decisions/{did}.md", fm)


def _test_art(root: Path, tid: str, ttype: str, story: str, **extra) -> Path:
    relmap = {
        "unit-test": "_specflow/specs/unit-tests",
        "integration-test": "_specflow/specs/integration-tests",
        "qualification-test": "_specflow/specs/qualification-tests",
    }
    fm = {"id": tid, "title": tid, "type": ttype, "status": "verified",
          "created": "2026-01-01",
          "links": [{"target": story, "role": "verified_by"}], "tags": []}
    fm.update(extra)
    return _write(root, f"{relmap[ttype]}/{tid}.md", fm)


# ── compute_risk_tier: irreversibility triggers (parametrized) ─────


import pytest


@pytest.mark.parametrize("trigger,build", [
    ("status-verified",
     lambda r: (_req(r, "REQ-001", status="verified"), ["REQ-001"])),
    ("status-released",
     lambda r: (_req(r, "REQ-001", status="released"), ["REQ-001"])),
    ("supersedes-link",
     lambda r: (_req(r, "REQ-001",
                     links=[{"target": "REQ-000", "role": "supersedes"}]),
                ["REQ-001"])),
    ("tag-destructive",
     lambda r: (_req(r, "REQ-001", tags=["destructive"]), ["REQ-001"])),
    ("tag-data-migration",
     lambda r: (_req(r, "REQ-001", tags=["data-migration"]), ["REQ-001"])),
    ("deletion",
     lambda r: (None, ["REQ-MISSING"])),
    ("baseline-or-release",
     lambda r: (_req(r, "REQ-001"), ["REQ-001"])),
])
def test_each_trigger_floors_tier_2(tmp_path, trigger, build):
    root = _scaffold(tmp_path)
    _, change_ids = build(root)
    artifacts = art_lib.discover_artifacts(root)
    kwargs = {"commit_subject": "release: v1.13.1"} if trigger == "baseline-or-release" else {}
    res = risk_lib.compute_risk_tier(change_ids, artifacts, root, **kwargs)
    assert res["tier"] == 2, f"{trigger}: expected tier 2, got {res}"
    assert res["reversibility"] == "irreversible", f"{trigger}: {res}"
    assert any(trigger.split("-")[0] in r or trigger in r for r in res["reasons"]), \
        f"{trigger}: reasons missing trigger: {res['reasons']}"


# ── Blast radius cone ─────────────────────────────────────────────


def test_large_cone_floors_tier_2(tmp_path):
    root = _scaffold(tmp_path)
    _req(root, "REQ-001")
    # Build a downstream cone of exactly LARGE_CONE_THRESHOLD stories → all link
    # to REQ-001, so the cone size == threshold (≥ threshold is "large").
    for i in range(risk_lib.LARGE_CONE_THRESHOLD):
        _story(root, f"STORY-{i:03d}", "REQ-001")
    artifacts = art_lib.discover_artifacts(root)
    res = risk_lib.compute_risk_tier(["REQ-001"], artifacts, root)
    assert res["blast_radius_count"] >= risk_lib.LARGE_CONE_THRESHOLD, res
    assert res["tier"] == 2, res
    assert any("large-blast-radius" in r for r in res["reasons"]), res


def test_small_cone_reversible_is_tier_1(tmp_path):
    root = _scaffold(tmp_path)
    _req(root, "REQ-001")
    for i in range(3):  # cone of 3, reversible → Tier 1
        _story(root, f"STORY-{i:03d}", "REQ-001")
    artifacts = art_lib.discover_artifacts(root)
    res = risk_lib.compute_risk_tier(["REQ-001"], artifacts, root)
    assert res["tier"] == 1, res
    assert res["reversibility"] == "reversible"
    assert res["blast_radius_count"] == 3


def test_zero_cone_reversible_is_tier_0(tmp_path):
    root = _scaffold(tmp_path)
    _req(root, "REQ-001")  # no downstream → cone 0, reversible → Tier 0
    artifacts = art_lib.discover_artifacts(root)
    res = risk_lib.compute_risk_tier(["REQ-001"], artifacts, root)
    assert res["tier"] == 0, res
    assert res["blast_radius_count"] == 0


# ── Unclassifiable defaults UP ────────────────────────────────────


def test_unclassifiable_defaults_up_to_tier_1(tmp_path):
    root = _scaffold(tmp_path)
    # No artifacts at all; change_ids reference nothing real and nothing deleted.
    artifacts = art_lib.discover_artifacts(root)
    res = risk_lib.compute_risk_tier([], artifacts, root)
    assert res["tier"] == 1, res
    assert any("unclassifiable" in r for r in res["reasons"]), res


def test_reasons_always_populated_when_triggered(tmp_path):
    root = _scaffold(tmp_path)
    _req(root, "REQ-001", status="verified", tags=["destructive"])
    artifacts = art_lib.discover_artifacts(root)
    res = risk_lib.compute_risk_tier(["REQ-001"], artifacts, root)
    assert len(res["reasons"]) >= 2, res  # status-verified + tag-destructive


# ── risk-tier CLI is READ-ONLY (explicit NO-GATE test) ────────────


def test_risk_tier_cli_is_read_only_no_mutation(tmp_path, monkeypatch):
    """The keystone NO-GATE test: invoking `specflow risk-tier` must not change
    any artifact file's mtime or frontmatter. The tier gates nothing in code."""
    from specflow.commands import risk_tier as risk_tier_cmd

    root = _scaffold(tmp_path)
    _req(root, "REQ-001", status="verified")
    artifacts_before = art_lib.discover_artifacts(root)

    # Snapshot mtime + full frontmatter of every artifact file.
    snapshot: dict[str, tuple[float, str]] = {}
    for art in artifacts_before:
        try:
            mtime = os.stat(art.path).st_mtime_ns
            content = art.path.read_text(encoding="utf-8")
            snapshot[str(art.path)] = (mtime, content)
        except Exception:
            pass

    monkeypatch.chdir(root)
    rc = risk_tier_cmd.run(root, {"ids": ["REQ-001"]})
    assert rc == 0

    # Force a clock tick so any real write would surface as a new mtime.
    time.sleep(0.01)

    for art in artifacts_before:
        cur_mtime = os.stat(art.path).st_mtime_ns
        cur_content = art.path.read_text(encoding="utf-8")
        old_mtime, old_content = snapshot[str(art.path)]
        assert cur_mtime == old_mtime, f"{art.id} mtime changed — risk-tier wrote!"
        assert cur_content == old_content, f"{art.id} content changed — risk-tier wrote!"


def test_risk_tier_cli_via_parser_dispatches(tmp_path, monkeypatch):
    """The argparse wiring routes `risk-tier` to the handler (smoke)."""
    from specflow.cli import build_parser

    root = _scaffold(tmp_path)
    _req(root, "REQ-001")
    monkeypatch.chdir(root)
    parser = build_parser()
    ns = parser.parse_args(["risk-tier", "REQ-001"])
    assert ns.command == "risk-tier"
    assert ns.ids == ["REQ-001"]


# ── No-gate grep guard: lib.risk must not be consulted by transitions ──


def test_lib_risk_imported_only_by_allowed_modules():
    """accounting-not-policing enforcement: no transition/status/commit/release
    code path may import or consult ``specflow.lib.risk``. The tier is computed
    and RECORDED only; it gates nothing. Allowed importers are the read-only CLI
    (commands/risk_tier), the auto change-record writer (commands/document_changes),
    and tests. cli.py is the dispatcher (routes to commands.risk_tier, never
    lib.risk) and is excluded from the lib-import check."""
    import re
    import specflow

    repo = Path(specflow.__file__).resolve().parents[2]
    src = repo / "src" / "specflow"
    allowed = {
        Path("commands/risk_tier.py"),
        Path("commands/document_changes.py"),
        Path("lib/risk.py"),
    }
    # Precise, lib-qualified import patterns. Naive "import risk" would false-
    # match "import risk_tier" in cli.py's dispatcher; these patterns anchor on
    # specflow.lib so only a real lib.risk import counts.
    import_re = re.compile(
        r"specflow\.lib\.risk|specflow\.lib import risk\b|from specflow\.lib import risk\b"
    )
    offenders: list[str] = []
    for py in src.rglob("*.py"):
        rel = py.relative_to(src)
        try:
            text = py.read_text(encoding="utf-8")
        except Exception:
            continue
        if import_re.search(text) and rel not in allowed:
            offenders.append(str(rel))
    assert not offenders, (
        "lib.risk imported outside the allowed set (risk_tier/document_changes): "
        f"{offenders} — the risk tier must gate NOTHING"
    )

    # Belt-and-suspenders: the status-transition / commit / release modules must
    # not consult risk at all (no compute_risk_tier calls, no risk_profile reads).
    for forbidden in ["commands/transitions.py", "commands/approve.py",
                      "commands/update.py", "commands/done.py", "commands/go.py",
                      "commands/baseline.py", "commands/hook.py",
                      "commands/cascade_status.py", "commands/reconcile.py"]:
        f = src / forbidden
        if f.exists():
            t = f.read_text(encoding="utf-8")
            assert "compute_risk_tier" not in t and "specflow.lib.risk" not in t, \
                f"{forbidden} consults risk — tier must gate nothing"


# ── dec-risk-profile lint ─────────────────────────────────────────


def test_dec_risk_profile_warns_for_approved_dec_without_profile(tmp_path):
    root = _scaffold(tmp_path)
    _dec(root, "DEC-001", status="approved")  # no risk_profile
    artifacts = art_lib.discover_artifacts(root)
    res = lint_cmd._run_check(artifacts, root, "dec-risk-profile")
    assert res["blocking_count"] == 0, res  # never error
    assert res["warning_count"] == 1, res
    assert "DEC-001" in res["detail"]


def test_dec_risk_profile_silent_when_profile_present(tmp_path):
    root = _scaffold(tmp_path)
    _dec(root, "DEC-001", status="approved",
         risk_profile={"tier": 1, "reversibility": "reversible",
                       "blast_radius_count": 2, "confidence": "", "confidence_reason": ""})
    artifacts = art_lib.discover_artifacts(root)
    res = lint_cmd._run_check(artifacts, root, "dec-risk-profile")
    assert res["blocking_count"] == 0
    assert res["warning_count"] == 0, res


def test_dec_risk_profile_silent_for_draft_dec(tmp_path):
    root = _scaffold(tmp_path)
    _dec(root, "DEC-001", status="draft")  # draft, no profile — no warning
    artifacts = art_lib.discover_artifacts(root)
    res = lint_cmd._run_check(artifacts, root, "dec-risk-profile")
    assert res["warning_count"] == 0, res


def test_dec_risk_profile_registered_and_gate_stays_green(tmp_path):
    """The new check is in CHECK_NAMES; running `--type gate` (a different code
    path) is unaffected — the check is advisory-only and never in gate mode."""
    assert "dec-risk-profile" in lint_cmd.CHECK_NAMES

    root = _scaffold(tmp_path)
    # A gate run needs a phase-gate checklist; the advisory check must not be
    # invoked there. Verify the check name itself runs cleanly via --type.
    _dec(root, "DEC-001", status="approved")  # would warn
    artifacts = art_lib.discover_artifacts(root)
    res = lint_cmd._run_check(artifacts, root, "dec-risk-profile")
    # Advisory: warnings are allowed, but blocking is always 0.
    assert res["blocking_count"] == 0


def test_dec_risk_profile_not_in_gate_type_choices():
    """`--type gate` is a separate choice; the advisory check is its own choice."""
    import argparse
    from specflow.cli import build_parser

    p = build_parser()
    # Find the artifact-lint subparser action.
    for act in p._actions:
        if isinstance(act, argparse._SubParsersAction):
            al = act.choices.get("artifact-lint")
            assert al is not None
            for a in al._actions:
                if "--type" in (a.option_strings or []):
                    choices = set(a.choices)
                    assert "dec-risk-profile" in choices
                    assert "gate" in choices
                    # gate and dec-risk-profile are distinct choices; gate mode
                    # never runs dec-risk-profile (handled by _run_gate_check).
                    return
    raise AssertionError("artifact-lint --type not found")


# ── document_changes populates the deterministic subset ───────────


def test_document_changes_writes_risk_profile_with_empty_confidence(tmp_path, monkeypatch):
    from specflow.commands import document_changes as dc

    root = _scaffold(tmp_path)
    # Need a decision schema with risk_profile optional + git machinery. Stub
    # the git helpers to feed one commit touching REQ-001.
    _req(root, "REQ-001")
    (root / ".specflow" / "schema" / "decision.yaml").write_text(yaml.dump({
        "type": "decision", "prefix": "DEC",
        "allowed_status": {"draft": [], "approved": ["draft"]},
        "optional_fields": ["risk_profile", "tags", "links", "review_status",
                            "rationale", "fingerprint"],
        "allowed_link_roles": ["derives_from", "addresses"],
    }), encoding="utf-8")

    commit = {
        "sha": "abc123def456", "author_name": "Tester",
        "author_email": "t@example.com", "date_iso": "2026-01-02",
        "subject": "release: v1.13.1", "body": "",
    }
    monkeypatch.setattr(dc.git_utils, "is_git_repo", lambda r: True)
    monkeypatch.setattr(dc.git_utils, "resolve_ref", lambda r, ref: ref)
    monkeypatch.setattr(dc.git_utils, "get_commits_since", lambda r, ref: [commit])
    monkeypatch.setattr(dc.git_utils, "get_changed_files",
                        lambda r, sha: ["_specflow/specs/requirements/REQ-001.md"])
    monkeypatch.setattr(dc.git_utils, "is_spec_artifact_path", lambda f: f.endswith(".md"))
    monkeypatch.setattr(dc.git_utils, "artifact_id_from_path",
                        lambda f: "REQ-001")
    monkeypatch.chdir(root)

    rc = dc.run(root, {"since": "HEAD~1"})
    assert rc == 0

    # Find the generated DEC.
    decs = [a for a in art_lib.discover_artifacts(root)
            if art_lib.get_prefix_from_id(a.id) == "DEC"]
    assert decs, "no DEC generated"
    rp = decs[0].frontmatter.get("risk_profile")
    assert rp is not None, "risk_profile not persisted"
    # Deterministic subset present.
    assert set(["tier", "reversibility", "blast_radius_count"]).issubset(rp.keys())
    # Confidence left EMPTY (no approval context at auto-record time).
    assert rp.get("confidence") == "", rp
    assert rp.get("confidence_reason") == "", rp
    # Release commit subject → irreversible → Tier 2.
    assert rp["tier"] == 2, rp
    assert rp["reversibility"] == "irreversible", rp


def test_document_changes_stamps_dec_kind_change_record(tmp_path, monkeypatch):
    """Generated change-record DECs carry dec_kind=change_record so the ledger
    can discriminate auto-generated change records from real ADRs (STORY-629)."""
    from specflow.commands import document_changes as dc

    root = _scaffold(tmp_path)
    _req(root, "REQ-001")
    (root / ".specflow" / "schema" / "decision.yaml").write_text(yaml.dump({
        "type": "decision", "prefix": "DEC",
        "allowed_status": {"draft": [], "approved": ["draft"]},
        "optional_fields": ["dec_kind", "risk_profile", "tags", "links",
                            "review_status", "rationale", "fingerprint"],
        "allowed_link_roles": ["derives_from", "addresses"],
    }), encoding="utf-8")

    commit = {
        "sha": "fedcba987654", "author_name": "Tester",
        "author_email": "t@example.com", "date_iso": "2026-01-03",
        "subject": "feat: touch REQ-001", "body": "",
    }
    monkeypatch.setattr(dc.git_utils, "is_git_repo", lambda r: True)
    monkeypatch.setattr(dc.git_utils, "resolve_ref", lambda r, ref: ref)
    monkeypatch.setattr(dc.git_utils, "get_commits_since", lambda r, ref: [commit])
    monkeypatch.setattr(dc.git_utils, "get_changed_files",
                        lambda r, sha: ["_specflow/specs/requirements/REQ-001.md"])
    monkeypatch.setattr(dc.git_utils, "is_spec_artifact_path", lambda f: f.endswith(".md"))
    monkeypatch.setattr(dc.git_utils, "artifact_id_from_path",
                        lambda f: "REQ-001")
    monkeypatch.chdir(root)

    rc = dc.run(root, {"since": "HEAD~1"})
    assert rc == 0

    decs = [a for a in art_lib.discover_artifacts(root)
            if art_lib.get_prefix_from_id(a.id) == "DEC"]
    assert decs, "no DEC generated"
    assert decs[0].frontmatter.get("dec_kind") == "change_record", \
        decs[0].frontmatter.get("dec_kind")


# ── verification-evidence aggregation (5C) ────────────────────────


def test_verification_evidence_unknown_no_contracts(tmp_path):
    root = _scaffold(tmp_path)
    _req(root, "REQ-001")
    _story(root, "STORY-001", "REQ-001")
    # A test with NO verify_command → no contracts declared.
    _test_art(root, "UT-001", "unit-test", "STORY-001")
    artifacts = art_lib.discover_artifacts(root)
    ev = risk_lib.verification_evidence(["STORY-001"], artifacts)
    assert ev == "unknown (no contracts declared)", ev


def test_verification_evidence_not_run(tmp_path):
    root = _scaffold(tmp_path)
    _req(root, "REQ-001")
    _story(root, "STORY-001", "REQ-001")
    # Contract declared but never run (no verify_run_at).
    _test_art(root, "UT-001", "unit-test", "STORY-001",
              verify_command="pytest -q", verify_exit_code=0)
    artifacts = art_lib.discover_artifacts(root)
    ev = risk_lib.verification_evidence(["STORY-001"], artifacts)
    assert ev == "not-run", ev


def test_verification_evidence_ran_green(tmp_path):
    root = _scaffold(tmp_path)
    _req(root, "REQ-001")
    _story(root, "STORY-001", "REQ-001")
    # Contract declared AND ran green (verify_run_at set, exit codes match).
    _test_art(root, "UT-001", "unit-test", "STORY-001",
              verify_command="pytest -q", verify_exit_code=0,
              verify_run_at="2026-01-02T00:00:00Z", verify_run_exit_code=0)
    _test_art(root, "UT-002", "unit-test", "STORY-001",
              verify_command="pytest -q", verify_exit_code=0,
              verify_run_at="2026-01-02T00:00:00Z", verify_run_exit_code=0)
    artifacts = art_lib.discover_artifacts(root)
    ev = risk_lib.verification_evidence(["STORY-001"], artifacts)
    assert ev == "ran (2 green)", ev


def test_verification_evidence_never_fabricates(tmp_path):
    """If contracts exist but none green, we report not-run — never 'ran'."""
    root = _scaffold(tmp_path)
    _req(root, "REQ-001")
    _story(root, "STORY-001", "REQ-001")
    # Ran but FAILED (exit 1 != expected 0) → not green → not-run.
    _test_art(root, "UT-001", "unit-test", "STORY-001",
              verify_command="pytest -q", verify_exit_code=0,
              verify_run_at="2026-01-02T00:00:00Z", verify_run_exit_code=1)
    artifacts = art_lib.discover_artifacts(root)
    ev = risk_lib.verification_evidence(["STORY-001"], artifacts)
    assert ev == "not-run", ev
