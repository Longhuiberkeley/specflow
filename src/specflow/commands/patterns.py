"""specflow patterns — inspect learned prevention patterns."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specflow.lib.learning import list_learned_patterns


def run(root: Path, args: dict[str, Any]) -> int:
    sub = args.get("patterns_subcommand")
    if sub == "list":
        return cmd_list(root, args)
    if sub == "show":
        return cmd_show(root, args)
    print("error: subcommand required (list | show)", file=__import__("sys").stderr)
    return 1


def cmd_list(root: Path, args: dict[str, Any]) -> int:
    patterns = list_learned_patterns(root)
    if not patterns:
        print("(no learned patterns — patterns accumulate from artifact reviews with blocking/warning findings)")
        return 0
    print(f"\nLearned prevention patterns: {len(patterns)}\n")
    for p in patterns:
        pid = p.get("id", "?")
        name = p.get("name", "")
        source = p.get("discovered_from", "")
        items = p.get("items", [])
        check_preview = items[0].get("check", "")[:80] if items else ""
        severity = items[0].get("severity", "?") if items else "?"
        print(f"  {pid}  [{severity}]  {name}")
        if source:
            print(f"         from: {source}")
        if check_preview:
            print(f"         check: {check_preview}")
    return 0


def cmd_show(root: Path, args: dict[str, Any]) -> int:
    import yaml

    pattern_id = args.get("pattern_id")
    if not pattern_id:
        print("error: pattern ID required (e.g., PREV-001)", file=__import__("sys").stderr)
        return 1
    patterns = list_learned_patterns(root)
    match = [p for p in patterns if p.get("id") == pattern_id]
    if not match:
        print(f"(pattern {pattern_id} not found)", file=__import__("sys").stderr)
        return 1
    print(yaml.dump(match[0], default_flow_style=False, sort_keys=False, allow_unicode=True))
    return 0
