"""CLI handler for 'specflow cascade-status' — cascade STORY status to linked specs."""

from pathlib import Path
from typing import Any

from specflow.lib import artifacts as art_lib
from specflow.lib.display import GREEN, YELLOW, NC


def run(root: Path, args: dict[str, Any]) -> int:
    """Cascade STORY status to linked ARCH/DDD (and optionally REQ) artifacts."""
    artifact_id = args.get("artifact_id", "")
    include_req = args.get("include_req", False)
    dry_run = args.get("dry_run", False)

    if not artifact_id:
        print(f"{YELLOW}No artifact ID provided{NC}")
        return 1

    prefix = art_lib.get_prefix_from_id(artifact_id)
    if prefix != "STORY":
        print(f"{YELLOW}cascade-status only applies to STORY artifacts (got {artifact_id}){NC}")
        return 1

    file_path = art_lib.resolve_link_target(root, artifact_id)
    if file_path is None:
        print(f"{YELLOW}Artifact not found: {artifact_id}{NC}")
        return 1

    story = art_lib.parse_artifact(file_path)
    if story is None:
        print(f"{YELLOW}Cannot parse artifact: {artifact_id}{NC}")
        return 1

    if story.status not in ("implemented", "verified"):
        print(f"{YELLOW}{artifact_id} is '{story.status}' (cascade only applies to implemented/verified){NC}")
        return 0

    target_status = "implemented"
    if story.status == "verified" and include_req:
        target_status = "verified"

    all_artifacts = art_lib.discover_artifacts(root)
    id_index = art_lib.build_id_index(all_artifacts)

    cascaded = []
    skipped = []

    for link in story.links:
        target = id_index.get(link.target)
        if target is None:
            continue

        target_prefix = art_lib.get_prefix_from_id(target.id)

        if link.role == "guided_by" and target_prefix == "ARCH":
            if target.status == "approved":
                cascaded.append((target.id, "ARCH", "approved", target_status))
            else:
                skipped.append((target.id, "ARCH", target.status))

        elif link.role == "specified_by" and target_prefix == "DDD":
            if target.status == "approved":
                cascaded.append((target.id, "DDD", "approved", target_status))
            else:
                skipped.append((target.id, "DDD", target.status))

    if include_req:
        for link in story.links:
            target = id_index.get(link.target)
            if target is None:
                continue
            if link.role == "implements" and art_lib.get_prefix_from_id(target.id) == "REQ":
                if target.status in ("approved", "implemented"):
                    req_status = "implemented"
                    if story.status == "verified":
                        req_status = "verified"
                    cascaded.append((target.id, "REQ", target.status, req_status))
                else:
                    skipped.append((target.id, "REQ", target.status))

    if not cascaded:
        if skipped:
            print(f"{GREEN}{artifact_id}: all linked specs already at or beyond target status{NC}")
            for tid, ttype, tstatus in skipped:
                print(f"  {tid} ({ttype}): {tstatus}")
        else:
            print(f"{GREEN}{artifact_id}: no linked ARCH/DDD specs found to cascade{NC}")
        return 0

    print(f"\n{GREEN}Cascade from {artifact_id} ({story.status}):{NC}")
    for tid, ttype, from_st, to_st in cascaded:
        if dry_run:
            print(f"  {tid} ({ttype}): {from_st} → {to_st} [dry-run]")
        else:
            result = art_lib.update_artifact(root, tid, status=to_st)
            if result.get("ok"):
                print(f"  {GREEN}✓{NC} {tid} ({ttype}): {from_st} → {to_st}")
            else:
                print(f"  {YELLOW}✗{NC} {tid} ({ttype}): {result.get('error', 'update failed')}")

    return 0
