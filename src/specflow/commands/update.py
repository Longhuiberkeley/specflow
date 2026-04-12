"""specflow update — Update an existing SpecFlow artifact's frontmatter."""

from __future__ import annotations

from pathlib import Path

from specflow.lib import artifacts as art_lib
from specflow.lib import defects as defects_lib

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
NC = "\033[0m"


def run(root: Path, args: dict) -> int:
    root = root.resolve()

    artifact_id = args.get("artifact_id", "")
    if not artifact_id:
        print(f"{RED}✗ Artifact ID is required (positional argument){NC}")
        return 1

    updates = {}

    status = args.get("status")
    if status:
        updates["status"] = status

    priority = args.get("priority")
    if priority:
        updates["priority"] = priority

    rationale = args.get("rationale")
    if rationale:
        updates["rationale"] = rationale

    tags_str = args.get("tags")
    if tags_str:
        updates["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]

    title = args.get("title")
    if title:
        updates["title"] = title

    if not updates:
        print(f"{RED}✗ No fields to update. Use --status, --title, --priority, --rationale, or --tags.{NC}")
        return 1

    result = art_lib.update_artifact(root=root, artifact_id=artifact_id, **updates)

    if result["ok"]:
        print(f"{GREEN}✓ Updated {result['id']}{NC}")
        # DEF closure hook: trigger reactive challenge-engine pattern extraction
        # when a defect transitions to `closed`. Best-effort — failures here
        # are reported as warnings but do not fail the update.
        if (
            artifact_id.startswith("DEF-")
            and updates.get("status") == "closed"
        ):
            outcome = defects_lib.on_closure(root, artifact_id)
            if outcome.get("ok"):
                print(
                    f"{GREEN}  ↳ Reactive challenge engine: prevention pattern seeded at "
                    f"{outcome.get('pattern_path')}{NC}"
                )
            else:
                print(
                    f"{YELLOW}  ⚠ Prevention-pattern extraction skipped: "
                    f"{outcome.get('error')}{NC}"
                )
        return 0
    else:
        print(f"{RED}✗ {result['error']}{NC}")
        return 1
