"""specflow patterns — inspect and maintain learned prevention patterns."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from specflow.lib import learning as learn_lib
from specflow.lib.learning import list_learned_patterns


def run(root: Path, args: dict[str, Any]) -> int:
    sub = args.get("patterns_subcommand")
    if sub == "list":
        return cmd_list(root, args)
    if sub == "show":
        return cmd_show(root, args)
    if sub == "update":
        return cmd_update(root, args)
    if sub == "retire":
        return cmd_retire(root, args)
    print("error: subcommand required (list | show | update | retire)", file=sys.stderr)
    return 1


def cmd_list(root: Path, args: dict[str, Any]) -> int:
    patterns = list_learned_patterns(root)
    if not patterns:
        print("(no learned patterns — they are seeded when a DEF closes, by "
              "`specflow done --auto`, or by `specflow verify --seed-prev`; "
              "retired patterns are hidden)")
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
        tags = learn_lib.pattern_tags(p)
        if tags:
            print(f"         tags: {', '.join(tags)}")
        else:
            print(f"         tags: (none — inert; repair: specflow patterns update {pid} --tags <a,b>)")
        if check_preview:
            print(f"         check: {check_preview}")
    return 0


def cmd_show(root: Path, args: dict[str, Any]) -> int:
    import yaml

    pattern_id = args.get("pattern_id")
    if not pattern_id:
        print("error: pattern ID required (e.g., PREV-001)", file=sys.stderr)
        return 1
    patterns = list_learned_patterns(root, include_retired=True)
    match = [p for p in patterns if p.get("id") == pattern_id]
    if not match:
        print(f"(pattern {pattern_id} not found)", file=sys.stderr)
        return 1
    print(yaml.dump(match[0], default_flow_style=False, sort_keys=False, allow_unicode=True))
    return 0


def cmd_update(root: Path, args: dict[str, Any]) -> int:
    pattern_id = args.get("pattern_id") or ""
    tags = (args.get("tags") or "").split(",")
    try:
        data = learn_lib.update_pattern_tags(root, pattern_id, tags)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    new_tags = learn_lib.pattern_tags(data)
    print(f"✓ {pattern_id} applies_to.tags = {', '.join(new_tags)}")
    if learn_lib.is_retired(data):
        print(f"  note: {pattern_id} is retired — checklist assembly still skips it")
    return 0


def cmd_retire(root: Path, args: dict[str, Any]) -> int:
    pattern_id = args.get("pattern_id") or ""
    try:
        learn_lib.retire_pattern(root, pattern_id)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"✓ {pattern_id} retired — `patterns list` and checklist assembly now skip it "
          f"(file kept so the id is never reused)")
    return 0
