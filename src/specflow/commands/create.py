"""specflow create — Create a new SpecFlow artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from specflow.lib import artifacts as art_lib
from specflow.lib import standards as std_lib
from specflow.lib.dedup import find_similar_to
from specflow.lib.display import RED, GREEN, YELLOW_DIM, CYAN, NC


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


def _lookup_standard_clause(root: Path, clause_id: str) -> dict | None:
    standards = std_lib.load_standards(root)
    for std in standards:
        for clause in std.get("clauses", []):
            if isinstance(clause, dict) and clause.get("id") == clause_id:
                return clause
    return None


def run(root: Path, args: dict) -> int:
    root = root.resolve()

    from_standard = args.get("from_standard")
    artifact_type = args.get("type", "")
    title = args.get("title", "")
    status = args.get("status", "draft")
    priority = args.get("priority")
    rationale = args.get("rationale")
    tags_str = args.get("tags", "")
    links_str = args.get("links", "")
    body = args.get("body", "")
    nfr_category = args.get("nfr_category")

    links = _parse_links(links_str) if links_str else []

    if from_standard:
        clause = _lookup_standard_clause(root, from_standard)
        if not clause:
            print(f"{RED}✗ Standard clause '{from_standard}' not found in installed standards{NC}")
            return 1
        artifact_type = "requirement"
        title = clause.get("title", f"Compliance with {from_standard}")
        body = clause.get("description", body)
        links.append({"target": from_standard, "role": "complies_with"})

    if not artifact_type:
        print(f"{RED}✗ --type is required{NC}")
        return 1
    if not title:
        print(f"{RED}✗ --title is required{NC}")
        return 1

    tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else None

    if not body and not sys.stdin.isatty():
        body = sys.stdin.read()

    if not args.get("skip_dedup_check", False):
        existing = art_lib.discover_artifacts(root)
        similar = find_similar_to(
            existing,
            artifact_type=artifact_type,
            title=title,
            tags=tags or [],
        )
        blocking = [c for c in similar if c.confidence in ("medium", "high")]
        if blocking:
            print(f"{YELLOW_DIM}⚠ Possible duplicate(s) of the artifact you're creating:{NC}")
            for c in blocking[:5]:
                print(f"  [{c.confidence}] {c.pair[1]}  "
                      f"tag={c.tag_jaccard:.2f}  tfidf={c.tfidf_cosine:.2f}")
            if args.get("force", False):
                print(f"{YELLOW_DIM}  --force supplied, proceeding anyway{NC}")
            elif not sys.stdin.isatty():
                print(f"{RED}✗ Non-interactive mode. Re-run with --force to create anyway, "
                      f"or --skip-dedup-check to bypass the check entirely.{NC}")
                return 1
            else:
                try:
                    reply = input("Create anyway? [y/N]: ").strip().lower()
                except EOFError:
                    reply = ""
                if reply not in ("y", "yes"):
                    print(f"{CYAN}Cancelled.{NC}")
                    return 1

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
        non_functional_category=nfr_category,
    )

    if result["ok"]:
        print(f"{GREEN}✓ Created {result['id']}{NC}")
        print(f"  Path: {result['path']}")
        return 0
    else:
        print(f"{RED}✗ {result['error']}{NC}")
        return 1
