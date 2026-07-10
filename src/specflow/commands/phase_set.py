"""specflow phase-set — reverse-lifecycle accounting: record a phase transition.

The phase machine (`lib/learning.py`) is forward-only via `close_phase`/`next_phase`.
When a user says "go back to requirements," `state.current` needs a way to be
corrected so `brief --next` routes correctly again. This command RECORDS a
transition — forward or a rewind — it never gates one (accounting, not policing).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specflow.lib import config as config_lib
from specflow.lib.learning import set_phase
from specflow.lib.display import RED, GREEN, YELLOW, NC


def run(root: Path, args: dict[str, Any]) -> int:
    root = root.resolve()
    config = config_lib.read_config(root)
    if not config:
        print(f"{RED}✗ SpecFlow is not initialized here. Run 'uv run specflow init'.{NC}")
        return 1

    target = (args.get("phase") or "").strip()
    reason = args.get("reason")

    result = set_phase(root, target, reason=reason)
    if not result.get("ok"):
        print(f"{RED}✗ {result.get('error', 'phase-set failed')}{NC}")
        return 1

    old_phase = result["old_phase"]
    new_phase = result["new_phase"]

    if old_phase == new_phase:
        print(f"{YELLOW}Already in phase '{new_phase}' — no change.{NC}")
        return 0

    arrow = f"{old_phase} → {new_phase}"
    if result.get("rewind"):
        arrow += f"  {YELLOW}(rewind){NC}"
    print(f"{GREEN}✓{NC} Phase set: {arrow}")
    if reason:
        print(f"  reason: {reason}")
    print("  Run 'specflow brief --next' for the recommended next step.")
    return 0
