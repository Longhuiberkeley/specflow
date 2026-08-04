"""CLI handler for 'specflow fingerprint-refresh' — minor edit fingerprint update without cascade."""

from pathlib import Path
from typing import Any

from specflow.lib.artifacts import parse_artifact, resolve_link_target
from specflow.lib.display import RED, GREEN, YELLOW, NC
from specflow.lib.impact import propagate_suspects
from specflow.lib import lint as lint_lib


def _report_stale(root: Path) -> int:
    """W3.1: with no targets, LIST stale fingerprints without modifying anything.

    Report-only by design — this preserves the explicit-repair doctrine (a
    present-but-wrong fingerprint is a meaningful drift signal; silently
    auto-fixing every stale one would destroy that signal). Always exits 0.
    """
    from specflow.lib import artifacts as art_lib
    artifacts = art_lib.discover_artifacts(root)
    stale = []
    for art in artifacts:
        if not art.fingerprint:
            continue
        if not lint_lib.validate_fingerprint(art)["match"]:
            stale.append(art.id)
    if not stale:
        print(f"{GREEN}✓ No stale fingerprints.{NC} Pass artifact IDs to refresh specific ones.")
        return 0
    print(f"{YELLOW}⚠ {len(stale)} stale fingerprint(s):{NC}")
    for art_id in stale:
        print(f"  - {art_id}")
    print(f"Pass IDs to refresh, e.g. {GREEN}specflow fingerprint-refresh {' '.join(stale[:5])}{NC}")
    return 0


def run(root: Path, args: dict[str, Any]) -> int:
    """Run the tweak command — recompute fingerprint as minor, skip suspect cascade.

    Accepts multiple targets, each an artifact ID (preferred) or a file path.
    A target is resolved as: (1) known artifact ID via resolve_link_target,
    (2) an existing file path. Unknown targets are reported per-line and
    skipped. Exits non-zero only when *every* target failed — a partial success
    still returns 0 so batch agents don't silently abort on one bad target.

    With NO targets, lists stale fingerprints without modifying anything (W3.1).
    """
    targets = args.get("targets") or []
    if not targets:
        return _report_stale(root)

    total = len(targets)
    failures = 0

    for target_str in targets:
        # Resolve: artifact ID first (preferred), then literal file path.
        resolved = resolve_link_target(root, target_str)
        if resolved is not None:
            target_path = resolved
        elif Path(target_str).exists():
            target_path = Path(target_str)
        else:
            print(f"{RED}✗ Not found: {target_str} "
                  f"(not a known artifact ID or existing file){NC}")
            failures += 1
            continue

        artifact = parse_artifact(target_path)
        if artifact is None:
            print(f"{RED}✗ Cannot parse artifact at {target_path}{NC}")
            failures += 1
            continue

        result = propagate_suspects(root, artifact.id, force_minor=True)

        if not result["ok"]:
            print(f"{RED}✗ {artifact.id}: {result.get('error', 'Unknown error')}{NC}")
            failures += 1
            continue

        if result.get("changed", False):
            print(f"{GREEN}✓ Tweaked {artifact.id}{NC} — fingerprint updated (minor, no cascade)")
        else:
            print(f"{GREEN}✓ {artifact.id}{NC} — no fingerprint change detected")

    # Non-zero only if ALL targets failed; partial success is still exit 0.
    return 1 if failures == total else 0
