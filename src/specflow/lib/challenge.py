"""Proactive challenge engine for edge case discovery."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from specflow.lib.artifacts import Artifact, create_artifact, resolve_link_target
from specflow.lib.checklists import AssembledChecklist, ChecklistItem


def extract_proactive_items(assembled: AssembledChecklist) -> list[ChecklistItem]:
    """Filter assembled checklist for proactive challenge items."""
    severity_rank = {"blocking": 3, "warning": 2, "info": 1}
    items = [i for i in assembled.items if i.mode == "proactive"]
    return sorted(items, key=lambda i: severity_rank.get(i.severity, 0), reverse=True)


def persist_edge_cases(
    root: Path,
    artifact_id: str,
    edge_cases: list[str],
) -> dict[str, Any]:
    """Add or extend edge_cases_identified in an artifact's frontmatter."""
    file_path = resolve_link_target(root, artifact_id)
    if file_path is None:
        return {"ok": False, "error": f"Artifact '{artifact_id}' not found"}

    try:
        text = file_path.read_text(encoding="utf-8").strip()
    except Exception:
        return {"ok": False, "error": f"Cannot read {file_path}"}

    if not text.startswith("---"):
        return {"ok": False, "error": "No frontmatter found"}

    end = text.find("---", 3)
    if end == -1:
        return {"ok": False, "error": "Malformed frontmatter"}

    try:
        fm = yaml.safe_load(text[3:end])
    except Exception:
        return {"ok": False, "error": "Cannot parse frontmatter"}

    if not isinstance(fm, dict):
        return {"ok": False, "error": "Invalid frontmatter"}

    existing = fm.get("edge_cases_identified", [])
    if not isinstance(existing, list):
        existing = []

    existing.extend(edge_cases)
    fm["edge_cases_identified"] = existing

    body = text[end + 3:].strip()
    new_text = "---\n" + yaml.dump(fm, default_flow_style=False, sort_keys=False) + "---\n\n" + body + "\n"
    file_path.write_text(new_text, encoding="utf-8")

    return {"ok": True, "count": len(edge_cases), "total": len(existing)}


def create_decision_artifact(
    root: Path,
    title: str,
    context: str,
    options: list[str],
    resolution: str | None,
    linked_artifact_id: str,
) -> dict[str, Any]:
    """Create a DEC (decision) artifact documenting alternatives explored."""
    options_text = "\n".join(f"- **Option {i+1}**: {opt}" for i, opt in enumerate(options))
    resolution_text = f"\n\n## Resolution\n\n{resolution}" if resolution else ""

    body = f"""## Context

{context}

## Options Considered

{options_text}
{resolution_text}
"""

    return create_artifact(
        root=root,
        artifact_type="decision",
        title=title,
        tags=["challenge", "proactive"],
        links=[{"target": linked_artifact_id, "role": "addresses"}],
        body=body,
    )


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
