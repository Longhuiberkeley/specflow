"""specflow autoresearch -- Harness-agnostic research loop CLI.

Provides plan, run, review, and leaderboard subcommands for the autoresearch
pack.  The host LLM drives the iteration loop; this command handles state
mutations (artifact creation, LOOP updates, leaderboard rendering) and prints
protocol checklists that any harness can follow.
"""

from __future__ import annotations

import sys
from pathlib import Path

from specflow.lib import artifacts as art_lib
from specflow.lib.display import RED, GREEN, CYAN, YELLOW, NC, BOLD, DIM


def _find_competitions(root: Path) -> list[art_lib.Artifact]:
    artifacts = art_lib.discover_artifacts(root)
    return [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "COMP"]


def _find_loops_for_comp(root: Path, comp_id: str) -> list[art_lib.Artifact]:
    artifacts = art_lib.discover_artifacts(root)
    return [
        a for a in artifacts
        if art_lib.get_prefix_from_id(a.id) == "LOOP"
        and a.frontmatter.get("competition") == comp_id
    ]


def _find_expts_for_loop(root: Path, loop_id: str) -> list[art_lib.Artifact]:
    artifacts = art_lib.discover_artifacts(root)
    return [
        a for a in artifacts
        if art_lib.get_prefix_from_id(a.id) == "EXPT"
        and a.frontmatter.get("loop") == loop_id
    ]


def _find_findings_for_comp(root: Path, comp_id: str) -> list[art_lib.Artifact]:
    artifacts = art_lib.discover_artifacts(root)
    results = []
    for a in artifacts:
        if art_lib.get_prefix_from_id(a.id) != "FIND":
            continue
        if a.frontmatter.get("competition") == comp_id:
            results.append(a)
            continue
        for link in a.links:
            if link.target == comp_id and link.role == "belongs_to":
                results.append(a)
                break
    return results


def _resolve_comp(root: Path, args: dict) -> art_lib.Artifact | None:
    comp_id = args.get("competition")
    if comp_id:
        artifacts = art_lib.discover_artifacts(root)
        id_index = art_lib.build_id_index(artifacts)
        comp = id_index.get(comp_id)
        if not comp:
            print(f"{RED}✗ Competition '{comp_id}' not found.{NC}")
            return None
        return comp

    comps = _find_competitions(root)
    if not comps:
        print(f"{RED}✗ No competitions found. Create one with "
              f"`specflow create --type competition --title <title> ...`{NC}")
        return None
    if len(comps) == 1:
        return comps[0]

    active = [c for c in comps if c.status == "active"]
    if len(active) == 1:
        return active[0]

    print(f"{YELLOW}Multiple competitions found. Specify --competition <ID>:{NC}")
    for c in sorted(comps, key=lambda a: a.id):
        print(f"  {CYAN}{c.id}{NC}  {c.title}  [{c.status}]")
    return None


def _get_all_expts_for_comp(root: Path, comp_id: str) -> list[art_lib.Artifact]:
    loops = _find_loops_for_comp(root, comp_id)
    all_expts = []
    for loop in loops:
        all_expts.extend(_find_expts_for_loop(root, loop.id))
    return all_expts


def _run_plan(root: Path, args: dict) -> int:
    comp = _resolve_comp(root, args)
    if not comp:
        return 1

    fm = comp.frontmatter
    print(f"\n{BOLD}=== Autoresearch Plan ==={NC}\n")
    print(f"Competition:   {CYAN}{comp.id}{NC}  {comp.title}")
    print(f"Metric:        {fm.get('metric_name', '?')} ({fm.get('metric_direction', '?')})")
    print(f"Verify cmd:    {fm.get('verify_command', '(none)')}")
    guard = fm.get("guard_command")
    if guard:
        print(f"Guard cmd:     {guard} (mode: {fm.get('guard_mode', 'pass_fail')})")
    print()

    loops = _find_loops_for_comp(root, comp.id)
    running = [l for l in loops if l.status == "running"]
    draft = [l for l in loops if l.status == "draft"]

    if running:
        print(f"{YELLOW}⚠ Running LOOP detected:{NC}")
        for l in running:
            lf = l.frontmatter
            print(f"  {CYAN}{l.id}{NC}  mode={lf.get('mode', '?')}  "
                  f"iterations={lf.get('iteration_count', 0)}/{lf.get('budget', '?')}  "
                  f"best={lf.get('best_metric', '—')}")
        print()
        print("Options: attach to running LOOP / abort it first / start a new COMP")
        print()

    if draft:
        print(f"{GREEN}Draft LOOP ready to start:{NC}")
        for l in draft:
            lf = l.frontmatter
            print(f"  {CYAN}{l.id}{NC}  mode={lf.get('mode', '?')}  "
                  f"budget={lf.get('budget', '?')}")
        print()

    findings = _find_findings_for_comp(root, comp.id)
    confirmed = [f for f in findings if f.status == "confirmed"]
    if confirmed:
        print(f"{BOLD}Confirmed FINDs to load:{NC}")
        for f in confirmed:
            print(f"  {CYAN}{f.id}{NC}  {f.title}  "
                  f"confidence={f.frontmatter.get('confidence', '?')}")
        print()

    print(f"{BOLD}Setup checklist:{NC}")
    print("  1. COMP exists ✓")
    if running:
        print("  2. ⚠ Resolve concurrent LOOP before proceeding")
    else:
        print("  2. No concurrent LOOP ✓")
    print("  3. Dry-run verify command (run it now to confirm)")
    if args.get("profile"):
        print("     → Run verify 3x for noise variance probe (--profile enabled)")
    print("  4. Create or confirm LOOP in draft status")
    print("  5. Load confirmed FINDs into LOOP knowledge_input")
    print("  6. User confirms setup summary")
    print()

    if not draft and not running:
        print(f"{DIM}No LOOP artifact yet. Create one:{NC}")
        print(f"  specflow create --type loop --title \"Initial exploration\" "
              f"--competition {comp.id} --mode explore --budget 50")
        print()

    return 0


