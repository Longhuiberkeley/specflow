"""CLI handler for 'specflow unlock' — break a stale lock on an artifact."""

from pathlib import Path
from typing import Any

from specflow.lib import locks as locks_lib
from specflow.lib.display import RED, GREEN, YELLOW, NC


def run(root: Path, args: dict[str, Any]) -> int:
    artifact_id = args.get("artifact_id", "")
    if not artifact_id:
        print(f"{RED}✗ Artifact ID is required{NC}")
        print("Usage: specflow unlock <artifact-id> | specflow unlock create-lock:<type>")
        return 1

    # 'create-lock:<type>' addresses the type-scoped create guard (the lock
    # whose key namespaces on the artifact type, not an existing ID).
    if artifact_id.startswith("create-lock:"):
        from specflow.lib.artifacts import normalize_type

        raw_type = artifact_id.split(":", 1)[1]
        artifact_type = normalize_type(raw_type)
        key = locks_lib.create_lock_key(artifact_type)
        label = f"create-lock:{artifact_type}"
    else:
        key = artifact_id
        label = artifact_id

    broken = locks_lib.break_stale_lock(root, key)
    if broken:
        print(f"{GREEN}✓ Broke stale lock on {label}{NC}")
        return 0

    existing = locks_lib.check_lock(root, key)
    if existing is None:
        print(f"{YELLOW}No lock exists on {label}{NC}")
    else:
        pid = existing.get("pid", "?")
        print(f"{YELLOW}Lock on {label} is still held by live PID {pid}; not broken{NC}")
    return 0
