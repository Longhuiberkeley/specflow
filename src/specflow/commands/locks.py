"""CLI handler for 'specflow locks' — list all active locks."""

from pathlib import Path
from typing import Any

from specflow.lib import locks as locks_lib


GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
NC = "\033[0m"


def run(root: Path, args: dict[str, Any]) -> int:
    locks = locks_lib.list_locks(root)
    if not locks:
        print(f"{GREEN}No active locks.{NC}")
        return 0

    print(f"{len(locks)} active lock(s):")
    for lock in locks:
        artifact_id = lock.get("artifact_id", "?")
        pid = lock.get("pid", "?")
        holder = lock.get("holder", "?")
        acquired = lock.get("acquired_at", "?")
        stale = lock.get("stale", False)
        flag = f"{YELLOW}[stale]{NC}" if stale else ""
        print(f"  {artifact_id}  pid={pid}  holder={holder}  acquired={acquired}  {flag}")
    return 0
