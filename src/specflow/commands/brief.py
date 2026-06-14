"""specflow brief — one-call deterministic recall digest.

Fuses already-existing data into a single compact, scannable digest so a fresh
agent can reconstruct project state in one command instead of orchestrating
status + index scans + state.yaml + git log + suspect checks + wave planning by
hand. Deterministic aggregation only — no salience ranking, no compaction.
"""

from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from specflow.lib import artifacts as art_lib
from specflow.lib import config as config_lib
from specflow.lib.waves import compute_waves, filter_executable_stories
from specflow.lib.display import RED, GREEN, YELLOW, CYAN, BOLD, NC

# Category → the prefixes that belong to it, in lifecycle order.
_CATEGORY_ORDER = ["spec", "work", "review", "research"]


def _adoption_summary(root: Path, artifacts: list[art_lib.Artifact]) -> dict | None:
    """Derive adoption progress from the graph (no state file).

    Returns None when adoption isn't in flight (no `backfilled` tags present),
    so greenfield projects pay zero cost. Otherwise returns coverage %, the
    per-type backfilled count, and the biggest un-adopted cluster — all derived
    from existing primitives (orphan-code scan + tag scan + cluster grouping).
    """
    backfilled = [a for a in artifacts if "backfilled" in (a.tags or [])]
    if not backfilled:
        return None

    from specflow.lib.orphans import find_orphan_code

    oc = find_orphan_code(root)
    total = oc["total_count"]
    ref_count = oc["referenced_count"]
    coverage = (100.0 * ref_count / total) if total else 100.0

    # Biggest un-adopted cluster: bucket orphans by first 2 path components.
    buckets: Counter[str] = Counter()
    for f in oc["orphan_files"]:
        try:
            rel = f.relative_to(root)
        except ValueError:
            rel = Path(f.name)
        if len(rel.parts) >= 2:
            top = "/".join(rel.parts[:2])
        elif len(rel.parts) >= 1:
            top = rel.parts[0]
        else:
            top = "(root)"
        buckets[top] += 1
    biggest = buckets.most_common(1)[0] if buckets else (None, 0)

    by_type: Counter[str] = Counter()
    for a in backfilled:
        by_type[art_lib.get_prefix_from_id(a.id) or a.type] += 1

    # Depth distribution for ARCHs: skeleton (no parent REQ) vs full (has REQ).
    archs = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "ARCH"]
    skeleton_archs = 0
    full_archs = 0
    for arch in archs:
        has_parent = any(
            lk.role == "derives_from" and art_lib.get_prefix_from_id(lk.target) == "REQ"
            for lk in arch.links
        ) or any(
            lk.role == "refined_by" and lk.target == arch.id
            for a2 in artifacts if art_lib.get_prefix_from_id(a2.id) == "REQ"
            for lk in a2.links
        )
        if has_parent:
            full_archs += 1
        else:
            skeleton_archs += 1

    return {
        "coverage_pct": coverage,
        "backfilled_count": len(backfilled),
        "by_type": dict(by_type),
        "biggest_cluster": biggest[0],
        "biggest_cluster_count": biggest[1],
        "orphan_count": len(oc["orphan_files"]),
        "skeleton_archs": skeleton_archs,
        "full_archs": full_archs,
    }


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
    adoption = _adoption_summary(root, artifacts)

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

    if adoption is not None:
        type_parts = [f"{n} {t}" for t, n in sorted(adoption["by_type"].items())]
        print(f"\n  {BOLD}Adoption{NC} (in progress)")
        print(f"    Coverage: {BOLD}{adoption['coverage_pct']:.1f}%{NC}   "
              f"({adoption['backfilled_count']} backfilled: {', '.join(type_parts) or 'none'})")
        if adoption["skeleton_archs"] or adoption["full_archs"]:
            depth_parts = []
            if adoption["skeleton_archs"]:
                depth_parts.append(f"{adoption['skeleton_archs']} skeleton")
            if adoption["full_archs"]:
                depth_parts.append(f"{adoption['full_archs']} full")
            print(f"    Depth: {', '.join(depth_parts)}")
        if adoption["biggest_cluster"]:
            print(f"    Biggest un-adopted cluster: {adoption['biggest_cluster']}/ "
                  f"({adoption['biggest_cluster_count']} files)")
        print(f"    {CYAN}specflow adopt status{NC} for the per-boundary + per-artifact view")

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

    drill = "specflow trace <ID>  |  specflow status  |  specflow artifact-lint"
    if adoption is not None:
        drill += "  |  specflow adopt status"
    print(f"\n  → Drill down: {drill}")
    print()
    return 0
