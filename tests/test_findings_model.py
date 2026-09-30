"""Typed findings (STORY-704, REQ-053 AC3/AC4) — unit level."""

from __future__ import annotations

from pathlib import Path

import pytest

from specflow.commands import artifact_lint as lint_cmd
from specflow.commands import init as init_cmd
from specflow.core import findings as fnd
from specflow.core.policy import ACCOUNTING_RULES, klass_for
from specflow.lib import artifacts as art_lib

REPO = Path(__file__).resolve().parents[1]


def test_key_excludes_args_and_text():
    a = fnd.make("links/orphan", ("STORY-1",), "warning", text="x", count=1)
    b = fnd.make("links/orphan", ("STORY-1",), "warning", text="y", count=9)
    assert a.key == b.key == ("links/orphan", ("STORY-1",))
    assert a != b, "args are part of equality (AC1), not of the key"


def test_class_comes_from_policy_table():
    assert fnd.make("quality/text", ("REQ-1", "x"), "warning").klass == "accounting"
    assert fnd.make("spike-lifecycle/stale", ("SPIKE-1",), "warning").klass == "accounting"
    assert fnd.make("spike-lifecycle/zombie", ("SPIKE-1",), "warning").klass == "escalating"
    assert fnd.make("links/orphan", ("STORY-1",), "warning").klass == "escalating"


def test_unknown_severity_rejected():
    with pytest.raises(ValueError):
        fnd.make("links/orphan", ("X",), "fatal")


def test_accounting_rules_name_real_checks():
    for rule in ACCOUNTING_RULES:
        assert rule.split("/", 1)[0] in lint_cmd.CHECK_NAMES, rule


def test_audit_adapter_shares_the_accounting_table():
    from specflow.commands.project_audit import _ACCOUNTING_CONCERNS

    for concern in _ACCOUNTING_CONCERNS:
        f = fnd.from_audit_dict({"severity": "warn", "concern": concern, "message": "REQ-001: x"})
        assert f.klass == "accounting" and f.subjects == ("REQ-001",)
    structural = fnd.from_audit_dict({"severity": "warn", "concern": "completeness", "message": "gap"})
    assert structural.klass == "escalating"
    # A category never makes an audit finding accounting — only a concern does.
    by_category = fnd.from_audit_dict({"severity": "warn", "category": "verification", "message": "m"})
    assert klass_for(by_category.rule_id) == "escalating"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "p"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    return root


def _story(root: Path, sid: str, body: str, output_files: list[str] | None = None) -> None:
    import yaml

    fm = {"id": sid, "title": sid, "type": "story", "status": "draft", "links": []}
    if output_files:
        fm["output_files"] = output_files
    path = root / "_specflow" / "work" / "stories" / f"{sid}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{yaml.safe_dump(fm)}---\n\n{body}\n", encoding="utf-8")


def test_two_problems_on_one_artifact_are_two_keys(project: Path):
    """AC2 of STORY-704: a discriminator subject separates distinct problems."""
    _story(project, "STORY-001", "## Acceptance Criteria\n\n1. a\n2. b",
           output_files=["src/missing_a.py", "src/missing_b.py"])
    arts = art_lib.discover_artifacts(project)
    result = lint_cmd._run_check(arts, project, "output-files")
    keys = {f.key for f in result["findings"]}
    assert keys == {
        ("output-files/missing", ("STORY-001", "src/missing_a.py")),
        ("output-files/missing", ("STORY-001", "src/missing_b.py")),
    }
    links = lint_cmd._run_check(arts, project, "links")
    assert ("links/orphan", ("STORY-001",)) in {f.key for f in links["findings"]}


def _assert_parity(root: Path) -> None:
    arts = art_lib.discover_artifacts(root)
    for name in lint_cmd.CHECK_NAMES:
        result = lint_cmd._run_check(arts, root, name)
        got = fnd.counts(result.get("findings", []))
        assert got == (result["blocking_count"], result["warning_count"]), name
        for f in result.get("findings", []):
            assert f.rule_id.split("/", 1)[0] in lint_cmd.CHECK_NAMES, f.rule_id
            assert f.subjects, f.rule_id


def test_finding_counts_match_counters_on_fixture(project: Path):
    """AC1 of STORY-704 (test-only invariant; no runtime assert)."""
    _story(project, "STORY-001", "no ac section", output_files=["src/nope.py"])
    _story(project, "STORY-002", "## Acceptance Criteria\n\n1. only one")
    _assert_parity(project)


def test_finding_counts_match_counters_on_this_repo():
    """The dogfood corpus exercises most checks; parity must hold there too."""
    _assert_parity(REPO)
