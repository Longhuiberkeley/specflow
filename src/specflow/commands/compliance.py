"""CLI handler for 'specflow compliance' — report coverage and gaps against standards."""

from pathlib import Path
from typing import Any

from specflow.lib import standards as standards_lib


_SEPARATOR = "─" * 58


def _list_available_presets() -> list[str]:
    """Return the names of built-in packs bundled with the package."""
    packs_dir = Path(__file__).parent.parent / "packs"
    if not packs_dir.exists():
        return []
    return sorted(
        p.name for p in packs_dir.iterdir()
        if p.is_dir() and not p.name.startswith("_") and (p / "pack.yaml").exists()
    )


def run(root: Path, args: dict[str, Any]) -> int:
    """Run the compliance command."""
    standard_name = args.get("standard")
    result = standards_lib.check_compliance(root, standard_name)

    if not result["ok"]:
        print(f"\033[0;31m✗ {result['error']}\033[0m")
        available = result.get("available") or []
        if not available:
            presets = _list_available_presets()
            if presets:
                print(f"  Available presets: {', '.join(presets)}")
        elif len(available) > 1:
            print(f"  Installed standards: {', '.join(available)}")
        return 1

    standard = result["standard"]
    title = result.get("title") or ""
    total = result["total_clauses"]
    covered = result["covered"]
    uncovered = result["uncovered"]

    header = f"Compliance Report: {standard}"
    if title:
        header += f" — {title}"
    print(f"\n\033[1m{header}\033[0m")
    print(_SEPARATOR)

    print(f"  Covered Clauses ({len(covered)}/{total}):")
    if not covered:
        print("    (none)")
    else:
        for entry in covered:
            print(f"    \033[0;32m✓\033[0m {entry['clause_id']}  {entry['clause_title']}")
            art_ids = entry.get("artifacts", [])
            if art_ids:
                print(f"        → {', '.join(art_ids)}")
    print()

    print(f"  Compliance Gaps ({len(uncovered)} uncovered):")
    if not uncovered:
        print("    (none)")
    else:
        for entry in uncovered:
            print(f"    \033[0;31m✗\033[0m {entry['clause_id']}  {entry['clause_title']}")
    print()

    print(_SEPARATOR)
    pct = (len(covered) * 100 // total) if total else 0
    print(f"  Coverage: {len(covered)}/{total} clauses ({pct}%)")
    return 0
