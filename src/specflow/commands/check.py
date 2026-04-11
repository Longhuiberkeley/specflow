"""CLI handler for 'specflow check' — context-specific review."""

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


def _check_artifact(
    root: Path,
    artifact: Artifact,
    gate: str | None,
    proactive: bool,
) -> int:
    """Run check on a single artifact. Returns 0 if no blocking failures."""
    assembled = assemble_checklist(root, artifact, phase_transition=gate)

    print(f"\n\033[1m{artifact.id}\033[0m — {artifact.title}")
    print(f"  Type: {artifact.type} | Tags: {artifact.tags}")
    print(f"  Sources: {', '.join(assembled.sources) if assembled.sources else '(none)'}")
    print(f"  Items: {len(assembled.items)} ({sum(1 for i in assembled.items if i.automated)} automated, "
          f"{sum(1 for i in assembled.items if not i.automated)} LLM-judged)")

    if not assembled.items:
        print("  \033[0;33mWarning: No checklists matched this artifact.\033[0m")
        return 0

    # Pass 1: Automated
    auto_results = run_automated_pass(root, assembled, artifact)
    blocking_failed = any(r.result == "failed" for r in auto_results)

    if auto_results:
        print("\n  Automated checks:")
        for r in auto_results:
            symbol = "\033[0;32m✓\033[0m" if r.result == "passed" else "\033[0;31m✗\033[0m"
            detail = f" — {r.detail}" if r.detail else ""
            print(f"    {symbol} {r.item_id}{detail}")

    if blocking_failed:
        print("\n  \033[0;31mBlocking automated check failed — LLM checks skipped.\033[0m")

    # Pass 2: LLM-judged items (listed for the skill to evaluate)
    llm_items = [i for i in assembled.items if not i.automated]
    if llm_items and not blocking_failed:
        print(f"\n  LLM-judged checks ({len(llm_items)} pending):")
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


def run(root: Path, args: dict[str, Any]) -> int:
    """Run the check command."""
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
            print(f"\033[0;31m✗ Artifact '{artifact_id}' not found\033[0m")
            return 1
        art = parse_artifact(file_path)
        if art is None:
            print(f"\033[0;31m✗ Cannot parse artifact at {file_path}\033[0m")
            return 1
        artifacts_to_check = [art]
    else:
        print("Usage: specflow check <ARTIFACT_ID> or specflow check --all")
        return 1

    print(f"\033[1mSpecFlow Check\033[0m — reviewing {len(artifacts_to_check)} artifact(s)")

    total_blocking = 0
    for art in artifacts_to_check:
        result = _check_artifact(root, art, gate, proactive)
        total_blocking += result

    if total_blocking:
        print(f"\n\033[0;31m{total_blocking} artifact(s) have blocking failures.\033[0m")
        return 1

    print(f"\n\033[0;32mAll automated checks passed.\033[0m")
    return 0
