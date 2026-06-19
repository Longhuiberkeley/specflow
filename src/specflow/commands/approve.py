"""specflow approve — batch-approve artifacts by type and current status.

A convenience wrapper around `specflow update --status approved` for many artifacts at
once (e.g. all draft REQs after a discovery session). This is a single explicit human
CLI act: it prints the full ID list and requires one confirmation. Skills MUST NOT
auto-invoke it as part of an auto-flow, and it never reads past approvals to size or
skip the batch (no approval-history calibration). Approval is always a human act.
"""

from __future__ import annotations

from pathlib import Path

from specflow.lib import artifacts as art_lib
from specflow.lib.display import RED, GREEN, YELLOW, BOLD, NC


def _resolve_prefix(artifact_type: str) -> str:
    """Accept either an ID prefix (REQ, STORY) or a full type name (requirement, story)."""
    candidate = artifact_type.upper()
    if candidate in art_lib.PREFIX_TO_TYPE:
        return candidate
    mapped = art_lib.TYPE_TO_PREFIX.get(artifact_type) or art_lib.TYPE_TO_PREFIX.get(artifact_type.lower())
    return mapped or candidate


def run(root: Path, args: dict) -> int:
    root = root.resolve()

    artifact_type = (args.get("type") or "").strip()
    if not artifact_type:
        print(f"{RED}✗ --type is required (e.g. --type REQ or --type STORY).{NC}")
        return 1

    prefix = _resolve_prefix(artifact_type)
    from_status = (args.get("status") or "draft").strip()
    target_status = (args.get("target_status") or "approved").strip()

    all_artifacts = art_lib.discover_artifacts(root)
    targets = [
        a for a in all_artifacts
        if art_lib.get_prefix_from_id(a.id) == prefix and (a.status or "draft") == from_status
    ]

    if not targets:
        print(f"{YELLOW}No {prefix} artifacts in status '{from_status}' to move to '{target_status}'.{NC}")
        return 0

    print(f"\n{BOLD}Batch approve{NC} — {len(targets)} {prefix} artifact(s): "
          f"'{from_status}' → '{target_status}'")
    for a in targets:
        title = (a.title or "(untitled)")[:70]
        print(f"  • {a.id} — {title}")

    if not args.get("yes"):
        try:
            ans = input(f"\nMove all {len(targets)} to '{target_status}'? [y/N] ").strip().lower()
        except EOFError:
            ans = ""
        if ans not in ("y", "yes"):
            print(f"{YELLOW}Aborted — no artifacts changed.{NC}")
            return 1

    ok = 0
    failed: list[tuple[str, str]] = []
    for a in targets:
        result = art_lib.update_artifact(root=root, artifact_id=a.id, status=target_status)
        if result.get("ok"):
            ok += 1
        else:
            failed.append((a.id, result.get("error", "unknown error")))

    print(f"\n{GREEN}✓ Moved {ok}/{len(targets)} {prefix} artifact(s) to '{target_status}'.{NC}")
    if failed:
        for art_id, err in failed:
            print(f"{RED}  ✗ {art_id}: {err}{NC}")
        return 1
    return 0
