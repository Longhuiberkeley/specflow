"""specflow artifact-review — Compose lint + checklist into a single review entry point.

This is STORY-022's minimal stub. Only --depth quick is implemented (deterministic
lint + checklist-run, zero LLM). STORY-024 adds --depth normal|deep with LLM
judgment, CHL artifacts, and thinking-technique subagent fan-out.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specflow.commands import artifact_lint, checklist_run


def run(root: Path, args: dict[str, Any]) -> int:
    """Execute specflow artifact-review.

    Returns:
        0 = clean, 2 = findings, 3 = tool error.
    """
    depth = args.get("depth") or "quick"
    if depth != "quick":
        print(
            f"\033[0;33m⚠ --depth {depth} is not yet implemented.\033[0m\n"
            "  The artifact-review depth tiers (normal, deep) and thinking-technique\n"
            "  fan-out are scheduled for STORY-024. For now, use --depth quick, or\n"
            "  run 'specflow artifact-lint' and 'specflow checklist-run' directly."
        )
        return 2

    lint_rc = artifact_lint.run(root, {})
    if lint_rc not in (0, 1):
        return 3

    check_args = {
        "artifact_id": args.get("artifact_id"),
        "all": args.get("all", False),
        "gate": args.get("gate"),
        "proactive": args.get("proactive", False),
        "dedup": False,
    }
    if not check_args["artifact_id"] and not check_args["all"]:
        check_args["all"] = True

    check_rc = checklist_run.run(root, check_args)
    if check_rc not in (0, 1):
        return 3

    return 2 if (lint_rc == 1 or check_rc == 1) else 0
