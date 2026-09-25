"""CLI commands for bundled best-practice seeding, validation, and migration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from specflow.lib import practices as practices_lib
from specflow.lib import practices_seed


def run(root: Path, args: dict[str, Any]) -> int:
    """Dispatch a ``specflow practices`` subcommand."""
    subcommand = args.get("practices_subcommand")
    if subcommand == "seed":
        return _seed(root, args)
    if subcommand == "validate":
        return _validate(root)
    if subcommand == "migrate":
        return _migrate(root, dry_run=bool(args.get("dry_run", False)))
    print("error: subcommand required (seed | validate | migrate)")
    return 1


def _seed(root: Path, args: dict[str, Any]) -> int:
    handbook = practices_seed.generate_handbook(root)
    if args.get("create"):
        return _create_bp_artifacts(root, handbook)
    print(practices_seed.format_handbook_text(handbook, verbose=bool(args.get("verbose"))))
    return 0


def _create_bp_artifacts(root: Path, handbook: dict[str, Any]) -> int:
    """Create draft BP artifacts from the stable bundled seed catalogue."""
    from specflow.commands.create import run as create_run
    from specflow.lib.display import BOLD, GREEN, NC

    domain = handbook["domain"]
    practices = handbook["practices"]
    created: list[str] = []
    failures = 0
    for practice in practices:
        bp_tags = list(dict.fromkeys(
            practice.tags + ([domain] if domain != "generic" else [])
        ))
        applicability = (
            {"always": True}
            if practice.domain == "generic"
            else {"domains": [practice.domain]}
        )
        set_fields = [
            "provenance=bundled",
            f"source={practice.seed_id}",
            f"applicability={json.dumps(applicability, separators=(',', ':'))}",
        ]
        rc = create_run(root, {
            "type": "best-practice",
            "title": practice.title,
            # A human approves a new best practice; seeding only drafts it.
            "status": "draft",
            "priority": None,
            "rationale": None,
            "tags": ", ".join(bp_tags) if bp_tags else None,
            "links": None,
            "body": practice.to_body(),
            "from_standard": None,
            "force": True,
            "skip_dedup_check": True,
            "nfr_category": None,
            "set_fields": set_fields,
        })
        if rc == 0:
            created.append(practice.title)
        else:
            failures += 1

    print(
        f"{GREEN}✓{NC} Created {len(created)} BP artifacts "
        f"({len(practices)} practices for domain '{domain}')"
    )
    for title in created:
        print(f"  {BOLD}BP{NC}  {title}")
    return 1 if failures else 0


def _validate(root: Path) -> int:
    issues = practices_lib.validate_practices(root)
    if issues:
        for issue in issues:
            print(f"{issue['path']}: {issue['reason']}")
        print(f"Validation failed: {len(issues)} issue(s).")
        return 1
    count = len(practices_lib._best_practice_files(root))
    print(f"Validated {count} best-practice artifact(s): PASS")
    return 0


def _migrate(root: Path, *, dry_run: bool) -> int:
    result = practices_lib.migrate_practices(root, dry_run=dry_run)
    plan = result["would_stamp"]
    if dry_run:
        print(f"Would stamp provenance on {len(plan)} best-practice artifact(s):")
        for item in plan:
            fields = ", ".join(f"{key}={value}" for key, value in item["fields"].items())
            print(f"  {item['path']}: {fields}")
        print("Dry run complete; no files written.")
    else:
        print(f"Stamped provenance on {len(result['stamped'])} best-practice artifact(s).")
    for warning in result["warnings"]:
        print(f"warning: {warning}")
    for error in result["errors"]:
        print(f"error: {error}")
    return 1 if result["errors"] else 0


__all__ = ["run"]
