"""CLI handler for 'specflow baseline' — create and compare immutable baselines."""

from pathlib import Path
from typing import Any

from specflow.lib import baselines as baselines_lib
from specflow.lib import evidence as evidence_lib


_SEPARATOR = "─" * 58


def _run_create(root: Path, args: dict[str, Any]) -> int:
    name = args.get("baseline_name", "")
    if not name:
        print("\033[0;31m✗ Baseline name is required\033[0m")
        print("Usage: specflow baseline create <name>")
        return 1

    result = baselines_lib.create_baseline(root, name)
    if not result["ok"]:
        print(f"\033[0;31m✗ {result['error']}\033[0m")
        return 1

    git_ref = result.get("git_ref") or "(no git ref)"
    print(f"\033[0;32m✓ Baseline '{name}' created ({result['path']})\033[0m")
    print(f"  Artifacts: {result['artifact_count']} | Git ref: {git_ref}")

    if args.get("evidence"):
        ev_result = evidence_lib.generate_evidence_report(root, name)
        if ev_result["ok"]:
            print(f"\033[0;32m✓ Evidence report generated ({ev_result['path']})\033[0m")
        else:
            print(f"\033[0;31m✗ Evidence report failed: {ev_result['error']}\033[0m")
            return 1

    return 0


def _print_section(title: str, entries: list[str]) -> None:
    print(f"  {title} ({len(entries)}):")
    if not entries:
        print("    (none)")
    else:
        for line in entries:
            print(f"    {line}")
    print()


def _run_diff(root: Path, args: dict[str, Any]) -> int:
    name_a = args.get("baseline_a", "")
    name_b = args.get("baseline_b", "")
    if not name_a or not name_b:
        print("\033[0;31m✗ Two baseline names are required\033[0m")
        print("Usage: specflow baseline diff <name-a> <name-b>")
        return 1

    result = baselines_lib.diff_baselines(root, name_a, name_b)
    if not result["ok"]:
        print(f"\033[0;31m✗ {result['error']}\033[0m")
        return 1

    print(f"\n\033[1mBaseline Diff: {name_a} → {name_b}\033[0m")
    print(_SEPARATOR)

    added = result["added"]
    removed = result["removed"]
    status_changed = result["status_changed"]
    fp_changed = result["fingerprint_changed"]

    _print_section(
        "Added",
        [f"+ {e['id']}  [{e['status']}]  {e['title']}" for e in added],
    )
    _print_section(
        "Removed",
        [f"- {e['id']}  [{e['status']}]  {e['title']}" for e in removed],
    )
    _print_section(
        "Status Changed",
        [f"~ {e['id']}  {e['old']} → {e['new']}" for e in status_changed],
    )
    _print_section(
        "Content Changed",
        [
            f"~ {e['id']}  fingerprint changed (status: {e['status']})"
            for e in fp_changed
        ],
    )

    print(_SEPARATOR)
    print(
        f"  Summary: {len(added)} added, {len(removed)} removed, "
        f"{len(status_changed)} status changes, {len(fp_changed)} content changes"
    )
    return 0


def run(root: Path, args: dict[str, Any]) -> int:
    """Run the baseline command (create or diff)."""
    sub = args.get("baseline_subcommand")
    if sub == "create":
        return _run_create(root, args)
    if sub == "diff":
        return _run_diff(root, args)

    print("Usage:")
    print("  specflow baseline create <name>")
    print("  specflow baseline diff <name-a> <name-b>")
    existing = baselines_lib.list_baselines(root)
    if existing:
        print("\nExisting baselines:")
        for n in existing:
            print(f"  - {n}")
    return 1
