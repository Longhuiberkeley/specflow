"""CLI handler for 'specflow change-impact' — report and resolve suspect flags."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from specflow.lib.artifacts import discover_artifacts
from specflow.lib.impact import (
    load_impact_events,
    resolve_suspect,
    build_output_file_index,
    query_reverse_impact,
    flag_suspects_from_matches,
)
from specflow.lib.display import RED, GREEN, YELLOW, CYAN, NC, BOLD


def _format_age(iso_timestamp: str) -> str:
    """Format an ISO timestamp as a human-readable age string."""
    try:
        ts = datetime.strptime(iso_timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - ts
        days = delta.days
        if days > 0:
            return f"{days}d ago"
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours}h ago"
        minutes = delta.seconds // 60
        return f"{minutes}m ago"
    except (ValueError, TypeError):
        return iso_timestamp


def _detect_source_file_changes(root: Path) -> list[str]:
    """Detect source file changes from the last git commit (non-_specflow files)."""
    from specflow.lib import git_utils

    if not git_utils.is_git_repo(root):
        return []

    try:
        sha = git_utils.get_current_sha(root)
        changed = git_utils.get_changed_files(root, sha)
    except Exception:
        return []

    return [f for f in changed if not f.startswith("_specflow/")]


def run(root: Path, args: dict[str, Any]) -> int:
    """Run the impact command."""
    resolve_id = args.get("resolve")
    filter_id = args.get("artifact_id")
    do_flag = args.get("flag", False)

    if resolve_id:
        result = resolve_suspect(root, resolve_id, resolved_by="user")
        if result["ok"]:
            print(f"{GREEN}✓ Resolved suspect flag on {resolve_id}{NC}")
            return 0
        else:
            print(f"{RED}✗ {result.get('error', result.get('message', 'Unknown error'))}{NC}")
            return 1

    events = load_impact_events(root)
    all_artifacts = discover_artifacts(root)
    suspects = [a for a in all_artifacts if a.suspect]

    if filter_id:
        relevant_events = [e for e in events if e.changed == filter_id and not e.resolved]
        relevant_suspect_ids = set()
        for e in relevant_events:
            for s in e.flagged_suspects:
                relevant_suspect_ids.add(s.get("artifact", ""))
        suspects = [a for a in suspects if a.id in relevant_suspect_ids]
        events = relevant_events

    unresolved_events = [e for e in events if not e.resolved]

    if not suspects and not unresolved_events:
        print("No unresolved suspect flags")
        return 0

    source_groups: dict[str, list[dict[str, str]]] = {}
    for event in unresolved_events:
        source = event.changed
        for s in event.flagged_suspects:
            source_groups.setdefault(source, []).append({
                "artifact": s.get("artifact", ""),
                "link_role": s.get("link_role", ""),
                "timestamp": event.timestamp,
            })

    print(f"\n{BOLD}Unresolved Suspect Flags{NC} ({len(suspects)} artifacts)\n")

    for source, flagged in sorted(source_groups.items()):
        print(f"  Source: {BOLD}{YELLOW}{source}{NC} (changed)")
        for f in flagged:
            art_id = f["artifact"]
            role = f["link_role"]
            ts = f["timestamp"]
            print(f"    → {art_id} (via {role}) — flagged {_format_age(ts)}")
        print()

    if unresolved_events:
        oldest_ts = min(e.timestamp for e in unresolved_events)
        print(f"  Oldest unresolved flag: {_format_age(oldest_ts)}\n")

    if suspects:
        print("To resolve: specflow change-impact --resolve <ARTIFACT_ID>")

    source_changes = _detect_source_file_changes(root)
    if source_changes:
        index = build_output_file_index(root)
        source_matches = query_reverse_impact(root, source_changes, index)

        if source_matches:
            if do_flag:
                flagged_ids = flag_suspects_from_matches(root, source_matches)
                print(f"\n{BOLD}Source File Impact{NC} ({len(source_matches)} match(es), {len(flagged_ids)} artifact(s) flagged)\n")
            else:
                print(f"\n{BOLD}Source File Impact{NC} ({len(source_matches)} match(es))\n")

            by_artifact: dict[str, list] = {}
            for m in source_matches:
                by_artifact.setdefault(m.artifact_id, []).append(m)

            for art_id, file_matches in sorted(by_artifact.items()):
                print(f"  Artifact: {BOLD}{YELLOW}{art_id}{NC}")
                for m in file_matches:
                    match_label = f"({m.match_type}: {m.pattern})"
                    print(f"    ← {m.file_path} {match_label}")
                print()

            if do_flag:
                print("To resolve: specflow change-impact --resolve <ARTIFACT_ID>")
            else:
                print("To flag these artifacts: specflow change-impact --flag")

    return 0
