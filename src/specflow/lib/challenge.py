"""Proactive challenge engine for edge case discovery."""

from __future__ import annotations

from specflow.lib.artifacts import Artifact
from specflow.lib.checklists import AssembledChecklist, ChecklistItem


def extract_proactive_items(assembled: AssembledChecklist) -> list[ChecklistItem]:
    """Filter assembled checklist for proactive challenge items."""
    severity_rank = {"blocking": 3, "warning": 2, "info": 1}
    items = [i for i in assembled.items if i.mode == "proactive"]
    return sorted(items, key=lambda i: severity_rank.get(i.severity, 0), reverse=True)


def format_proactive_prompt(
    artifact: Artifact,
    items: list[ChecklistItem],
) -> str:
    """Build a structured prompt for LLM to evaluate proactive challenges.

    This string is used by the skill, not executed by Python directly.
    """
    checks = "\n".join(
        f"  {i+1}. [{item.id}] {item.check}"
        + (f"\n     Hint: {item.llm_prompt}" if item.llm_prompt else "")
        for i, item in enumerate(items)
    )

    return f"""## Proactive Challenge Review

**Artifact**: {artifact.id} — "{artifact.title}"
**Type**: {artifact.type} | **Tags**: {artifact.tags}

### Artifact Content

{artifact.body}

### Proactive Checks

{checks}

### Instructions

For each check above:
1. Enumerate every relevant branching path:
   - What if input is null/empty/malformed?
   - What if an external system is slow/down/unavailable?
   - What if a user acts out of order?
2. Flag any path without a defined handling strategy.
3. Rate each finding as: blocking, warning, or info.

Respond with a structured list of findings.
"""
