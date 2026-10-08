"""Proactive challenge engine for edge case discovery.

``checklist-run --proactive`` lists each proactive item with its ``llm_prompt``
as a ``Hint:`` line; the host agent evaluates the hints itself (no prompt
string is built or executed here).
"""

from __future__ import annotations

from specflow.lib.checklists import AssembledChecklist, ChecklistItem


def extract_proactive_items(assembled: AssembledChecklist) -> list[ChecklistItem]:
    """Filter assembled checklist for proactive challenge items."""
    severity_rank = {"blocking": 3, "warning": 2, "info": 1}
    items = [i for i in assembled.items if i.mode == "proactive"]
    return sorted(items, key=lambda i: severity_rank.get(i.severity, 0), reverse=True)
