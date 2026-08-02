"""CLI handler for 'specflow rebuild-index' — regenerate stale _index.yaml files."""

from pathlib import Path
from typing import Any

from specflow.lib import artifacts as artifacts_lib
from specflow.lib import docs as docs_lib
from specflow.lib.display import GREEN, NC


def run(root: Path, args: dict[str, Any]) -> int:
    artifact_type = args.get("type")
    result = artifacts_lib.rebuild_index(root, artifact_type)
    rebuilt = result.get("rebuilt", 0)
    repaired = result.get("repaired", 0)
    quarantined = result.get("quarantined", 0)
    scope = f"type={artifact_type}" if artifact_type else "all types"
    print(f"{GREEN}✓ Rebuilt index ({scope}): {rebuilt} artifact(s){NC}")
    print(
        f"{GREEN}  repaired {repaired} fingerprint(s), "
        f"quarantined {quarantined} fileless entr(ies){NC}"
    )

    # The docs knowledge surface is rebuilt alongside the artifact index when no
    # specific artifact type is requested. Docs are NOT artifacts — this cache is
    # a derived accelerator for `brief`, never the source of truth.
    if not artifact_type:
        payload = docs_lib.write_docs_index(root)
        print(f"{GREEN}✓ Rebuilt docs index: {len(payload.get('docs', {}))} doc(s){NC}")

    return 0
