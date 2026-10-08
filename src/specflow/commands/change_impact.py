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


# Artifacts listed in full under "Source File Impact" before the rest is
# summarised: a release commit can touch a hundred test files, and 300 lines
# of repeat output is what made the section read as noise.
_SOURCE_IMPACT_MAX_ARTIFACTS = 20


def _detect_source_file_changes(root: Path) -> tuple[list[str], str, str]:
    """Source files changed by the HEAD commit (non-_specflow paths).

    Returns ``(files, sha, commit_timestamp)`` where the timestamp is ISO-8601
    UTC (``%Y-%m-%dT%H:%M:%SZ``, the impact-log format) or ``''`` when unknown.
    HEAD semantics are deliberate: the CI job runs this on every push to
    report what the pushed commit touched.
    """
    from specflow.lib import git_utils

    if not git_utils.is_git_repo(root):
        return [], "", ""

    try:
        sha = git_utils.get_current_sha(root)
        changed = git_utils.get_changed_files(root, sha)
    except Exception:
        return [], "", ""

    commit_ts = ""
    try:
        iso = git_utils.get_commit_timestamp(root, sha)
        if iso:
            # %cI carries the committer's offset; the impact log is UTC "Z".
            commit_ts = (
                datetime.fromisoformat(iso)
                .astimezone(timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%SZ")
            )
    except (OSError, ValueError, TypeError):
        commit_ts = ""

    return [f for f in changed if not f.startswith("_specflow/")], sha, commit_ts


def _commit_is_newer_than_log(commit_ts: str, events: list) -> bool:
    """True when the HEAD commit postdates every impact-log event (or the log
    is empty): only then is the ``--flag`` nudge actionable. A commit older
    than the newest event has been sitting there across later spec activity,
    so re-nudging on every run is noise."""
    if not events:
        return True
    if not commit_ts:
        return False
    newest = max((e.timestamp for e in events if e.timestamp), default="")
    return commit_ts > newest


def run(root: Path, args: dict[str, Any]) -> int:
    """Run the impact command."""
    resolve_id = args.get("resolve")
    filter_id = args.get("artifact_id")
    do_flag = args.get("flag", False)

    if resolve_id:
        result = resolve_suspect(root, resolve_id, resolved_by="user")
        if result["ok"]:
            if result.get("message"):
                # Idempotent resolve: nothing was suspect on the artifact.
                # Say so instead of claiming a resolution (exit 0 either way);
                # stale open events that still named it are closed and counted.
                closed = int(result.get("events_closed", 0) or 0)
                if closed:
                    print(f"{YELLOW}⚠ {result['message']} — closed {closed} stale "
                          f"impact-log event(s) that still named it{NC}")
                else:
                    print(f"{YELLOW}⚠ {result['message']} — nothing to resolve{NC}")
                return 0
            print(f"{GREEN}✓ Resolved suspect flag on {resolve_id}{NC}")
            return 0
        else:
            print(f"{RED}✗ {result.get('error', result.get('message', 'Unknown error'))}{NC}")
            return 1

    events = load_impact_events(root)
    all_events = events
    all_artifacts = discover_artifacts(root)
    suspects = [a for a in all_artifacts if a.suspect]
    currently_suspect = {a.id for a in suspects}

    if filter_id:
        relevant_events = [e for e in events if e.changed == filter_id and not e.resolved]
        relevant_suspect_ids = set()
        for e in relevant_events:
            for s in e.flagged_suspects:
                relevant_suspect_ids.add(s.get("artifact", ""))
        suspects = [a for a in suspects if a.id in relevant_suspect_ids]
        events = relevant_events

    # An event that flagged nothing has nothing to resolve: minor updates and
    # split/merge records never count as "unresolved", so a healthy repo no
    # longer reports "0 artifacts / oldest flag Nd ago" forever. Likewise a
    # flag that was cleared outside --resolve (legacy hand edit) is not an
    # open flag: only entries whose artifact is suspect right now count.
    unresolved_events = [
        e for e in events
        if not e.resolved
        and any(s.get("artifact", "") in currently_suspect for s in e.flagged_suspects)
    ]

    # Detect source file changes before the early return so the Source File
    # Impact section renders even when there are no pre-existing suspect flags.
    source_changes, head_sha, head_ts = _detect_source_file_changes(root)
    source_matches = []
    if source_changes:
        index = build_output_file_index(root)
        source_matches = query_reverse_impact(root, source_changes, index)

    if not suspects and not unresolved_events and not source_matches:
        print("No unresolved suspect flags")
        return 0

    if suspects or unresolved_events:
        source_groups: dict[str, list[dict[str, str]]] = {}
        for event in unresolved_events:
            source = event.changed
            for s in event.flagged_suspects:
                if s.get("artifact", "") not in currently_suspect:
                    continue
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

    if source_matches:
        origin = f"from last commit {head_sha[:7]}" if head_sha else "from last commit"
        if head_ts:
            origin += f" ({_format_age(head_ts)})"
        if do_flag:
            flagged_ids = flag_suspects_from_matches(root, source_matches)
            print(f"\n{BOLD}Source File Impact{NC} ({len(source_matches)} match(es), "
                  f"{len(flagged_ids)} artifact(s) flagged) — {origin}\n")
        else:
            print(f"\n{BOLD}Source File Impact{NC} ({len(source_matches)} match(es)) "
                  f"— {origin}, informational\n")

        by_artifact: dict[str, list] = {}
        for m in source_matches:
            by_artifact.setdefault(m.artifact_id, []).append(m)

        shown = sorted(by_artifact.items())
        hidden = shown[_SOURCE_IMPACT_MAX_ARTIFACTS:]
        for art_id, file_matches in shown[:_SOURCE_IMPACT_MAX_ARTIFACTS]:
            print(f"  Artifact: {BOLD}{YELLOW}{art_id}{NC}")
            for m in file_matches:
                match_label = f"({m.match_type}: {m.pattern})"
                print(f"    ← {m.file_path} {match_label}")
            print()
        if hidden:
            hidden_files = sum(len(fm) for _, fm in hidden)
            print(f"  … and {len(hidden)} more artifact(s) ({hidden_files} file match(es)) "
                  f"not listed\n")

        if do_flag:
            print("To resolve: specflow change-impact --resolve <ARTIFACT_ID>")
        elif _commit_is_newer_than_log(head_ts, all_events):
            print("To flag these artifacts: specflow change-impact --flag")
        else:
            print(f"{CYAN}ℹ This commit predates the newest impact-log entry — "
                  f"nothing new to flag.{NC}")

    return 0
