"""CLI handler for 'specflow fingerprint-refresh' — minor edit fingerprint update without cascade."""

from pathlib import Path
from typing import Any

from specflow.lib.artifacts import parse_artifact
from specflow.lib.display import RED, GREEN, NC
from specflow.lib.impact import propagate_suspects


def run(root: Path, args: dict[str, Any]) -> int:
    """Run the tweak command — recompute fingerprint as minor, skip suspect cascade."""
    filepath = args.get("filepath", "")
    if not filepath:
        print(f"{RED}✗ No file path provided{NC}")
        return 1

    target = Path(filepath)
    if not target.exists():
        print(f"{RED}✗ File not found: {filepath}{NC}")
        return 1

    artifact = parse_artifact(target)
    if artifact is None:
        print(f"{RED}✗ Cannot parse artifact at {filepath}{NC}")
        return 1

    result = propagate_suspects(root, artifact.id, force_minor=True)

    if not result["ok"]:
        print(f"{RED}✗ {result.get('error', 'Unknown error')}{NC}")
        return 1

    if result.get("changed", False):
        print(f"{GREEN}✓ Tweaked {artifact.id}{NC} — fingerprint updated (minor, no cascade)")
    else:
        print(f"{GREEN}✓ {artifact.id}{NC} — no fingerprint change detected")

    return 0
