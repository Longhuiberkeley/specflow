"""CLI handler for 'specflow go' — parallel subagent execution."""

from pathlib import Path
from typing import Any

from specflow.lib.artifacts import discover_artifacts
from specflow.lib.executor import run_execution
from specflow.lib.waves import compute_waves, filter_executable_stories


def run(root: Path, args: dict[str, Any]) -> int:
    """Run the go command — execute approved stories in parallel waves."""
    dry_run = args.get("dry_run", False)
    timeout = args.get("timeout", 600)

    # Load approved stories
    all_stories = discover_artifacts(root, "story")
    stories = filter_executable_stories(all_stories)

    if not stories:
        print("\033[0;33mNo approved stories found for execution.\033[0m")
        print("Approve stories first: uv run specflow update STORY-XXX --status approved")
        return 1

    if dry_run:
        wave_result = compute_waves(stories)
        if not wave_result["ok"]:
            print(f"\033[0;31m✗ {wave_result['error']}\033[0m")
            if "cycle" in wave_result:
                print(f"  Cycle: {' -> '.join(wave_result['cycle'])}")
            return 1

        waves = wave_result["waves"]
        print(f"\n\033[1mExecution Plan\033[0m — {len(waves)} wave(s), {len(stories)} stories\n")
        for i, wave in enumerate(waves, 1):
            print(f"  Wave {i}: {', '.join(wave)}")
        print(f"\nRun without --dry-run to execute.")
        return 0

    # Execute
    result = run_execution(root, stories=stories, timeout=timeout, dry_run=False)

    if not result["ok"]:
        print(f"\033[0;31m✗ {result.get('error', 'Execution failed')}\033[0m")
        return 1

    # Print summary
    completed = result.get("completed", [])
    failed = result.get("failed", [])
    deferred = result.get("deferred", [])

    print(f"\n\033[1mExecution Complete\033[0m — {result['total_waves']} wave(s)")
    if completed:
        print(f"  \033[0;32mCompleted\033[0m: {', '.join(completed)}")
    if failed:
        print(f"  \033[0;31mFailed\033[0m: {', '.join(failed)}")
    if deferred:
        print(f"  \033[0;33mDeferred\033[0m: {', '.join(deferred)}")

    return 1 if failed else 0
