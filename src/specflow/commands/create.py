"""specflow create — Create a new SpecFlow artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from specflow.lib import artifacts as art_lib

RED = "\033[0;31m"
GREEN = "\033[0;32m"
CYAN = "\033[0;36m"
NC = "\033[0m"


def _parse_links(links_json: str) -> list[dict[str, str]]:
    try:
        parsed = json.loads(links_json)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    results = []
    for part in links_json.split(","):
        part = part.strip()
        if ":" in part:
            target, role = part.split(":", 1)
            results.append({"target": target.strip(), "role": role.strip()})
    return results


def run(root: Path, args: dict) -> int:
    root = root.resolve()

    artifact_type = args.get("type", "")
    title = args.get("title", "")
    status = args.get("status", "draft")
    priority = args.get("priority")
    rationale = args.get("rationale")
    tags_str = args.get("tags", "")
    links_str = args.get("links", "")
    body = args.get("body", "")

    if not artifact_type:
        print(f"{RED}✗ --type is required{NC}")
        return 1
    if not title:
        print(f"{RED}✗ --title is required{NC}")
        return 1

    tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else None
    links = _parse_links(links_str) if links_str else None

    if not body and not sys.stdin.isatty():
        body = sys.stdin.read()

    result = art_lib.create_artifact(
        root=root,
        artifact_type=artifact_type,
        title=title,
        status=status,
        priority=priority,
        rationale=rationale,
        tags=tags,
        links=links,
        body=body,
    )

    if result["ok"]:
        print(f"{GREEN}✓ Created {result['id']}{NC}")
        print(f"  Path: {result['path']}")
        return 0
    else:
        print(f"{RED}✗ {result['error']}{NC}")
        return 1
