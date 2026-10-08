"""CLI handler for 'specflow rebuild-index' — regenerate stale _index.yaml files."""

import difflib
from pathlib import Path
from typing import Any

from specflow.lib import artifacts as artifacts_lib
from specflow.lib import docs as docs_lib
from specflow.lib.display import GREEN, NC, RED


def run(root: Path, args: dict[str, Any]) -> int:
    artifact_type = args.get("type")
    if artifact_type:
        # Resolve prefixes/aliases (REQ, req, ddd ...) to the canonical type and
        # reject anything that is not a known type: `rebuild_index` would skip
        # an unknown type silently and report "✓ 0 artifact(s)".
        artifacts_lib._load_active_packs(root)
        canonical = artifacts_lib.normalize_type(artifact_type)
        if canonical not in artifacts_lib.TYPE_TO_DIR:
            # Canonical names are case-sensitive in normalize_type; accept
            # `Requirement` the way `REQ`/`req` are already accepted.
            canonical = artifacts_lib.normalize_type(artifact_type.lower())
        if canonical not in artifacts_lib.TYPE_TO_DIR:
            valid = sorted(artifacts_lib.TYPE_TO_DIR)
            hint = ""
            close = difflib.get_close_matches(canonical.lower(), valid, n=3)
            if close:
                hint = f" Did you mean: {', '.join(close)}?"
            print(f"{RED}✗ Unknown artifact type '{artifact_type}'.{hint} "
                  f"Valid types: {', '.join(valid)}.{NC}")
            return 1
        artifact_type = canonical
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
