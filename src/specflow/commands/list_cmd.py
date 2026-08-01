"""specflow list — List artifacts with optional filters."""

from __future__ import annotations

import difflib
import json
from pathlib import Path

from specflow.lib import artifacts as art_lib
from specflow.lib.display import RED, CYAN, NC


def run(root: Path, args: dict) -> int:
    root = root.resolve()

    type_filter = args.get("type")
    status_filter = args.get("status")
    tags_str = args.get("tags")
    as_json = args.get("json", False)

    # Normalize the type filter so aliases/prefixes resolve to a canonical
    # type, then validate it: an unknown type must error, not fall through to
    # discover_artifacts' scan-everything branch (which would silently ignore
    # the filter).
    discover_type = None
    if type_filter:
        discover_type = art_lib.normalize_type(type_filter)
        art_lib._load_active_packs(root)
        if discover_type not in art_lib.TYPE_TO_DIR:
            valid = sorted(art_lib.TYPE_TO_DIR)
            msg = (f"{RED}✗ No schema found for type '{type_filter}'. "
                   f"Valid types: {', '.join(valid)}.{NC}")
            close = difflib.get_close_matches(discover_type, valid, n=3)
            if close:
                msg = f"{RED}✗ No schema found for type '{type_filter}'. " \
                      f"Did you mean: {', '.join(close)}? " \
                      f"Valid types: {', '.join(valid)}.{NC}"
            print(msg)
            return 1

    artifacts = art_lib.discover_artifacts(root, artifact_type=discover_type)

    if status_filter:
        artifacts = [a for a in artifacts if a.status == status_filter]

    if tags_str:
        wanted = {t.strip() for t in tags_str.split(",") if t.strip()}
        if wanted:
            artifacts = [
                a for a in artifacts
                if wanted & set(a.tags)
            ]

    if as_json:
        payload = [
            {
                "id": a.id,
                "type": a.type,
                "status": a.status,
                "title": a.title,
                "path": str(a.path),
            }
            for a in artifacts
        ]
        print(json.dumps(payload, indent=2))
        return 0

    if not artifacts:
        print("No artifacts match the given filters.")
        return 0

    # Aligned columns: ID / STATUS / TITLE.
    id_w = max((len(a.id) for a in artifacts), default=2)
    id_w = max(id_w, len("ID"))
    status_w = max((len(a.status) for a in artifacts), default=6)
    status_w = max(status_w, len("STATUS"))

    print(f"{CYAN}{'ID':<{id_w}}  {'STATUS':<{status_w}}  TITLE{NC}")
    for a in artifacts:
        print(f"{a.id:<{id_w}}  {a.status:<{status_w}}  {a.title}")

    print()
    print(f"{len(artifacts)} artifact(s).")
    return 0
