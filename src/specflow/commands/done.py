"""CLI handler for 'specflow done' — phase closure and pattern extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specflow.lib.artifacts import discover_artifacts
from specflow.lib.learning import (
    close_phase,
    create_pattern_from_finding,
    list_learned_patterns,
    suggest_next_phase,
    _max_patterns_per_session,
)


def _auto_extract_patterns(root: Path, stories: list) -> int:
    count = 0
    max_patterns = _max_patterns_per_session(root)
    for story in stories:
        if count >= max_patterns:
            break
        lines = [
            l.strip()
            for l in (story.body or "").splitlines()
            if l.strip() and not l.strip().startswith("#")
        ]
        if not lines:
            continue
        check_text = f"Verify {story.title}" if story.title else "Verify implementation completeness"
        reason = lines[0][:200]
        path = create_pattern_from_finding(
            root, story,
            check_text=check_text,
            reason=reason,
            severity="warning",
        )
        if path:
            count += 1
            print(f"    Created {path.name} from {story.id}")
    return count


def run(root: Path, args: dict[str, Any]) -> int:
    auto = args.get("auto", True)
    no_patterns = args.get("no_patterns", False)

    all_artifacts = discover_artifacts(root)
    stories = [a for a in all_artifacts if a.type == "story"]

    status_counts: dict[str, int] = {}
    for art in all_artifacts:
        status_counts[art.status] = status_counts.get(art.status, 0) + 1

    implemented_stories = [s for s in stories if s.status == "implemented"]

    print(f"\n\033[1mPhase Closure\033[0m")
    print(f"\n  Artifacts by status:")
    for status, count in sorted(status_counts.items()):
        print(f"    {status}: {count}")

    print(f"\n  Implemented stories: {len(implemented_stories)}")
    for s in implemented_stories:
        print(f"    • {s.id} — {s.title}")

    if not no_patterns and implemented_stories:
        existing = list_learned_patterns(root)
        print(f"\n  Existing learned patterns: {len(existing)}")

        if auto:
            count = _auto_extract_patterns(root, implemented_stories)
            if count:
                print(f"  ✓ Extracted {count} prevention pattern(s) from implemented stories")
            else:
                print("  (no new patterns extracted)")
        else:
            print("\n  Run `specflow done --auto` to extract prevention patterns from implemented stories.")
            print("  Or `specflow done --no-patterns` to skip.")

    result = close_phase(root)
    if not result["ok"]:
        print(f"\n\033[0;31m✗ {result.get('error', 'Phase closure failed')}\033[0m")
        return 1

    print(f"\n  \033[0;32m✓ Phase '{result['phase_closed']}' closed.\033[0m")

    suggestion = suggest_next_phase(root)
    print(f"  {suggestion}")

    return 0
