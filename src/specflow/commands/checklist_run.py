"""CLI handler for 'specflow checklist-run' — context-specific review."""

from pathlib import Path
from typing import Any

from specflow.lib.artifacts import Artifact, discover_artifacts, resolve_link_target, parse_artifact
from specflow.lib.checklists import (
    assemble_checklist,
    persist_results,
    run_automated_pass,
    update_artifact_checklists_applied,
)
from specflow.lib.challenge import extract_proactive_items, format_proactive_prompt
from specflow.lib.dedup import find_duplicates, write_candidates_file
from specflow.lib.display import RED, GREEN, YELLOW, BOLD, NC


def _check_artifact(
    root: Path,
    artifact: Artifact,
    gate: str | None,
    proactive: bool,
) -> int:
    """Run check on a single artifact. Returns 0 if no blocking failures."""
    assembled = assemble_checklist(root, artifact, phase_transition=gate)

    print(f"\n{BOLD}{artifact.id}{NC} — {artifact.title}")
    print(f"  Type: {artifact.type} | Tags: {artifact.tags}")
    print(f"  Sources: {', '.join(assembled.sources) if assembled.sources else '(none)'}")
    print(f"  Items: {len(assembled.items)} ({sum(1 for i in assembled.items if i.automated)} automated, "
          f"{sum(1 for i in assembled.items if not i.automated)} agent-judged)")

    if not assembled.items:
        print(f"  {YELLOW}Warning: No checklists matched this artifact.{NC}")
        # Persist the honest incomplete outcome instead of returning with no
        # record (which is indistinguishable from a successful no-op).
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        checklist_id = f"check-{artifact.id}"
        persist_results(root, artifact.id, checklist_id, [])
        update_artifact_checklists_applied(root, artifact.id, checklist_id, ts)
        return 0

    # Pass 1: Automated
    auto_results = run_automated_pass(root, assembled, artifact)
    blocking_failed = any(r.result == "failed" for r in auto_results)

    if auto_results:
        print("\n  Automated checks:")
        for r in auto_results:
            symbol = f"{GREEN}✓{NC}" if r.result == "passed" else f"{RED}✗{NC}"
            detail = f" — {r.detail}" if r.detail else ""
            print(f"    {symbol} {r.item_id}{detail}")

    if blocking_failed:
        print(f"\n  {RED}Blocking automated check failed — agent checks skipped.{NC}")

    # Agent-judged items (listed for the host agent to evaluate)
    llm_items = [i for i in assembled.items if not i.automated]
    if llm_items and not blocking_failed:
        print(f"\n  Agent-judged checks ({len(llm_items)} pending):")
        for item in llm_items:
            mode_label = f" [{item.mode}]" if item.mode != "standard" else ""
            print(f"    • [{item.severity}]{mode_label} {item.check}")

    # Proactive challenges
    if proactive and not blocking_failed:
        proactive_items = extract_proactive_items(assembled)
        if proactive_items:
            print(f"\n  Proactive challenges ({len(proactive_items)}):")
            prompt = format_proactive_prompt(artifact, proactive_items)
            for item in proactive_items:
                print(f"    ⚡ {item.check}")

    # Persist results
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    checklist_id = f"check-{artifact.id}"
    persist_results(root, artifact.id, checklist_id, auto_results)
    update_artifact_checklists_applied(root, artifact.id, checklist_id, ts)

    return 1 if blocking_failed else 0


def _run_dedup(root: Path) -> int:
    """Tier 1 + tier 2 dedup across all artifacts. Writes candidates file for the skill."""
    artifacts = discover_artifacts(root)
    candidates = find_duplicates(artifacts)
    out_path = write_candidates_file(root, candidates)

    rel = out_path.relative_to(root) if out_path.is_absolute() else out_path
    print(f"{BOLD}SpecFlow Dedup{NC} — analyzed {len(artifacts)} artifact(s)")

    if not candidates:
        print(f"  {GREEN}✓{NC} No duplicate candidates found")
        print(f"  Candidates file: {rel}")
        return 0

    by_conf: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for c in candidates:
        by_conf[c.confidence] = by_conf.get(c.confidence, 0) + 1

    print(f"  {YELLOW}{len(candidates)} candidate pair(s){NC} — "
          f"{by_conf.get('high', 0)} high, {by_conf.get('medium', 0)} medium, {by_conf.get('low', 0)} low")

    for c in candidates[:10]:
        a, b = c.pair
        print(f"    [{c.confidence}] {a} <-> {b}  "
              f"tag={c.tag_jaccard:.2f}  tfidf={c.tfidf_cosine:.2f}")
    if len(candidates) > 10:
        print(f"    ... and {len(candidates) - 10} more")

    print(f"  Candidates file: {rel}")
    print("  Review with the check skill for agent confirmation (tier 3).")
    return 0


def run(root: Path, args: dict[str, Any]) -> int:
    """Run the check command."""
    if args.get("dedup", False):
        return _run_dedup(root)

    artifact_id = args.get("artifact_id")
    check_all = args.get("all", False)
    gate = args.get("gate")
    proactive = args.get("proactive", False)

    artifacts_to_check: list[Artifact] = []

    if check_all:
        artifacts_to_check = discover_artifacts(root)
    elif artifact_id:
        file_path = resolve_link_target(root, artifact_id)
        if file_path is None:
            print(f"{RED}✗ Artifact '{artifact_id}' not found{NC}")
            return 1
        art = parse_artifact(file_path)
        if art is None:
            print(f"{RED}✗ Cannot parse artifact at {file_path}{NC}")
            return 1
        artifacts_to_check = [art]
    else:
        print("Usage: specflow checklist-run <ARTIFACT_ID> or specflow checklist-run --all")
        return 1

    print(f"{BOLD}SpecFlow Checklist Run{NC} — reviewing {len(artifacts_to_check)} artifact(s)")

    total_blocking = 0
    for art in artifacts_to_check:
        result = _check_artifact(root, art, gate, proactive)
        total_blocking += result

    if total_blocking:
        print(f"\n{RED}{total_blocking} artifact(s) have blocking failures.{NC}")
        return 1

    print(f"\n{GREEN}All automated checks passed.{NC}")
    return 0
