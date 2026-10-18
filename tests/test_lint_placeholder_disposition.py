"""STORY-741 / REQ-067 OBL-4/5 (AC8-AC10) — ledger-hygiene accounting rules.

- ``placeholder/unfilled``: an artifact past ``draft`` whose body (code
  stripped) still carries ``generate_tests.PLACEHOLDER_TEST_CASES``.
- ``challenge/disposition-without-reason``: an ``accepted`` CHL, touched on or
  after the challenge schema's ``resolution_since``, with no ``resolution``.

Both are dedicated, warning-only, accounting checks: they never flip an exit
code (lint or project-audit).
"""

from __future__ import annotations

import contextlib
import io
from datetime import date
from pathlib import Path

import pytest
import yaml

from specflow import cli
from specflow.commands import artifact_lint as lint_cmd
from specflow.commands import generate_tests as gen_cmd
from specflow.commands import init as init_cmd
from specflow.commands.generate_tests import PLACEHOLDER_TEST_CASES
from specflow.core import policy
from specflow.core.policy import klass_for
from specflow.lib import artifacts as art_lib

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _restore_type_registry():
    dirs = dict(art_lib.TYPE_TO_DIR)
    prefixes = dict(art_lib.TYPE_TO_PREFIX)
    reverse = dict(art_lib.PREFIX_TO_TYPE)
    aliases = dict(art_lib.TYPE_ALIASES)
    yield
    for live, snap in ((art_lib.TYPE_TO_DIR, dirs), (art_lib.TYPE_TO_PREFIX, prefixes),
                       (art_lib.PREFIX_TO_TYPE, reverse), (art_lib.TYPE_ALIASES, aliases)):
        live.clear()
        live.update(snap)


_TYPES = [
    ("requirement", "REQ", "specs/requirements"),
    ("unit-test", "UT", "specs/unit-tests"),
    ("qualification-test", "QT", "specs/qualification-tests"),
    ("challenge", "CHL", "specs/challenges"),
]
_FLOW = {"draft": [], "approved": ["draft"], "implemented": ["approved"],
         "verified": ["implemented"], "deprecated": ["draft", "approved", "implemented"]}
_CHL_FLOW = {"open": [], "addressed": ["open"], "accepted": ["open", "addressed"]}


def _project(tmp: Path, *, resolution_since: str | None = "2026-10-18") -> Path:
    root = tmp / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    for art_type, prefix, rel in _TYPES:
        schema: dict = {
            "type": art_type, "prefix": prefix, "directory": f"_specflow/{rel}",
            "allowed_status": dict(_CHL_FLOW if art_type == "challenge" else _FLOW),
            "allowed_link_roles": ["verified_by", "challenges"],
            "optional_fields": ["resolution", "severity", "technique", "modified"],
        }
        if art_type == "challenge" and resolution_since is not None:
            schema["resolution_since"] = resolution_since
        (schema_dir / f"{art_type}.yaml").write_text(yaml.dump(schema), encoding="utf-8")
    config = {"project": {"name": "hyg-test", "created": "2026-01-01"},
              "artifact_types": [t for t, _, _ in _TYPES], "active_packs": []}
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "idle", "history": []}), encoding="utf-8")
    return root


def _mk(root: Path, art_type: str, art_id: str, *, status: str, body: str = "Body.",
        created: str = "2026-10-18", **extra) -> None:
    rel = {t: r for t, _, r in _TYPES}[art_type]
    path = root / "_specflow" / rel / f"{art_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = {"id": art_id, "title": art_id, "type": art_type, "status": status,
          "tags": [], "suspect": False, "links": [], "created": created, **extra}
    path.write_text(f"---\n{yaml.dump(fm, sort_keys=False)}---\n\n{body}\n", encoding="utf-8")


def _check(root: Path, name: str) -> dict:
    return lint_cmd._run_check(art_lib.discover_artifacts(root), root, name)


def _rule_subjects(result: dict, rule_id: str) -> list[tuple[str, ...]]:
    return [f.subjects for f in result["findings"] if f.rule_id == rule_id]


_PLACEHOLDER_LINE = f"## Test Cases\n\n- [ ] {PLACEHOLDER_TEST_CASES}\n"


# ── placeholder/unfilled (AC8) ──────────────────────────────────────


