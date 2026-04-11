"""CLI handler for 'specflow done' — phase closure and pattern extraction."""

from pathlib import Path
from typing import Any

from specflow.lib.artifacts import discover_artifacts
from specflow.lib.learning import close_phase, list_learned_patterns, suggest_next_phase


def run(root: Path, args: dict[str, Any]) -> int:
    """Run the done command — close the current phase."""
    auto = args.get("auto", False)
    no_patterns = args.get("no_patterns", False)

    # Show phase summary
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

    # Pattern extraction
    if not no_patterns:
        existing = list_learned_patterns(root)
        print(f"\n  Existing learned patterns: {len(existing)}")

        if not auto and implemented_stories:
            print("\n  Pattern extraction requires interactive prompts.")
            print("  Use --auto to skip prompts or --no-patterns to skip entirely.")
            print("  (In skill mode, the AI agent handles pattern extraction interactively.)")

    # Close phase
    result = close_phase(root)
    if not result["ok"]:
        print(f"\n\033[0;31m✗ {result.get('error', 'Phase closure failed')}\033[0m")
        return 1

    print(f"\n  \033[0;32m✓ Phase '{result['phase_closed']}' closed.\033[0m")

    # Suggest next
    suggestion = suggest_next_phase(root)
    print(f"  {suggestion}")

    return 0
