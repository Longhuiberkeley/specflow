"""CLI handler for ``specflow risk-tier`` — print the deterministic risk tier.

READ-ONLY: computes the minimum risk tier for a change set and prints it. Never
writes a file, never mutates frontmatter, never changes an exit code based on
the tier (accounting, not policing). The tier gates nothing in code; it is a
recorded floor the host agent (or a human) may escalate above freely.

Usage::

    specflow risk-tier ID [ID ...]

The printed tier is the MINIMUM. Downgrading below it requires a recorded
justification on the DEC (``risk_profile.confidence_reason``); escalation needs
no justification.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specflow.lib import artifacts as art_lib
from specflow.lib import risk as risk_lib
from specflow.lib.display import RED, GREEN, YELLOW, CYAN, BOLD, NC


_TIER_LABEL = {0: "light", 1: "normal", 2: "stop"}
_TIER_COLOR = {0: GREEN, 1: YELLOW, 2: RED}


def run(root: Path, args: dict[str, Any]) -> int:
    """Run the risk-tier command. Always returns 0 (read-only, advisory)."""
    root = root.resolve()
    ids: list[str] = args.get("ids") or []

    if not ids:
        print(f"{RED}✗ provide at least one artifact ID{NC}")
        print(f"  usage: specflow risk-tier ID [ID ...]")
        return 1

    artifacts = art_lib.discover_artifacts(root)
    result = risk_lib.compute_risk_tier(ids, artifacts, root)
    evidence = risk_lib.verification_evidence(ids, artifacts)

    tier = result["tier"]
    color = _TIER_COLOR.get(tier, YELLOW)
    label = _TIER_LABEL.get(tier, "normal")

    print(f"\n{CYAN}Risk tier{NC} — {', '.join(ids)}")
    print(f"{CYAN}{'─' * 50}{NC}")
    print(f"  Tier:          {BOLD}{color}Tier {tier} — {label}{NC}")
    print(f"  Reversibility: {result['reversibility']}")
    cone = result["blast_radius_count"]
    large = cone >= risk_lib.LARGE_CONE_THRESHOLD
    cone_note = f" {YELLOW}(large ≥ {risk_lib.LARGE_CONE_THRESHOLD}){NC}" if large else ""
    print(f"  Blast radius:  {cone} downstream artifact(s){cone_note}")
    print(f"  Verification evidence: {evidence}")

    if result["reasons"]:
        print(f"\n  {BOLD}Reasons (triggers that fired){NC}:")
        for r in result["reasons"]:
            print(f"    • {r}")

    print(
        f"\n  {CYAN}This is the minimum tier — escalate freely; "
        f"downgrade only with a recorded justification.{NC}"
    )
    print()
    return 0
