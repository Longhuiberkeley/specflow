"""specflow brief — one-call deterministic recall digest.

Fuses already-existing data into a single compact, scannable digest so a fresh
agent can reconstruct project state in one command instead of orchestrating
status + index scans + state.yaml + git log + suspect checks + wave planning by
hand. Deterministic aggregation only — no salience ranking, no compaction.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from specflow.lib import artifacts as art_lib
from specflow.lib import config as config_lib
from specflow.lib.waves import compute_waves, filter_executable_stories
from specflow.lib.display import RED, GREEN, YELLOW, CYAN, BOLD, NC

# Category → the prefixes that belong to it, in lifecycle order.
_CATEGORY_ORDER = ["spec", "work", "review", "research"]


def _recent_changes(root: Path, since: str) -> list[str]:
    """One-line-per-commit log of changes touching _specflow/ since `since`."""
    try:
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--pretty=format:%h %ad %s",
             "--date=short", "--", "_specflow/"],
            cwd=str(root), capture_output=True, text=True, timeout=15,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []
    return [ln for ln in result.stdout.splitlines() if ln.strip()]


def run(root: Path, args: dict[str, Any]) -> int:
    root = root.resolve()
    since = args.get("since") or "7 days ago"

    config = config_lib.read_config(root)
    state = config_lib.read_state(root)
    if not config or not state:
        print(f"{RED}✗ SpecFlow is not initialized here. Run 'uv run specflow init'.{NC}")
        return 1

    project_name = config.get("project", {}).get("name", "unknown")
    phase = state.get("current", "idle")

    artifacts = art_lib.discover_artifacts(root)

    # Per-category counts with status breakdown — the index summary.
    by_cat_status: dict[str, dict[str, int]] = {}
    schema_dir = root / ".specflow" / "schema"
    prefix_to_cat: dict[str, str] = {}
    if schema_dir.exists():
        import yaml
        for yf in schema_dir.glob("*.yaml"):
            try:
                sch = yaml.safe_load(yf.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(sch, dict) and sch.get("prefix"):
                prefix_to_cat[sch["prefix"]] = sch.get("category", "spec")

    for art in artifacts:
        prefix = art_lib.get_prefix_from_id(art.id)
        cat = prefix_to_cat.get(prefix, "spec")
        status = art.status or "draft"
        by_cat_status.setdefault(cat, {}).setdefault(status, 0)
        by_cat_status[cat][status] += 1

    suspects = [a for a in artifacts if a.suspect]

    # In-scope wave (next executable wave), best-effort.
    stories = filter_executable_stories(art_lib.discover_artifacts(root, "story"))
    next_wave: list[str] = []
    if stories:
        wave_result = compute_waves(stories)
        if wave_result.get("ok") and wave_result.get("waves"):
            next_wave = wave_result["waves"][0]

    recent = _recent_changes(root, since)

    # ── Render ──────────────────────────────────────────────────
    print(f"\n{CYAN}SpecFlow Brief{NC} — {BOLD}{project_name}{NC}")
    print(f"{CYAN}{'─' * 50}{NC}")
    print(f"  Phase: {BOLD}{phase}{NC}   ({len(artifacts)} artifacts)")

    print(f"\n  {BOLD}Inventory{NC}")
    for cat in _CATEGORY_ORDER:
        statuses = by_cat_status.get(cat)
        if not statuses:
            continue
        parts = [f"{n} {s}" for s, n in sorted(statuses.items())]
        total = sum(statuses.values())
        print(f"    {cat:<9} {total:>3}  ({', '.join(parts)})")

    if suspects:
        ids = ", ".join(a.id for a in suspects[:8])
        if len(suspects) > 8:
            ids += f" (+{len(suspects) - 8} more)"
        print(f"\n  {YELLOW}⚠ Suspects ({len(suspects)}){NC}: {ids}")
        print(f"    Resolve: specflow change-impact --resolve <ID>  |  "
              f"specflow defect-from-suspect <ID> --req <REQ>")
    else:
        print(f"\n  {GREEN}✓ No unresolved suspects{NC}")

    print(f"\n  {BOLD}In-scope (next wave){NC}")
    if next_wave:
        print(f"    {', '.join(next_wave)}")
    else:
        print(f"    (no approved stories ready to execute)")

    print(f"\n  {BOLD}Recent _specflow/ changes{NC} (since {since})")
    if recent:
        for ln in recent[:10]:
            print(f"    {ln}")
        if len(recent) > 10:
            print(f"    … {len(recent) - 10} more commits")
    else:
        print(f"    (none)")

    print(f"\n  → Drill down: specflow trace <ID>  |  specflow status  |  "
          f"specflow artifact-lint")
    print()
    return 0