def _run_run(root: Path, args: dict) -> int:
    comp = _resolve_comp(root, args)
    if not comp:
        return 1

    loop_id = args.get("loop")
    loops = _find_loops_for_comp(root, comp.id)

    target_loop = None
    if loop_id:
        target_loop = next((l for l in loops if l.id == loop_id), None)
        if not target_loop:
            print(f"{RED}✗ LOOP '{loop_id}' not found under {comp.id}.{NC}")
            return 1
    else:
        running = [l for l in loops if l.status == "running"]
        draft = [l for l in loops if l.status == "draft"]
        if running:
            target_loop = running[0]
        elif draft:
            target_loop = draft[0]
        else:
            print(f"{RED}✗ No running or draft LOOP found for {comp.id}. "
                  f"Create one first.{NC}")
            return 1

    lf = target_loop.frontmatter
    fm = comp.frontmatter
    print(f"\n{BOLD}=== Autoresearch Loop Protocol ==={NC}\n")
    print(f"Competition:  {CYAN}{comp.id}{NC}  {comp.title}")
    print(f"LOOP:         {CYAN}{target_loop.id}{NC}  mode={lf.get('mode', 'explore')}  "
          f"budget={lf.get('budget', '?')}")
    print(f"Metric:       {fm.get('metric_name', '?')} ({fm.get('metric_direction', '?')})")
    print(f"Verify:       {fm.get('verify_command', '?')}")
    guard = fm.get("guard_command")
    if guard:
        print(f"Guard:        {guard} (mode: {fm.get('guard_mode', 'pass_fail')})")
    ic = lf.get("iteration_count", 0)
    budget = lf.get("budget", "?")
    print(f"Progress:     {ic}/{budget} iterations  "
          f"kept={lf.get('kept_count', 0)}  "
          f"discarded={lf.get('discarded_count', 0)}  "
          f"best={lf.get('best_metric', '—')}")
    print()
    print(f"{BOLD}8-Phase Protocol Checklist:{NC}")
    print("  Phase 1: Review — Read FINDs + current EXPTs + git history")
    print("  Phase 2: Ideate — Pick next change (fix crashes → exploit → explore → combine)")
    print("  Phase 3: Modify — ONE atomic change, one-sentence test")
    print("  Phase 4: Commit — git add <files> && git commit -m 'experiment(<scope>): ...'")
    print("  Phase 5: Verify — Run COMP.verify_command, extract metric")
    print("  Phase 5.1: Noise — Multi-run median if metric is noisy")
    print("  Phase 5.5: Guard — Run guard_command if defined on COMP")
    print("  Phase 6: Decide — kept / discarded / crashed / no_op")
    print("  Phase 7: Log — Create EXPT artifact, update LOOP totals")
    print("  Phase 8: Repeat or Complete — Check budget, condense every 10 iterations")
    print()
    print(f"{DIM}Full protocol: references/autonomous-loop-protocol.md{NC}")
    print(f"{DIM}Mode guide:    references/explore-exploit-protocol.md{NC}")
    print()

    return 0


