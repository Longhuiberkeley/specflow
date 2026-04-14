"""CLI handler for 'specflow change-impact' — report and resolve suspect flags."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from specflow.lib.artifacts import discover_artifacts
from specflow.lib.impact import load_impact_events, resolve_suspect


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


def run(root: Path, args: dict[str, Any]) -> int:
    """Run the impact command."""
    resolve_id = args.get("resolve")
    filter_id = args.get("artifact_id")

    if resolve_id:
        result = resolve_suspect(root, resolve_id, resolved_by="user")
        if result["ok"]:
            print(f"\033[0;32m✓ Resolved suspect flag on {resolve_id}\033[0m")
            return 0
        else:
            print(f"\033[0;31m✗ {result.get('error', result.get('message', 'Unknown error'))}\033[0m")
            return 1

    # Load all events and artifacts
    events = load_impact_events(root)
    all_artifacts = discover_artifacts(root)
    suspects = [a for a in all_artifacts if a.suspect]

    # Filter by source artifact if specified
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

    # Group suspects by source change
    source_groups: dict[str, list[dict[str, str]]] = {}
    for event in unresolved_events:
        source = event.changed
        for s in event.flagged_suspects:
            source_groups.setdefault(source, []).append({
                "artifact": s.get("artifact", ""),
                "link_role": s.get("link_role", ""),
                "timestamp": event.timestamp,
            })

    print(f"\n\033[1mUnresolved Suspect Flags\033[0m ({len(suspects)} artifacts)\n")

    for source, flagged in sorted(source_groups.items()):
        print(f"  Source: \033[1;33m{source}\033[0m (changed)")
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

    return 0
