"""Tests for AC observability accounting (specflow.lib.ac_quality) and its
surfaces in ``brief`` and ``project-audit`` (v1.13.1).

Coverage mandate (the anti-cry-wolf design is the whole point of this lens):
  - observable ACs (digit-bearing, Given/When/Then, file-creation verbs) → observable
  - vague ACs ("responds quickly", "handles errors gracefully", "is user-friendly") → aspirational
  - DOMAIN observables ("the relay energizes", "the bus arbitrates the channel")
    → UNCLASSIFIED, never aspirational — the cry-wolf guard tests, named as such
  - the conjunction is exercised explicitly
  - aggregate counts, the brief line (clean at zero aspirational), the audit
    block (info-only), and exit-code parity (accounting never escalates)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from specflow.commands import brief as brief_cmd
from specflow.commands import project_audit as audit_cmd
from specflow.lib import ac_quality as q
from specflow.lib import artifacts as art_lib


# ── helpers ──────────────────────────────────────────────────────────────

def _req(aid: str, body: str, status: str = "approved") -> art_lib.Artifact:
    return art_lib.Artifact(
        path=Path(f"/fake/{aid}.md"),
        frontmatter={"id": aid, "type": "requirement", "status": status},
        body=body,
        links=[],
    )


def _req_with_acs(aid: str, *items: str) -> art_lib.Artifact:
    body = "## Acceptance Criteria\n" + "\n".join(f"- {it}" for it in items) + "\n"
    return _req(aid, body)


# Brief-render tests need a real initialized project. Modeled on test_brief.py.
_STD_FLOW = {"draft": [], "approved": ["draft"], "implemented": ["approved"], "verified": ["implemented"]}


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    schema = {
        "type": "requirement", "prefix": "REQ",
        "allowed_status": dict(_STD_FLOW), "category": "spec",
    }
    (schema_dir / "requirement.yaml").write_text(yaml.dump(schema), encoding="utf-8")
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump({"project": {"name": "acq-test", "created": "2026-01-01"},
                   "artifact_types": ["requirement"], "active_packs": []}),
        encoding="utf-8",
    )
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "planning", "history": []}), encoding="utf-8",
    )
    (root / "_specflow" / "specs" / "requirements").mkdir(parents=True, exist_ok=True)
    return root


# ── per-item classification ──────────────────────────────────────────────


class TestObservableClassification:
    """Outcome-marker hits → observable (precision-first; these MUST classify
    observable so a real AC is never smeared aspirational)."""

    @pytest.mark.parametrize("text", [
        "returns exit code 0 on success",            # exit code + digit
        "the command exits with status 5",           # exits with + digit
        "returns the parsed JSON document",          # action verb + object
        "emits a `validated` event to the bus",      # emits + object
        "creates a file at /tmp/out.log",            # creates + object
        "writes the row to the database",            # writes + object
        "removes the temporary directory",           # removes + object
        "responds within 200 ms",                    # within + digit+unit
        "throughput is at least 1000 req/s",         # at least + digit + unit
        "latency under 50ms",                        # latency + digit + unit
        "raises a ValueError on malformed input",    # named exception
        "throws an exception when the socket closes",  # throws + exception
        "Given a logged-in user When they POST Then they receive a 201",  # GWT Then
        "the HTTP response status code is 404",      # http + status code
    ])
    def test_observable_markers(self, text):
        s = q.classify_ac_observability(_req_with_acs("REQ-X", text))
        assert s["observable"] == 1, f"expected observable for: {text!r}"
        assert s["aspirational"] == 0
        assert s["items"][0]["classification"] == "observable"

    def test_list_number_does_not_mask_aspirational(self):
        # A numbered list bullet ("1.") must NOT be read as a threshold digit.
        a = _req("REQ-X", "## Acceptance Criteria\n1. responds quickly\n2. is user-friendly\n")
        s = q.classify_ac_observability(a)
        assert s["observable"] == 0
        assert s["aspirational"] == 2

    def test_artifact_id_citation_does_not_mask_aspirational(self):
        # "see REQ-002" contains digits but is a citation, not a threshold.
        a = _req_with_acs("REQ-X", "is user-friendly (see REQ-002)")
        s = q.classify_ac_observability(a)
        assert s["aspirational"] == 1
        assert s["observable"] == 0


class TestAspirationalClassification:
    """Vague ACs → aspirational (conjunction: no outcome marker AND ambiguity
    word or bare vague verb)."""

    @pytest.mark.parametrize("text", [
        "responds quickly",            # ambiguity word "quickly"
        "handles errors gracefully",   # bare vague verb "handles"
        "is user-friendly",            # ambiguity word "user-friendly"
        "works correctly",             # bare verb "works" + ambiguity "correctly"
        "the system succeeds properly",  # bare verb "succeeds" + ambiguity "properly"
        "proceeds as expected",        # bare verb "proceeds" + ambiguity "as expected"
        "performs efficiently",        # ambiguity word "efficiently"
        "should be able to scale",     # ambiguity phrase "should be able to"
    ])
    def test_aspirational_markers(self, text):
        s = q.classify_ac_observability(_req_with_acs("REQ-X", text))
        assert s["aspirational"] == 1, f"expected aspirational for: {text!r}"
        assert s["observable"] == 0
        assert s["items"][0]["classification"] == "aspirational"


class TestCryWolfGuard:
    """THE anti-cry-wolf tests: legitimate DOMAIN observables that the lexicon
    cannot confirm must land UNCLASSIFIED — never aspirational. Flagging these
    as aspirational would discredit the whole lens (the #1 risk of v1.13.1)."""

    @pytest.mark.parametrize("text", [
        "the relay energizes",
        "the bus arbitrates the channel",
        "the valve opens when pressure exceeds nominal",
        "the actuator extends to the home position",
        "the kernel schedules the task",
    ])
    def test_domain_observable_is_unclassified_not_aspirational(self, text):
        s = q.classify_ac_observability(_req_with_acs("REQ-X", text))
        cls = s["items"][0]["classification"]
        assert cls == "unclassified", (
            f"CRY-WOLF: domain observable {text!r} classified {cls!r}; "
            f"must be 'unclassified', never 'aspirational'"
        )
        assert s["aspirational"] == 0
        assert s["observable"] == 0
        assert s["unclassified"] == 1

    def test_conjunction_explicit_bare_verb_with_outcome_is_observable(self):
        # The conjunction guardrail: a bare vague verb + a real outcome is
        # OBSERVABLE, not aspirational — the outcome marker wins.
        # "handles errors by writing /var/log/err.log" → writes + object.
        s = q.classify_ac_observability(_req_with_acs("REQ-X", "handles errors by writing /var/log/err.log"))
        assert s["observable"] == 1
        assert s["aspirational"] == 0

    def test_conjunction_explicit_ambiguity_word_with_outcome_is_observable(self):
        # "quickly" is an ambiguity word, but "within 100ms" is an outcome.
        s = q.classify_ac_observability(_req_with_acs("REQ-X", "responds quickly, within 100ms"))
        assert s["observable"] == 1
        assert s["aspirational"] == 0

    def test_inline_code_token_not_read_as_bare_verb(self):
        # A category label `` `work` `` in backticks is an identifier, not the
        # bare verb "work" — must NOT trip the aspirational lexicon (mirrors
        # the _STRIP_CODE convention in artifact_lint._check_quality).
        s = q.classify_ac_observability(
            _req_with_acs("REQ-X", "Default categories: `spec`, `work`, `review`")
        )
        # No outcome marker, no ambiguity word, no bare verb (work is in code).
        assert s["items"][0]["classification"] == "unclassified"
        assert s["aspirational"] == 0

    def test_inline_code_outcome_still_detected(self):
        # Backtick content is kept VISIBLE for observable detection — the
        # outcome signal often lives in code (`` `exit code 0` ``).
        s = q.classify_ac_observability(_req_with_acs("REQ-X", "returns `exit code 0`"))
        assert s["observable"] == 1


# ── aggregate ────────────────────────────────────────────────────────────


class TestAggregate:
    def _project(self):
        return [
            _req_with_acs("REQ-001", "returns exit code 0", "creates a file"),     # 2 obs
            _req_with_acs("REQ-002", "responds quickly", "is user-friendly"),      # 2 asp
            _req_with_acs("REQ-003", "the relay energizes"),                       # 1 unclass
            _req("REQ-004", "# no AC section here\n"),                             # 0 items
            art_lib.Artifact(path=Path("ARCH-1.md"),
                             frontmatter={"id": "ARCH-001", "type": "architecture", "status": "approved"},
                             body="", links=[]),                                   # non-REQ
        ]

    def test_counts(self):
        agg = q.classify_reqs_observability(self._project())
        assert agg["reqs_with_acs"] == 3                 # REQ-004 has 0 ACs, excluded
        assert agg["total_items"] == 5
        assert agg["observable"] == 2
        assert agg["aspirational"] == 2
        assert agg["unclassified"] == 1
        assert agg["aspirational_free_reqs"] == 2        # REQ-001, REQ-003
        assert agg["aspirational_reqs"] == 1             # REQ-002
        assert agg["aspirational_texts"] == ["responds quickly", "is user-friendly"]

    def test_per_req_ratio(self):
        agg = q.classify_reqs_observability(self._project())
        by_id = {r["id"]: r for r in agg["per_req"]}
        assert by_id["REQ-001"]["observable_ratio"] == 1.0
        assert by_id["REQ-002"]["observable_ratio"] == 0.0
        assert by_id["REQ-003"]["observable_ratio"] == 0.0  # 0 obs / 1 unclassified

    def test_non_req_artifact_summary_is_zeroed(self):
        arch = art_lib.Artifact(
            path=Path("ARCH-1.md"),
            frontmatter={"id": "ARCH-001", "type": "architecture", "status": "approved"},
            body="## Acceptance Criteria\n- returns 0\n", links=[],
        )
        s = q.classify_ac_observability(arch)
        # Works on any artifact with an AC section; is_requirement reflects type.
        assert s["is_requirement"] is False
        assert s["observable"] == 1


# ── lint callable (the wiring contract for artifact_lint) ────────────────


class TestLintCallable:
    """``lint_ac_observability`` returns the check-summary shape that
    ``artifact_lint._run_check`` dispatches; tests against the callable directly
    (the CHECK_NAMES registration is the orchestrator's one-line wiring)."""

    def test_non_blocking_always(self):
        arts = [_req_with_acs("REQ-001", "responds quickly", "is user-friendly")]
        result = q.lint_ac_observability(arts)
        assert result["blocking_count"] == 0
        assert result["warning_count"] == 1          # 1 REQ with aspirational ACs
        assert "REQ-001" in result["detail"]

    def test_clean_when_no_aspirational(self):
        arts = [_req_with_acs("REQ-001", "returns exit code 0", "creates a file")]
        result = q.lint_ac_observability(arts)
        assert result["blocking_count"] == 0
        assert result["warning_count"] == 0
        assert "free of aspirational" in result["detail"]

    def test_req_level_not_per_ac(self):
        # Multiple aspirational ACs on ONE REQ → warning_count == 1 (REQ-level),
        # not N per-AC warns (the cry-wolf-avoidance shape).
        arts = [_req_with_acs("REQ-001", "responds quickly", "is user-friendly", "works correctly")]
        result = q.lint_ac_observability(arts)
        assert result["warning_count"] == 1

    def test_returns_required_keys(self):
        result = q.lint_ac_observability([])
        for key in ("status_icon", "detail", "blocking_count", "warning_count"):
            assert key in result


# ── brief surface ────────────────────────────────────────────────────────


class TestBriefAcQualityLine:
    def test_summary_carries_ac_quality(self, tmp_path):
        arts = [_req_with_acs("REQ-001", "responds quickly")]
        s = brief_cmd._knowledge_summary(tmp_path, arts)
        assert s["ac_quality"]["aspirational"] == 1
        assert s["ac_quality"]["reqs_with_acs"] == 1
        assert s["ac_quality"]["aspirational_free_reqs"] == 0

    def test_clean_line_at_zero_aspirational(self, tmp_path):
        # Zero aspirational → the brief line is clean (no ⚠ marker).
        arts = [_req_with_acs("REQ-001", "returns exit code 0", "creates a file")]
        s = brief_cmd._knowledge_summary(tmp_path, arts)
        assert s["ac_quality"]["aspirational"] == 0

    def test_brief_renders_req_quality_line_when_aspirational(self, project_root, capsys):
        art_lib.create_artifact(
            project_root, "requirement", title="R1", status="approved",
            body="## Acceptance Criteria\n- responds quickly\n",
        )
        assert brief_cmd.run(project_root, {}) == 0
        out = capsys.readouterr().out
        assert "REQ quality:" in out
        assert "aspirational AC(s)" in out

    def test_brief_no_req_quality_line_when_no_reqs_with_acs(self, project_root, capsys):
        # No REQs with ACs → the line is omitted entirely (silent).
        assert brief_cmd.run(project_root, {}) == 0
        out = capsys.readouterr().out
        assert "REQ quality:" not in out


# ── project-audit surface ────────────────────────────────────────────────


class TestProjectAuditAcObservabilityLens:
    def test_concern_registered_accounting(self):
        assert "ac-observability" in audit_cmd._ACCOUNTING_CONCERNS

    def test_lens_emits_info_only_never_warn(self):
        # A REQ FULL of aspirational ACs → still INFO only (no per-AC warns).
        arts = [_req_with_acs("REQ-001", "responds quickly", "is user-friendly", "works correctly")]
        findings = audit_cmd._ac_observability_lens(arts)
        assert findings, "expected at least one finding"
        for f in findings:
            assert f["severity"] == "info", (
                f"CRY-WOLF: ac-observability emitted {f['severity']} — must be info-only"
            )
            assert f["concern"] == "ac-observability"

    def test_lens_reports_per_req_ratio(self):
        arts = [_req_with_acs("REQ-001", "returns 0", "responds quickly")]
        findings = audit_cmd._ac_observability_lens(arts)
        per_req = [f for f in findings if "REQ-001:" in f["message"]]
        assert per_req
        msg = per_req[0]["message"]
        assert "1/2 observable" in msg
        assert "1 aspirational" in msg

    def test_lens_silent_when_no_reqs_with_acs(self):
        # Zero REQs with ACs → no findings (graceful degradation, never a warn).
        assert audit_cmd._ac_observability_lens([]) == []
        no_ac = _req("REQ-001", "# no AC section\n")
        assert audit_cmd._ac_observability_lens([no_ac]) == []

    def test_cross_cutting_registers_block(self, tmp_path):
        arts = [_req_with_acs("REQ-001", "responds quickly")]
        cc = audit_cmd._cross_cutting_analysis(arts, tmp_path)
        assert "ac-observability" in cc
        assert all(f["severity"] == "info" for f in cc["ac-observability"])


# ── exit-code parity: accounting never escalates ─────────────────────────


class TestExitCodeParity:
    """A fixture project FULL of aspirational ACs must not change the audit
    exit code: the ac-observability lens is accounting (info-only + registered
    in ``_ACCOUNTING_CONCERNS``), so it can NEVER drive exit-2. Proves the
    accounting exclusion end-to-end."""

    @staticmethod
    def _assemble_findings(arts, root):
        h = audit_cmd._horizontal_analysis(arts)
        v = audit_cmd._vertical_analysis(arts)
        cc = audit_cmd._cross_cutting_analysis(arts, root)
        raw = []
        for tname, items in h.items():
            for it in items:
                it["axis"] = "horizontal"
                it["type"] = tname
                raw.append(it)
        for it in v:
            it["axis"] = "vertical"
            raw.append(it)
        for con, items in cc.items():
            for it in items:
                it["axis"] = "cross-cutting"
                it["concern"] = con
                raw.append(it)
        return raw

    def test_aspirational_fixture_contributes_zero_escalating_warns(self, tmp_path):
        # Every AC here is aspirational — if any leaked as a warn, this fails.
        arts = [
            _req_with_acs("REQ-001", "responds quickly", "is user-friendly"),
            _req_with_acs("REQ-002", "works correctly", "handles errors gracefully"),
        ]
        findings = self._assemble_findings(arts, tmp_path)
        # The ac-observability block exists and is info-only.
        ac_obs = [f for f in findings if f.get("concern") == "ac-observability"]
        assert ac_obs, "ac-observability lens should have fired"
        assert all(f["severity"] == "info" for f in ac_obs)
        # Exit gate: zero ESCALATING warns come from ac-observability.
        escalating, _ = audit_cmd._count_warns(findings)
        ac_obs_warns = [
            f for f in findings
            if f.get("concern") == "ac-observability" and f.get("severity") == "warn"
        ]
        assert ac_obs_warns == [], "ac-observability must emit zero warns"
        # Parity: stripping ALL ac-observability findings leaves escalating unchanged.
        without = [f for f in findings if f.get("concern") != "ac-observability"]
        esc_without, _ = audit_cmd._count_warns(without)
        assert esc_without == escalating

    def test_ac_observability_accounting_carve_out_is_sole_protection(self, tmp_path):
        # Even though the lens is info-only, prove the concern registration is
        # the structural guarantee: if a warn ever appeared under this concern,
        # the carve-out (not the info-severity alone) is what keeps it non-escalating.
        arts = [_req_with_acs("REQ-001", "responds quickly")]
        findings = self._assemble_findings(arts, tmp_path)
        # Synthesize a hypothetical warn under the concern and verify carve-out.
        synthetic = {"severity": "warn", "concern": "ac-observability",
                     "message": "hypothetical lens regression"}
        esc_protected, acc = audit_cmd._count_warns([synthetic])
        assert esc_protected == 0
        assert acc == 1
