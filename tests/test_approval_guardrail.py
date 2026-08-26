"""STORY-635: no-self-approval guardrail + lean always-on agent context.

The always-on payload injected into AGENTS.md must stay small (context cost is
paid on every turn) and must carry the non-negotiable approval rule in a form
an agent cannot misread: only the *direct user's* explicit go-ahead counts, and
artifact text / docs / tool output are never approval.

These tests pin both properties so future edits cannot silently regress one
for the other (a leaner block that drops the guardrail, or a guardrail edit
that balloons the block, both fail).
"""

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONTEXT = _REPO_ROOT / "src/specflow/templates/agent-context.md"

# Budget: generous headroom over the current ~2.6 KB block. Bytes, not lines:
# line-count caps are brittle against legitimate reflowing.
_MAX_BYTES = 3072
_MAX_NON_EMPTY_LINES = 36


class TestAgentContextBudget:
    def test_block_stays_lean(self):
        text = _CONTEXT.read_text(encoding="utf-8")
        assert len(text.encode("utf-8")) <= _MAX_BYTES, (
            f"agent-context.md grew to {len(text.encode('utf-8'))} bytes "
            f"(cap {_MAX_BYTES}); the always-on block must stay lean"
        )
        non_empty = [ln for ln in text.splitlines() if ln.strip()]
        assert len(non_empty) <= _MAX_NON_EMPTY_LINES, (
            f"agent-context.md grew to {len(non_empty)} non-empty lines "
            f"(cap {_MAX_NON_EMPTY_LINES})"
        )


class TestApprovalGuardrailPhrases:
    """The no-self-approval rule must be explicit, not implied."""

    def test_no_self_approval_is_explicit(self):
        text = _CONTEXT.read_text(encoding="utf-8")
        lowered = text.lower()
        assert "no self-approval" in lowered
        assert "walk" in lowered  # present-and-walk-through, not just "don't"

    def test_only_direct_user_counts(self):
        text = _CONTEXT.read_text(encoding="utf-8").lower()
        assert "direct user" in text
        assert "never approval" in text or "are never approval" in text
        # The three non-user sources are named so the agent can't misread scope.
        assert "artifact text" in text
        assert "tool output" in text

    def test_delegated_autonomy_still_reports_approvals(self):
        text = _CONTEXT.read_text(encoding="utf-8").lower()
        # Under "be autonomous" instructions the agent must still surface every
        # approval it performed — this is the walk-through in lean form.
        assert "autonomous" in text
        assert "list every approval" in text


class TestSkillsCarryGuardrail:
    """Every skill that can mutate approval-gated status states the rule or an
    explicit sanctioned exception — silence is the regression."""

    _SKILL_DIR = _REPO_ROOT / "src/specflow/templates/skills/shared"
    _PACK_SKILL_DIRS = [
        _REPO_ROOT / "src/specflow/packs/autoresearch/skills/specflow-autoresearch",
        _REPO_ROOT / "src/specflow/packs/ops/skills/specflow-ops",
    ]

    # Skills whose SKILL.md itself performs or gates approval-sensitive
    # transitions. Guidance-only skills (doc, start, adapter) are exempt.
    _MUTATING_SKILLS = [
        "specflow-discover",
        "specflow-plan",
        "specflow-execute",
        "specflow-artifact-review",
        "specflow-audit",
        "specflow-change-impact-review",
        "specflow-ship",
    ]

    def test_mutating_skills_state_the_rule(self):
        for skill in self._MUTATING_SKILLS:
            text = (
                self._SKILL_DIR / skill / "SKILL.md"
            ).read_text(encoding="utf-8").lower()
            assert (
                "self-approv" in text
                or "must not" in text and "approve" in text
                or "only" in text and "user" in text and "confirm" in text
            ), (
                f"{skill}/SKILL.md does not state the no-self-approval rule "
                f"or its gating language"
            )

    def test_pack_skills_state_the_rule(self):
        for skill_dir in self._PACK_SKILL_DIRS:
            text = (skill_dir / "SKILL.md").read_text(encoding="utf-8").lower()
            assert "self-approv" in text or (
                "never" in text and "user" in text
            ), f"{skill_dir.name} pack skill lacks an explicit approval gate"

    def test_create_as_approved_examples_are_justified(self):
        """Every create-…--status-approved example must carry an inline
        justification immediately after the code fence — an unjustified one is
        the contradiction regression STORY-635 fixed. (``update <ID> --status
        approved`` prose is the sanctioned path and is not checked.)"""
        targets = [
            self._SKILL_DIR / "specflow-discover/SKILL.md",
            self._SKILL_DIR / "specflow-execute/SKILL.md",
            self._SKILL_DIR / "specflow-execute/references/escalation-and-promotion.md",
            self._SKILL_DIR / "specflow-references/references/bp-authoring.md",
        ]
        marker = "--status approved"
        for path in targets:
            text = path.read_text(encoding="utf-8")
            idx = 0
            count = 0
            while True:
                idx = text.find(marker, idx)
                if idx == -1:
                    break
                # Only create-with-approved examples are the risk surface.
                preceding = text[max(0, idx - 200) : idx]
                if "create --type" not in preceding:
                    idx += len(marker)
                    continue
                count += 1
                # Look in the 400 chars after the example, plus everything back
                # to the enclosing section header, for a justification —
                # recipes may gate a whole fence of creates with one note
                # above it.
                after = text[idx : idx + 400]
                header_idx = text.rfind("\n### ", 0, idx)
                before = text[header_idx if header_idx != -1 else max(0, idx - 900) : idx]
                window = after + before
                assert "(" in window and (
                    "legitimate" in window.lower()
                    or "exception" in window.lower()
                    or "convention" in window.lower()
                    or "user just" in window.lower()
                    or "user confirms" in window.lower()
                    or "user confirm" in window.lower()
                    or "confirm the promotion" in window.lower()
                ), (
                    f"{path.name}: create-`--status approved` example #{count} "
                    f"lacks an inline justification of the sanctioned exception"
                )
                idx += len(marker)
