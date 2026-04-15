"""CLI handler for 'specflow unlock' — break a stale lock on an artifact."""

from pathlib import Path
from typing import Any

from specflow.lib import locks as locks_lib


RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
NC = "\033[0m"


def run(root: Path, args: dict[str, Any]) -> int:
    artifact_id = args.get("artifact_id", "")
    if not artifact_id:
        print(f"{RED}✗ Artifact ID is required{NC}")
        print("Usage: specflow unlock <artifact-id>")
        return 1

    broken = locks_lib.break_stale_lock(root, artifact_id)
    if broken:
        print(f"{GREEN}✓ Broke stale lock on {artifact_id}{NC}")
        return 0

    existing = locks_lib.check_lock(root, artifact_id)
    if existing is None:
        print(f"{YELLOW}No lock exists on {artifact_id}{NC}")
    else:
        pid = existing.get("pid", "?")
        print(f"{YELLOW}Lock on {artifact_id} is still held by live PID {pid}; not broken{NC}")
    return 0
