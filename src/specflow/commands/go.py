"""CLI handler for 'specflow go' — parallel subagent execution."""

from pathlib import Path
from typing import Any

from specflow.lib.artifacts import discover_artifacts
from specflow.lib.display import RED, GREEN, YELLOW, BOLD, NC
from specflow.lib.executor import run_execution
from specflow.lib.waves import compute_waves, filter_executable_stories


def run(root: Path, args: dict[str, Any]) -> int:
    """Run the go command — execute approved stories in parallel waves."""
    dry_run = args.get("dry_run", False)
    timeout = args.get("timeout", 600)
    wave_filter = args.get("wave")

    # Load approved stories
    all_stories = discover_artifacts(root, "story")
    stories = filter_executable_stories(all_stories)

    if not stories:
        print(f"{YELLOW}No approved stories found for execution.{NC}")
        print("Approve stories first: specflow update STORY-XXX --status approved")
        return 1

    wave_result = compute_waves(stories)
    if not wave_result["ok"]:
        print(f"{RED}✗ {wave_result['error']}{NC}")
        if "cycle" in wave_result:
            print(f"  Cycle: {' -> '.join(wave_result['cycle'])}")
        return 1

    waves = wave_result["waves"]

    # Filter to a specific wave if requested
    if wave_filter is not None:
        if wave_filter < 1 or wave_filter > len(waves):
            print(f"{RED}✗ Wave {wave_filter} not found. Available: 1-{len(waves)}{NC}")
            return 1
        stories = [s for s in stories if s.id in waves[wave_filter - 1]]
        waves = [waves[wave_filter - 1]]

    if dry_run:
        print(f"\n{BOLD}Execution Plan{NC} — {len(waves)} wave(s), {len(stories)} stories\n")
        for i, wave in enumerate(waves, 1):
            print(f"  Wave {i}: {', '.join(wave)}")
        print(f"\nRun without --dry-run to execute.")
        return 0

    # Execute
    result = run_execution(root, stories=stories, timeout=timeout, dry_run=False)

    if not result["ok"]:
        print(f"{RED}✗ {result.get('error', 'Execution failed')}{NC}")
        return 1

    # Print summary
    completed = result.get("completed", [])
    failed = result.get("failed", [])
    deferred = result.get("deferred", [])

    print(f"\n{BOLD}Execution Complete{NC} — {result['total_waves']} wave(s)")
    if completed:
        print(f"  {GREEN}Completed{NC}: {', '.join(completed)}")
    if failed:
        print(f"  {RED}Failed{NC}: {', '.join(failed)}")
    if deferred:
        print(f"  {YELLOW}Deferred{NC}: {', '.join(deferred)}")

    return 1 if failed else 0
