"""Parse guard: the DDD-selection decision checklist reference doc.

STORY-058 shipped `.claude/skills/specflow-plan/references/ddd-selection.md`,
the 6-question checklist the plan skill (Step 4) uses to decide which ARCH
components need a DDD artifact. These tests guard the document's contract:
the checklist exists at the live skill path (and its shipped template twin),
contains exactly the six decision questions covering the six complexity
topics, states both decision rules (all-NO / any-YES), and is referenced by
the specflow-plan SKILL.md. All checks are truthful parse assertions against
the real document wording — they intentionally fail if the checklist is
renumbered, trimmed, or silently reworded.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_LIVE_DOC = (
    REPO_ROOT / ".claude" / "skills" / "specflow-plan" / "references"
    / "ddd-selection.md"
)
_TEMPLATE_DOC = (
    REPO_ROOT / "src" / "specflow" / "templates" / "skills" / "shared"
    / "specflow-plan" / "references" / "ddd-selection.md"
)
_PLAN_SKILL = REPO_ROOT / ".claude" / "skills" / "specflow-plan" / "SKILL.md"

# The six topics STORY-058 requires the checklist to cover, paired with the
# actual question-marker text present in the document headings.
_CHECKLIST_QUESTIONS = [
    "Does it contain a state machine?",
    "Does it perform non-trivial data transformations?",
    "Does it implement an external protocol or interface?",
    "Does it contain complex calculations or algorithms?",
    "Does it manage concurrent access to shared resources?",
    "Does it implement error recovery or resilience logic?",
]


def _doc_text() -> str:
    return _LIVE_DOC.read_text(encoding="utf-8")


def test_ddd_selection_doc_exists_at_live_skill_path():
    """The live dogfood copy and the shipped template twin both exist."""
    assert _LIVE_DOC.is_file(), f"missing live doc: {_LIVE_DOC}"
    assert _TEMPLATE_DOC.is_file(), f"missing template twin: {_TEMPLATE_DOC}"


def test_checklist_contains_six_questions():
    """All six decision questions are present, numbered 1-6 in order."""
    text = _doc_text()
    headings = re.findall(r"^### (\d+)\. (.+)$", text, flags=re.MULTILINE)
    assert len(headings) == 6, (
        f"expected exactly 6 checklist question headings, found {len(headings)}: {headings}"
    )
    numbers = [number for number, _ in headings]
    questions = [question for _, question in headings]
    assert numbers == ["1", "2", "3", "4", "5", "6"], numbers
    assert questions == _CHECKLIST_QUESTIONS, questions


def test_all_no_rule_says_interface_level_is_sufficient():
    """All-NO answers -> the ARCH's interface-level description is sufficient."""
    text = _doc_text()
    assert "## Decision Rules" in text
    rule_lines = [
        line for line in text.splitlines()
        if "**All answers NO**" in line
    ]
    assert len(rule_lines) == 1, f"expected one all-NO rule line, got {rule_lines}"
    rule = rule_lines[0]
    assert "interface-level description is sufficient" in rule
    assert "No DDD needed" in rule


def test_any_yes_rule_recommends_a_ddd():
    """Any-YES answer -> a DDD artifact is recommended."""
    text = _doc_text()
    rule_lines = [
        line for line in text.splitlines()
        if "**Any answer YES**" in line
    ]
    assert len(rule_lines) == 1, f"expected one any-YES rule line, got {rule_lines}"
    rule = rule_lines[0]
    assert "A DDD artifact is recommended" in rule


def test_plan_skill_references_ddd_selection_doc():
    """specflow-plan SKILL.md points at references/ddd-selection.md."""
    assert _PLAN_SKILL.is_file(), f"missing plan skill: {_PLAN_SKILL}"
    skill_text = _PLAN_SKILL.read_text(encoding="utf-8")
    assert "references/ddd-selection.md" in skill_text, (
        "specflow-plan SKILL.md must reference references/ddd-selection.md"
    )