class TestPlaceholderUnfilled:
    def test_registered(self):
        assert "placeholder" in lint_cmd.CHECK_NAMES

    def test_generator_writes_the_constant(self, tmp_path):
        """The rule matches the generator's single constant (OBL-4)."""
        root = _project(tmp_path)
        _mk(root, "requirement", "REQ-001", status="approved", body="No criteria here.")
        req = next(a for a in art_lib.discover_artifacts(root) if a.id == "REQ-001")
        stub = gen_cmd._build_test_body(req, "Qualification Test")
        assert f"- [ ] {PLACEHOLDER_TEST_CASES}" in stub
        # ...and the lint flags exactly that output once the stub moves on.
        _mk(root, "qualification-test", "QT-001", status="verified", body=stub)
        assert _check(root, "placeholder")["warning_count"] == 1

    def test_verified_spec_with_placeholder_warns_once(self, tmp_path):
        root = _project(tmp_path)
        _mk(root, "unit-test", "UT-001", status="verified",
            body=_PLACEHOLDER_LINE + f"\n- [ ] {PLACEHOLDER_TEST_CASES}\n")
        result = _check(root, "placeholder")
        assert result["warning_count"] == 1
        assert result["blocking_count"] == 0
        assert _rule_subjects(result, "placeholder/unfilled") == [("UT-001",)]
        assert "UT-001" in result["detail"]

    def test_fenced_or_inline_placeholder_is_not_flagged(self, tmp_path):
        root = _project(tmp_path)
        _mk(root, "unit-test", "UT-001", status="verified",
            body=f"## Example\n\n```\n- [ ] {PLACEHOLDER_TEST_CASES}\n```\n")
        _mk(root, "requirement", "REQ-001", status="approved",
            body=f"Specs still carry `{PLACEHOLDER_TEST_CASES}` today.")
        assert _check(root, "placeholder")["warning_count"] == 0

    @pytest.mark.parametrize("status", ["draft", "deprecated"])
    def test_draft_or_retired_is_not_flagged(self, tmp_path, status):
        root = _project(tmp_path)
        _mk(root, "unit-test", "UT-001", status=status, body=_PLACEHOLDER_LINE)
        assert _check(root, "placeholder")["warning_count"] == 0

    def test_real_cases_are_clean(self, tmp_path):
        root = _project(tmp_path)
        _mk(root, "unit-test", "UT-001", status="verified",
            body="## Test Cases\n\n- [ ] Given x, when y, then z\n")
        assert _check(root, "placeholder")["warning_count"] == 0

    def test_dogfood_repo_has_no_unfilled_placeholder(self):
        """AC11: the 20 legacy specs carry real test cases."""
        result = _check(REPO_ROOT, "placeholder")
        assert result["warning_count"] == 0, result["detail"]


# ── challenge/disposition-without-reason (AC9) ──────────────────────


class TestChallengeDisposition:
    def test_registered(self):
        assert "challenge" in lint_cmd.CHECK_NAMES

    def test_accepted_without_resolution_warns(self, tmp_path):
        root = _project(tmp_path)
        _mk(root, "challenge", "CHL-001", status="accepted")
        result = _check(root, "challenge")
        assert result["warning_count"] == 1
        assert result["blocking_count"] == 0
        assert _rule_subjects(result, "challenge/disposition-without-reason") == [("CHL-001",)]
        assert "specflow update CHL-001 --set resolution=" in result["detail"]

    @pytest.mark.parametrize("value", ["", "   "])
    def test_empty_resolution_warns(self, tmp_path, value):
        root = _project(tmp_path)
        _mk(root, "challenge", "CHL-001", status="accepted", resolution=value)
        assert _check(root, "challenge")["warning_count"] == 1

    def test_resolution_set_is_clean(self, tmp_path):
        root = _project(tmp_path)
        _mk(root, "challenge", "CHL-001", status="accepted",
            resolution="Trade-off judged acceptable: latency budget has headroom")
        assert _check(root, "challenge")["warning_count"] == 0

    def test_open_or_addressed_is_not_flagged(self, tmp_path):
        root = _project(tmp_path)
        _mk(root, "challenge", "CHL-001", status="open")
        _mk(root, "challenge", "CHL-002", status="addressed")
        assert _check(root, "challenge")["warning_count"] == 0

    def test_chl_older_than_resolution_since_is_history(self, tmp_path):
        root = _project(tmp_path)
        _mk(root, "challenge", "CHL-001", status="accepted",
            created="2026-04-01", modified="2026-10-17")
        assert _check(root, "challenge")["warning_count"] == 0

    def test_old_chl_modified_after_the_date_is_asked(self, tmp_path):
        """A legacy CHL disposed now (modified on/after the date) owes a reason."""
        root = _project(tmp_path)
        _mk(root, "challenge", "CHL-001", status="accepted",
            created="2026-04-01", modified="2026-10-18")
        assert _check(root, "challenge")["warning_count"] == 1

    def test_schema_key_moves_the_horizon(self, tmp_path):
        root = _project(tmp_path, resolution_since="2027-01-01")
        _mk(root, "challenge", "CHL-001", status="accepted", created="2026-12-31")
        assert _check(root, "challenge")["warning_count"] == 0

    def test_schema_without_key_falls_back_to_ship_date(self, tmp_path):
        """A consumer schema that predates the key uses the module constant."""
        root = _project(tmp_path, resolution_since=None)
        assert lint_cmd.CHALLENGE_RESOLUTION_SINCE == date(2026, 10, 18)
        _mk(root, "challenge", "CHL-001", status="accepted", created="2026-10-17")
        _mk(root, "challenge", "CHL-002", status="accepted", created="2026-10-18")
        result = _check(root, "challenge")
        assert _rule_subjects(result, "challenge/disposition-without-reason") == [("CHL-002",)]