def _run_review(root: Path, args: dict) -> int:
    comp = _resolve_comp(root, args)
    if not comp:
        return 1

    fm = comp.frontmatter
    print(f"\n{BOLD}=== Autoresearch Review: {comp.id} {comp.title} ==={NC}\n")

    loops = _find_loops_for_comp(root, comp.id)
    print(f"{BOLD}Loops ({len(loops)}):{NC}")
    if not loops:
        print(f"  {DIM}(none){NC}")
    for l in sorted(loops, key=lambda a: a.id):
        lf = l.frontmatter
        ic = lf.get("iteration_count", 0)
        budget = lf.get("budget", "?")
        print(f"  {CYAN}{l.id}{NC}  mode={lf.get('mode', '?')}  "
              f"iter={ic}/{budget}  "
              f"kept={lf.get('kept_count', 0)}  "
              f"disc={lf.get('discarded_count', 0)}  "
              f"best={lf.get('best_metric', '—')}  "
              f"[{l.status}]")
    print()

    findings = _find_findings_for_comp(root, comp.id)
    print(f"{BOLD}Findings ({len(findings)}):{NC}")
    if not findings:
        print(f"  {DIM}(none){NC}")
    for f in sorted(findings, key=lambda a: a.id):
        conf = f.frontmatter.get("confidence", "?")
        summary = f.frontmatter.get("summary", "")
        summary_short = summary[:80] + "..." if len(summary) > 80 else summary
        print(f"  {CYAN}{f.id}{NC}  [{f.status}]  conf={conf}")
        print(f"    {DIM}{summary_short}{NC}")
    print()

    all_expts = _get_all_expts_for_comp(root, comp.id)
    kept = [e for e in all_expts if e.status == "kept"]
    direction = fm.get("metric_direction", "higher_is_better")
    reverse = direction == "higher_is_better"
    kept.sort(key=lambda e: float(e.frontmatter.get("metric_value", 0)), reverse=reverse)

    top_n = args.get("top", 5)
    print(f"{BOLD}Top {top_n} Kept Experiments:{NC}")
    if not kept:
        print(f"  {DIM}(none){NC}")
    for i, e in enumerate(kept[:top_n]):
        ef = e.frontmatter
        mv = ef.get("metric_value", "?")
        cat = ef.get("change_category", "?")
        summary = e.title
        loop_ref = ef.get("loop", "?")
        aux = ef.get("auxiliary_metrics")
        line = f"  #{i+1}  {CYAN}{e.id}{NC}  {mv}  {cat}  \"{summary}\"  ({loop_ref})"
        print(line)
        if aux and isinstance(aux, dict):
            parts = [f"{k}={v}" for k, v in aux.items()]
            print(f"      {DIM}aux: {', '.join(parts)}{NC}")
    print()

    return 0


def _run_leaderboard(root: Path, args: dict) -> int:
    show_all = args.get("all", False)
    comp_filter = args.get("competition")

    if show_all and comp_filter:
        print(f"{RED}✗ --all and --competition are mutually exclusive.{NC}")
        return 1

    if show_all:
        comps = _find_competitions(root)
        if not comps:
            print(f"{RED}✗ No competitions found.{NC}")
            return 1
    else:
        comp = _resolve_comp(root, args)
        if not comp:
            return 1
        comps = [comp]

    top_n = args.get("top", 10)

    for comp in comps:
        fm = comp.frontmatter
        direction = fm.get("metric_direction", "higher_is_better")
        reverse = direction == "higher_is_better"
        all_expts = _get_all_expts_for_comp(root, comp.id)
        kept = [e for e in all_expts if e.status == "kept"]
        kept.sort(key=lambda e: float(e.frontmatter.get("metric_value", 0)), reverse=reverse)

        print(f"\n{BOLD}=== {comp.id} Leaderboard: {comp.title} ==={NC}")
        print(f"  Metric: {fm.get('metric_name', '?')} ({direction})")
        print()

        if not kept:
            print(f"  {DIM}(no kept experiments yet){NC}")
            print()
            continue

        for i, e in enumerate(kept[:top_n]):
            ef = e.frontmatter
            mv = ef.get("metric_value", "?")
            cat = ef.get("change_category", "?")
            summary = e.title
            loop_ref = ef.get("loop", "?")
            aux = ef.get("auxiliary_metrics")

            print(f"  {BOLD}#{i+1:>2}{NC}  {CYAN}{e.id}{NC}  {mv}  {cat}  "
                  f"\"{summary}\"  ({loop_ref})")
            if aux and isinstance(aux, dict):
                parts = [f"{k}={v}" for k, v in aux.items()]
                print(f"        {DIM}aux: {', '.join(parts)}{NC}")

        print()

    return 0


def run(root: Path, args: dict) -> int:
    root = root.resolve()
    sub = args.get("autoresearch_subcommand")

    if sub == "plan":
        return _run_plan(root, args)
    if sub == "run":
        return _run_run(root, args)
    if sub == "review":
        return _run_review(root, args)
    if sub == "leaderboard":
        return _run_leaderboard(root, args)

    print(f"{RED}✗ Unknown autoresearch subcommand. "
          f"Use: plan, run, review, leaderboard{NC}")
    return 1
