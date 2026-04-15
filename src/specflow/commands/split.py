"""CLI handler for 'specflow split' — split an artifact into two."""

from pathlib import Path
from typing import Any

from specflow.lib import impact as impact_lib


RED = "\033[0;31m"
GREEN = "\033[0;32m"
NC = "\033[0m"


def run(root: Path, args: dict[str, Any]) -> int:
    source_id = args.get("source_id", "")
    new_id = args.get("new_id", "")
    reassign_links = args.get("reassign_links") or []

    if not source_id or not new_id:
        print(f"{RED}✗ Both source_id and new_id are required{NC}")
        print("Usage: specflow split <source-id> <new-id> [--reassign TARGET]...")
        return 1

    result = impact_lib.split_artifact(root, source_id, new_id, reassign_links)
    if not result.get("ok"):
        print(f"{RED}✗ {result.get('error', 'split failed')}{NC}")
        return 1

    rewritten = result.get("rewritten", [])
    print(f"{GREEN}✓ Split {source_id} → {new_id}{NC}")
    print(f"  Links rewritten on {len(rewritten)} artifact(s): {', '.join(rewritten) if rewritten else '(none)'}")
    print(f"  Impact event: {result.get('event_path', '(none)')}")
    return 0