# ── accounting: never flips an exit code (AC8/AC9 "warning") ─────────


@pytest.mark.parametrize(
    "rule_id", ["placeholder/unfilled", "challenge/disposition-without-reason"])
def test_rules_are_accounting(rule_id):
    assert klass_for(rule_id) == "accounting"
    assert klass_for(rule_id, subject_status="verified") == "accounting"


def _hygiene_only_project(tmp_path: Path) -> Path:
    root = _project(tmp_path)
    _mk(root, "unit-test", "UT-001", status="draft", body="## Test Cases\n\n- [ ] Given a\n")
    _mk(root, "qualification-test", "QT-001", status="verified", body=_PLACEHOLDER_LINE)
    _mk(root, "challenge", "CHL-001", status="accepted")
    return root


def test_full_lint_with_baseline_never_escalates(tmp_path, capsys):
    root = _hygiene_only_project(tmp_path)
    (root / ".specflow" / "findings-baseline.yaml").write_text("entries: []\n", encoding="utf-8")
    _, findings = lint_cmd.collect(root, lint_cmd.CHECK_NAMES, as_of=date(2026, 10, 18))
    ids = {f.rule_id: f.klass for f in findings}
    assert ids.get("placeholder/unfilled") == "accounting"
    assert ids.get("challenge/disposition-without-reason") == "accounting"
    # The full-run verdict against an empty baseline (ratchet on) never
    # counts either rule as new debt.
    verdict = policy.decide(findings, frozenset(), full_run=True)
    new_ids = {f.rule_id for f in verdict.new}
    assert "placeholder/unfilled" not in new_ids
    assert "challenge/disposition-without-reason" not in new_ids
    for name in ("placeholder", "challenge"):
        assert lint_cmd.run(root, {"type": name}) == 0
    capsys.readouterr()


def test_project_audit_stays_green(tmp_path):
    from specflow.commands import project_audit as pa

    root = _hygiene_only_project(tmp_path)
    assert _check(root, "placeholder")["warning_count"] == 1
    assert _check(root, "challenge")["warning_count"] == 1
    assert pa.run(root, {"dry_run": True}) == 0


# ── the shipped schema + the skill's disposition command (AC5, OBL-5) ─


def test_shipped_challenge_schemas_identical_and_offer_resolution():
    live = REPO_ROOT / ".specflow" / "schema" / "challenge.yaml"
    shipped = REPO_ROOT / "src" / "specflow" / "templates" / "schemas" / "challenge.yaml"
    assert live.read_bytes() == shipped.read_bytes()
    schema = yaml.safe_load(shipped.read_text(encoding="utf-8"))
    assert "resolution" in schema["optional_fields"]
    assert str(schema["resolution_since"]) == "2026-10-18"


def _cli(*argv: str) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cli.main(list(argv))
    return code, buf.getvalue()


def test_disposition_command_records_resolution(tmp_path, monkeypatch):
    """The artifact-review report step's command works against the shipped schema
    and clears the finding."""
    root = tmp_path / "proj"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    monkeypatch.chdir(root)
    code, out = _cli("create", "--type", "challenge", "--title", "Latency risk",
                     "--set", "severity=warning", "--set", "technique=pre_mortem")
    assert code == 0, out
    chl = next(a for a in art_lib.discover_artifacts(root) if a.type == "challenge")
    code, out = _cli("update", chl.id, "--status", "addressed")
    assert code == 0, out
    assert _check(root, "challenge")["warning_count"] == 0
    # The exact one-call command the artifact-review report step prints.
    code, out = _cli("update", chl.id, "--status", "accepted",
                     "--set", "resolution=Budget has headroom")
    assert code == 0, out
    chl = next(a for a in art_lib.discover_artifacts(root) if a.id == chl.id)
    assert chl.frontmatter.get("resolution") == "Budget has headroom"
    assert _check(root, "challenge")["warning_count"] == 0
    code, out = _cli("schema", "challenge")
    assert code == 0 and "resolution" in out
