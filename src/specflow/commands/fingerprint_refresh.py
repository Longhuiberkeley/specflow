"""CLI handler for 'specflow fingerprint-refresh' — minor edit fingerprint update without cascade."""

from pathlib import Path
from typing import Any

from specflow.lib.artifacts import parse_artifact
from specflow.lib.impact import propagate_suspects


def run(root: Path, args: dict[str, Any]) -> int:
    """Run the tweak command — recompute fingerprint as minor, skip suspect cascade."""
    filepath = args.get("filepath", "")
    if not filepath:
        print("\033[0;31m✗ No file path provided\033[0m")
        return 1

    target = Path(filepath)
    if not target.exists():
        print(f"\033[0;31m✗ File not found: {filepath}\033[0m")
        return 1

    artifact = parse_artifact(target)
    if artifact is None:
        print(f"\033[0;31m✗ Cannot parse artifact at {filepath}\033[0m")
        return 1

    result = propagate_suspects(root, artifact.id, force_minor=True)

    if not result["ok"]:
        print(f"\033[0;31m✗ {result.get('error', 'Unknown error')}\033[0m")
        return 1

    if result.get("changed", False):
        print(f"\033[0;32m✓ Tweaked {artifact.id}\033[0m — fingerprint updated (minor, no cascade)")
    else:
        print(f"\033[0;32m✓ {artifact.id}\033[0m — no fingerprint change detected")

    return 0
