"""CLI handler for 'specflow merge' — merge two artifacts."""

from pathlib import Path
from typing import Any

from specflow.lib import impact as impact_lib
from specflow.lib.display import RED, GREEN, NC


def run(root: Path, args: dict[str, Any]) -> int:
    source_id = args.get("source_id", "")
    target_id = args.get("target_id", "")

    if not source_id or not target_id:
        print(f"{RED}✗ Both source_id and target_id are required{NC}")
        print("Usage: specflow merge <source-id> <target-id>")
        return 1

    result = impact_lib.merge_artifact(root, source_id, target_id)
    if not result.get("ok"):
        print(f"{RED}✗ {result.get('error', 'merge failed')}{NC}")
        return 1

    rewritten = result.get("rewritten", [])
    print(f"{GREEN}✓ Merged {source_id} → {target_id}{NC}")
    print(f"  Links rewritten on {len(rewritten)} artifact(s): {', '.join(rewritten) if rewritten else '(none)'}")
    return 0
