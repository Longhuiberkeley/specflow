"""specflow update — Update an existing SpecFlow artifact's frontmatter."""

from __future__ import annotations

from pathlib import Path

from specflow.lib import artifacts as art_lib

RED = "\033[0;31m"
GREEN = "\033[0;32m"
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
        return 0
    else:
        print(f"{RED}✗ {result['error']}{NC}")
        return 1
