"""Parse-guard tests for discovery→plan skill continuity — QT-028.

These tests verify that the shipped discover and plan skill files contain the
instructions required by QT-028's acceptance criteria. They are *structural
parse-guards*: they assert that specific behavioral instructions exist in the
skill markdown so that an agent following the skill will perform the expected
continuity behaviors.

QT-028 ACs:
  1. discover persists significant challenges as DEC artifacts.
  2. discover records inter-REQ derives_from links.
  3. discover exit message lists the approval command.
  4. plan reads project domain/tags and discovery DECs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Shipped skill templates are the source of truth for agent instructions.
_SKILLS_DIR = (
    Path(__file__).resolve().parent.parent
    / "src" / "specflow" / "templates" / "skills" / "shared"
)

_DISCOVER_SKILL = _SKILLS_DIR / "specflow-discover" / "SKILL.md"
_PLAN_SKILL = _SKILLS_DIR / "specflow-plan" / "SKILL.md"


@pytest.fixture(scope="module")
def discover_text() -> str:
    assert _DISCOVER_SKILL.exists(), f"Missing discover skill: {_DISCOVER_SKILL}"
    return _DISCOVER_SKILL.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def plan_text() -> str:
    assert _PLAN_SKILL.exists(), f"Missing plan skill: {_PLAN_SKILL}"
    return _PLAN_SKILL.read_text(encoding="utf-8")


class TestQT028AC1DiscoverPersistsChallengesAsDEC:
    """AC1: discover persists significant challenge results as DEC artifacts
    so they survive across sessions and are available to the plan skill."""

    def test_mentions_decision_artifact_creation(self, discover_text: str):
        """The skill must instruct creating DEC artifacts for significant findings."""
        assert "--type decision" in discover_text, (
            "Discover skill must instruct creating DEC artifacts via "
            "'specflow create --type decision'"
        )

    def test_dropped_requirement_pattern(self, discover_text: str):
        """Dropped requirements must be persisted as DEC with 'Dropped:' title."""
        assert "Dropped" in discover_text, (
            "Discover skill must cover the 'Dropped:' DEC pattern for dropped requirements"
        )

    def test_assumption_pattern(self, discover_text: str):
        """Assumptions must be persisted as DEC."""
        assert "Assumption" in discover_text, (
            "Discover skill must cover the 'Assumption:' DEC pattern"
        )

    def test_risk_pattern(self, discover_text: str):
        """Risks must be persisted as DEC."""
        assert "Risk" in discover_text, (
            "Discover skill must cover the 'Risk:' DEC pattern"
        )

    def test_mentions_plan_skill_consumption(self, discover_text: str):
        """The skill must explicitly state DECs are available to the plan skill."""
        assert "plan skill" in discover_text.lower(), (
            "Discover skill must state that DEC artifacts are available to the plan skill"
        )

    def test_significance_guard(self, discover_text: str):
        """Only significant findings should produce DECs (noise guard)."""
        assert "significant" in discover_text.lower(), (
            "Discover skill must guard DEC creation to significant findings only"
        )


class TestQT028AC2InterREQDerivesFrom:
    """AC2: inter-REQ dependencies shall be captured as derives_from links."""

    def test_mentions_derives_from_role(self, discover_text: str):
        """The skill must instruct using derives_from for inter-REQ dependencies."""
        assert "derives_from" in discover_text, (
            "Discover skill must instruct using 'derives_from' for inter-REQ dependencies"
        )

    def test_add_link_command(self, discover_text: str):
        """The skill must show the --add-link command for recording dependencies."""
        assert "--add-link" in discover_text, (
            "Discover skill must show 'specflow update <REQ> --add-link <REQ>:derives_from'"
        )

    def test_dependency_prompting(self, discover_text: str):
        """The skill must include dependency prompting step."""
        # The inter-REQ dependency section must exist
        assert "depend" in discover_text.lower(), (
            "Discover skill must include inter-REQ dependency prompting"
        )


class TestQT028AC3ExitListsApprovalCommand:
    """AC3: discover exit message shall state which requirements need approval
    and provide the command to approve them."""

    def test_exit_message_mentions_approval(self, discover_text: str):
        """The exit message must mention approval."""
        assert "approve" in discover_text.lower(), (
            "Discover skill exit message must mention approval"
        )

    def test_exit_message_has_approve_command(self, discover_text: str):
        """The exit message must contain the specflow approve command."""
        assert "specflow approve" in discover_text.lower(), (
            "Discover skill exit message must contain 'specflow approve' command"
        )

    def test_exit_message_mentions_draft_status(self, discover_text: str):
        """The exit message must state that REQs are in draft status."""
        assert "draft" in discover_text.lower(), (
            "Discover skill must inform that REQs are in draft status pending approval"
        )

    def test_exit_message_mentions_plan_skill(self, discover_text: str):
        """The exit message must point at /specflow-plan as the next step."""
        assert "specflow-plan" in discover_text, (
            "Discover skill exit message must point at /specflow-plan"
        )


class TestQT028AC4PlanReadsDomainAndDECs:
    """AC4: plan skill shall consume domain classification, tags, and
    discovery DECs to scope its decomposition approach."""

    def test_reads_domain_from_config(self, plan_text: str):
        """Plan skill must read project.domain from config."""
        assert "project.domain" in plan_text or "project.domain" in plan_text, (
            "Plan skill must instruct reading project.domain from .specflow/config.yaml"
        )

    def test_reads_domain_tags(self, plan_text: str):
        """Plan skill must read domain_tags from config."""
        assert "domain_tags" in plan_text, (
            "Plan skill must instruct reading project.domain_tags"
        )

    def test_loads_decision_artifacts(self, plan_text: str):
        """Plan skill must load DEC artifacts created during discovery."""
        assert "decision" in plan_text.lower(), (
            "Plan skill must instruct loading decision artifacts from _specflow/work/decisions/"
        )

    def test_mentions_discovery_decs_specifically(self, plan_text: str):
        """Plan skill must reference DECs produced by the discover skill."""
        # The plan skill must reference discovery-produced DECs
        assert "discovery" in plan_text.lower() or "discover" in plan_text.lower(), (
            "Plan skill must reference decision artifacts created during discovery"
        )

    def test_uses_domain_checklist_concept_map(self, plan_text: str):
        """Plan skill must apply the domain checklist concept→artifact map."""
        assert "domain-checklists" in plan_text or "concept" in plan_text.lower(), (
            "Plan skill must reference domain checklist concept→artifact map"
        )
