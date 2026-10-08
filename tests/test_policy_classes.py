"""Staged and lean-path finding classes (STORY-716 AC1/AC2, DEC-095 amending
DEC-099): pre-implementation test-linkage rows are accounting, a
STORY that claims implemented without tests escalates, keys never move."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from specflow.commands import artifact_lint as lint_cmd
from specflow.commands import init as init_cmd
from specflow.core import policy
from specflow.core.findings import make

# (rule, subject_status, expected class) — the single truth table.
TRUTH_TABLE = [
    ("coverage/no-test", None, "accounting"),
    ("coverage/no-test", "draft", "accounting"),
    ("coverage/no-test", "approved", "accounting"),
    ("coverage/no-test", "implemented", "escalating"),
    ("coverage/no-test", "verified", "escalating"),
    ("links/missing-v-pair", "approved", "accounting"),
    ("links/missing-v-pair", "implemented", "escalating"),
    ("links/missing-v-pair", "verified", "escalating"),
    ("bp-application/no-test", None, "accounting"),
    ("bp-application/no-test", "implemented", "escalating"),
    ("wave-cycles/fan-in", "draft", "accounting"),
    ("wave-cycles/fan-in", "implemented", "accounting"),
    ("wave-cycles/cycle", None, "escalating"),
    ("story-size/ac-max", "approved", "accounting"),
    ("story-size/ac-min", None, "accounting"),
    ("story-size/no-ac", None, "accounting"),
    ("story-size/subsystems", None, "accounting"),
    ("coverage/no-story", "approved", "escalating"),
    ("coverage/no-arch", "approved", "escalating"),
    ("links/orphan", "implemented", "escalating"),
    ("thinking-techniques/unchallenged", "approved", "escalating"),
    ("quality/text", "implemented", "accounting"),
]


@pytest.mark.parametrize("rule,status,expected", TRUTH_TABLE)
def test_truth_table(rule: str, status: str | None, expected: str):
    assert policy.klass_for(rule, subject_status=status) == expected


def test_staged_rules_are_not_prefix_accounting():
    # The table stages exact rule ids; the check prefixes stay escalating
    # for their other rules (coverage/no-story, links/orphan).
    for rule in policy.STAGED_RULES:
        assert rule.partition("/")[0] in lint_cmd.CHECK_NAMES, rule
    assert policy.CLAIMED_STATUSES == frozenset({"implemented", "verified"})


def test_lean_path_only_for_no_arch():
    assert policy.klass_for("coverage/no-arch") == "escalating"
    assert policy.klass_for("coverage/no-arch", lean_path=True) == "accounting"
    assert policy.klass_for("coverage/no-story", lean_path=True) == "escalating"
    assert policy.klass_for("links/orphan", lean_path=True) == "escalating"


def test_classification_inputs_never_touch_key_or_args():
    approved = make("coverage/no-test", ("STORY-1", "UT", "REQ-1"), "warning", subject_status="approved")
    claimed = make("coverage/no-test", ("STORY-1", "UT", "REQ-1"), "warning", subject_status="implemented")
    assert approved.key == claimed.key
    assert approved.as_dict()["args"] == {} and claimed.as_dict()["args"] == {}
    assert (approved.klass, claimed.klass) == ("accounting", "escalating")
    lean = make("coverage/no-arch", ("REQ-1",), "warning", lean_path=True)
    assert lean.key == ("coverage/no-arch", ("REQ-1",)) and lean.as_dict()["args"] == {}


def test_decide_staged_row_blocks_only_when_claimed():
    approved = make("coverage/no-test", ("STORY-1", "UT", "REQ-1"), "warning", subject_status="approved")
    claimed = make("coverage/no-test", ("STORY-1", "UT", "REQ-1"), "warning", subject_status="implemented")
    assert policy.decide([approved], frozenset(), full_run=True).exit_code == 0
    verdict = policy.decide([claimed], frozenset(), full_run=True)
    assert verdict.exit_code == 1 and verdict.new == [claimed]
    # The key a baseline recorded while the STORY was approved still matches.
    assert policy.decide([claimed], frozenset({approved.key}), full_run=True).exit_code == 0


# ── Fresh-init scenarios (STORY-716 AC1/AC2) ───────────────────────────────


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "p"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    assert (root / ".specflow" / "findings-baseline.yaml").exists(), "init seeds an empty baseline"
    return root


def _write(root: Path, rel: str, fm: dict, body: str) -> Path:
    path = root / "_specflow" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{yaml.safe_dump(fm, sort_keys=False)}---\n\n{body}\n", encoding="utf-8")
    return path


_AC = "## Acceptance Criteria\n\n- [ ] AC1: Given a request, when it runs, then it returns 200.\n- [ ] AC2: Given bad input, when it runs, then it returns 400."


def _lean_project(root: Path, story_status: str) -> None:
    """One approved REQ realised directly by one STORY: no ARCH, no tests."""
    _write(root, "specs/requirements/REQ-001.md", {
        "id": "REQ-001", "title": "Serve the thing", "type": "requirement",
        "status": "approved", "created": "2026-10-01",
        "thinking_techniques": ["premortem"],
        "non_functional_category": "functional",
        "links": [],
    }, "# Serve the thing\n\nThe system **shall** serve the thing.\n\n" + _AC)
    _write(root, "work/stories/STORY-001.md", {
        "id": "STORY-001", "title": "Implement the thing", "type": "story",
        "status": story_status, "created": "2026-10-01",
        "links": [{"target": "REQ-001", "role": "implements"}],
    }, "# Implement the thing\n\n" + _AC)


def _new_keys(root: Path) -> set[tuple[str, tuple[str, ...]]]:
    from specflow.core import findings_baseline

    _results, findings = lint_cmd.collect(root, lint_cmd.CHECK_NAMES)
    baseline, err = findings_baseline.load(root)
    assert err is None
    verdict = policy.decide(findings, baseline, full_run=True)
    return {f.key for f in verdict.new}


@pytest.mark.parametrize("story_status", ["draft", "approved"])
def test_fresh_init_pre_implementation_passes_with_empty_baseline(project: Path, story_status: str, capsys):
    """AC1: nothing is claimed yet, so no-test / no-arch rows never gate."""
    _lean_project(project, story_status)
    assert lint_cmd.run(project, {}) == 0, capsys.readouterr().out
    out = capsys.readouterr().out
    assert "0 new" in out and "FAIL" not in out
    assert _new_keys(project) == set()


def test_story_implemented_without_tests_escalates(project: Path, capsys):
    """AC2: the STORY claims implemented with no UT/IT/QT → the rows escalate."""
    _lean_project(project, "implemented")
    assert lint_cmd.run(project, {}) == 1
    out = capsys.readouterr().out
    assert "[coverage/no-test] STORY-001 UT REQ-001" in out
    assert "new vs findings baseline" in out
    assert _new_keys(project) == {
        ("coverage/no-test", ("STORY-001", "UT", "REQ-001")),
        ("coverage/no-test", ("STORY-001", "IT", "REQ-001")),
        ("coverage/no-test", ("STORY-001", "QT", "REQ-001")),
    }


def test_lean_path_no_arch_row_prints_as_accounting(project: Path):
    _lean_project(project, "approved")
    results, findings = lint_cmd.collect(project, ["coverage"])
    no_arch = [f for f in findings if f.rule_id == "coverage/no-arch"]
    assert [f.subjects for f in no_arch] == [("REQ-001",)]
    assert no_arch[0].klass == "accounting"
    assert "no ARCH derives_from" in results[0][1]["detail"], "the row still prints"
    no_test = [f for f in findings if f.rule_id == "coverage/no-test"]
    assert len(no_test) == 3 and all(f.klass == "accounting" for f in no_test)


def test_req_with_no_story_keeps_escalating(project: Path):
    """From planning on, an approved REQ nobody has decomposed is debt."""
    from specflow.lib import learning

    _lean_project(project, "approved")
    (project / "_specflow" / "work" / "stories" / "STORY-001.md").unlink()
    assert learning.set_phase(project, "planning", "test")["ok"]
    assert ("coverage/no-story", ("REQ-001",)) in _new_keys(project)
    assert ("coverage/no-arch", ("REQ-001",)) in _new_keys(project), "no lean path without a STORY"


@pytest.mark.parametrize("phase", ["idle", "discovering"])
def test_req_with_no_story_is_accounting_before_planning(project: Path, phase: str, capsys):
    """DEC-095: between discover and plan an approved REQ with nothing
    downstream is the expected state, so its planning-gap rows never gate."""
    from specflow.lib import learning

    _lean_project(project, "approved")
    (project / "_specflow" / "work" / "stories" / "STORY-001.md").unlink()
    if phase != "idle":
        assert learning.set_phase(project, phase, "test")["ok"]
    assert lint_cmd.run(project, {}) == 0, capsys.readouterr().out
    _results, findings = lint_cmd.collect(project, ["coverage", "links"])
    rows = {f.rule_id: f.klass for f in findings if f.subjects == ("REQ-001",)}
    assert rows["coverage/no-story"] == "accounting", "the row still exists, as accounting"
    assert rows["links/orphan"] == "accounting"
    assert _new_keys(project) == set()


def test_pre_planning_only_stages_planning_gap_rules():
    assert policy.klass_for("links/orphan", pre_planning=True) == "accounting"
    assert policy.klass_for("coverage/no-story", pre_planning=True) == "accounting"
    assert policy.klass_for("coverage/no-story") == "escalating"
    assert policy.klass_for("coverage/no-test", subject_status="implemented", pre_planning=True) == "escalating", "staged rules ignore the phase"
    assert policy.klass_for("links/broken", pre_planning=True) == "escalating"


def test_missing_v_pair_is_staged_by_spec_status(project: Path):
    _lean_project(project, "approved")
    assert ("links/missing-v-pair", ("REQ-001", "QT")) not in _new_keys(project)
    path = project / "_specflow" / "specs" / "requirements" / "REQ-001.md"
    path.write_text(path.read_text(encoding="utf-8").replace("status: approved", "status: verified"), encoding="utf-8")
    assert ("links/missing-v-pair", ("REQ-001", "QT")) in _new_keys(project)
