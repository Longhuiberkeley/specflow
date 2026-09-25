"""Shared best-practice anatomy and applicability primitives."""

from __future__ import annotations

import re
from typing import Any


PRACTICE_SECTIONS = (
    "Practice",
    "Applies when",
    "Work products",
    "Verification",
    "Rationale",
)

PROVENANCE_VALUES = frozenset({"bundled", "standard", "synthesized", "learned"})
STRENGTH_VALUES = frozenset({"mandatory", "recommended", "neutral", "informal"})
VERIFICATION_METHODS = frozenset({"test", "inspection", "analysis", "demonstration"})

_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def render_practice_body(
    practice: str,
    applies_when: str,
    work_products: str,
    verification: str,
    rationale: str,
) -> str:
    """Render the normative five-section BP body in its canonical order."""
    values = (practice, applies_when, work_products, verification, rationale)
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("all five best-practice sections need non-empty text")
    return "\n\n".join(
        f"## {heading}\n\n{value.strip()}"
        for heading, value in zip(PRACTICE_SECTIONS, values)
    ) + "\n"


def validate_anatomy(body: str) -> list[str]:
    """Return deterministic anatomy problems, in canonical section order."""
    headings = [match.group(1).strip() for match in _SECTION_RE.finditer(body or "")]
    positions: list[int] = []
    problems: list[str] = []
    for section in PRACTICE_SECTIONS:
        matches = [index for index, heading in enumerate(headings) if heading == section]
        if not matches:
            problems.append(f"missing section '{section}'")
        elif len(matches) > 1:
            problems.append(f"duplicate section '{section}'")
        else:
            positions.append(matches[0])
    if len(positions) == len(PRACTICE_SECTIONS) and positions != sorted(positions):
        problems.append("sections are not in canonical order")

    # A required heading with no body text is structurally present but unusable.
    for match in _SECTION_RE.finditer(body or ""):
        heading = match.group(1).strip()
        if heading not in PRACTICE_SECTIONS:
            continue
        content_start = match.end()
        next_heading = _SECTION_RE.search(body, content_start)
        content_end = next_heading.start() if next_heading else len(body)
        if not body[content_start:content_end].strip():
            problems.append(f"section '{heading}' is empty")
    return problems


def status_is_valid(schema: dict[str, Any], status: str) -> bool:
    """Accept active BP records as transition-only legacy statuses.

    The lifecycle no longer has an ``active`` node. The approved transition
    retains ``active`` as a predecessor so pre-migration artifacts and their
    supersession edges remain lintable while they are migrated.
    """
    allowed = schema.get("allowed_status", {})
    if status in allowed:
        return True
    if schema.get("type") != "best-practice" or not isinstance(allowed, dict):
        return False
    return status in {predecessor for values in allowed.values() for predecessor in (values or [])}
