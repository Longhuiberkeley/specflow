"""CLI handler for 'specflow handbook generate' — bundled best-practice guidance.

QT-027 AC3: provides bundled generic best practices as a deterministic fallback
that works without an LLM API key.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specflow.lib.handbook import generate_handbook, format_handbook_text


def run(root: Path, args: dict[str, Any]) -> int:
    """Run the handbook generate command."""
    do_create = args.get("create", False)

    handbook = generate_handbook(root)

    if do_create:
        return _create_bp_artifacts(root, handbook)

    print(format_handbook_text(handbook))
    return 0


def _create_bp_artifacts(root: Path, handbook: dict) -> int:
    """Create BP artifacts from the bundled practices."""
    from specflow.commands.create import run as create_run

    domain = handbook["domain"]
    tags = handbook.get("tags", [])
    practices = handbook["practices"]

    created: list[str] = []
    for p in practices:
        bp_tags = list(set(p.tags + ([domain] if domain != "generic" else [])))
        tag_str = ", ".join(bp_tags) if bp_tags else None
        rc = create_run(root, {
            "type": "best-practice",
            "title": p.title,
            "status": "approved",
            "priority": None,
            "rationale": None,
            "tags": tag_str,
            "links": None,
            "body": p.to_body(),
            "from_standard": None,
            "force": True,
            "skip_dedup_check": True,
            "nfr_category": None,
        })
        if rc == 0:
            created.append(p.title)

    from specflow.lib.display import GREEN, BOLD, NC
    print(
        f"{GREEN}✓{NC} Created {len(created)} BP artifacts "
        f"({len(practices)} practices for domain '{domain}')"
    )
    for title in created:
        print(f"  {BOLD}BP{NC}  {title}")
    return 0
