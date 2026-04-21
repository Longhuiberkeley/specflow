"""CLI handler for 'specflow rebuild-index' — regenerate stale _index.yaml files."""

from pathlib import Path
from typing import Any

from specflow.lib import artifacts as artifacts_lib
from specflow.lib.display import GREEN, NC


def run(root: Path, args: dict[str, Any]) -> int:
    artifact_type = args.get("type")
    result = artifacts_lib.rebuild_index(root, artifact_type)
    rebuilt = result.get("rebuilt", 0)
    scope = f"type={artifact_type}" if artifact_type else "all types"
    print(f"{GREEN}✓ Rebuilt index ({scope}): {rebuilt} artifact(s){NC}")
    return 0
