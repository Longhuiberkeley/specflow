"""specflow autoresearch -- Harness-agnostic research loop CLI.

Provides plan, run, review, and leaderboard subcommands for the autoresearch
pack.  The host LLM drives the iteration loop; this command handles state
mutations (artifact creation, LOOP updates, leaderboard rendering) and prints
protocol checklists that any harness can follow.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from specflow.lib import artifacts as art_lib
from specflow.lib.display import RED, GREEN, CYAN, YELLOW, NC, BOLD, DIM
from specflow.lib.domain_constants import DOMAIN_RECOMMENDED


def _domain_recommended_fields(domain: str) -> list[str]:
    return DOMAIN_RECOMMENDED.get(domain, [])


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
        print(f"  specflow create --type loop --title \"Initial exploration\" --status draft "
              f"--set competition={comp.id} --set mode=explore --set budget=50")
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
    print(f"{YELLOW}This command prints the protocol checklist. The loop is driven by the AI agent.{NC}")
    print(f"{DIM}Run /specflow-autoresearch in your AI assistant to execute the loop.{NC}")
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

    # Warnings section
    warnings: list[str] = []

    for l in loops:
        if l.status in ("completed", "plateaued"):
            loop_expts = _find_expts_for_loop(root, l.id)
            loop_findings = [f for f in findings if f.frontmatter.get("source_loop") == l.id]
            if not loop_findings:
                warnings.append(f"  {YELLOW}⚠{NC} {CYAN}{l.id}{NC} is {l.status} but has zero FINDs")
            for e in loop_expts:
                if e.status == "kept" and not e.frontmatter.get("parameters"):
                    warnings.append(f"  {YELLOW}⚠{NC} {CYAN}{e.id}{NC} (kept) has no `parameters` logged")
                if e.status in ("discarded", "crashed") and not e.frontmatter.get("failure_analysis"):
                    warnings.append(f"  {YELLOW}⚠{NC} {CYAN}{e.id}{NC} ({e.status}) has no `failure_analysis` logged")

    domain = fm.get("domain")
    if domain:
        domain_recs = _domain_recommended_fields(domain)
        for e in kept:
            aux = e.frontmatter.get("auxiliary_metrics") or {}
            missing = [f for f in domain_recs if f not in aux]
            if missing:
                warnings.append(f"  {YELLOW}⚠{NC} {CYAN}{e.id}{NC} missing recommended aux metrics for '{domain}': {', '.join(missing[:3])}")

    if warnings:
        print(f"{BOLD}Warnings:{NC}")
        for w in warnings:
            print(w)
        print()

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
        params = ef.get("parameters")
        mo = ef.get("model_origin")
        line = f"  #{i+1}  {CYAN}{e.id}{NC}  {mv}  {cat}  \"{summary}\"  ({loop_ref})"
        print(line)
        if aux and isinstance(aux, dict):
            parts = [f"{k}={v}" for k, v in aux.items()]
            print(f"      {DIM}aux: {', '.join(parts)}{NC}")
        if params and isinstance(params, dict):
            parts = [f"{k}={v}" for k, v in params.items()]
            print(f"      {DIM}params: {', '.join(parts)}{NC}")
        if mo:
            print(f"      {DIM}model_origin: {mo}{NC}")
    print()

    return 0


# Maps `leaderboard --group-by <choice>` (and --show-family) to the EXPT
# frontmatter field it groups on. EXPT.loop lets a multi-loop competition be
# sliced by loop so per-loop-ordinal EXPT IDs (EXPT-EXPT001 reused every loop)
# are told apart at the leaderboard level. `strategy_family` groups on the
# `strategy_used` field. Module-level constant — it carries no per-competition
# state, so there is no reason to rebuild it inside the loop.
_LEADERBOARD_GROUP_FIELD = {
    "model_origin": "model_origin",
    "change_category": "change_category",
    "loop": "loop",
    "strategy_family": "strategy_used",
}


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

    group_by = args.get("group_by")
    show_family = args.get("show_family", False)

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

        # Grouping: --group-by <field> (or --show-family, which forces model_origin
        # with a change_category fallback). Field mapping lives in the module-level
        # _LEADERBOARD_GROUP_FIELD.
        if show_family or group_by:
            group_field = "model_origin" if show_family else _LEADERBOARD_GROUP_FIELD.get(group_by, group_by)
            groups: dict[str, list[art_lib.Artifact]] = {}
            for e in kept:
                val = e.frontmatter.get(group_field)
                if val is None and group_field == "model_origin":
                    val = e.frontmatter.get("change_category", "unspecified")
                key = str(val) if val is not None else "unspecified"
                groups.setdefault(key, []).append(e)
            for key, g_expts in sorted(groups.items()):
                g_expts.sort(key=lambda e: float(e.frontmatter.get("metric_value", 0)), reverse=reverse)
                print(f"  {BOLD}{key}:{NC}")
                for i, e in enumerate(g_expts[:top_n]):
                    ef = e.frontmatter
                    mv = ef.get("metric_value", "?")
                    summary = e.title
                    aux = ef.get("auxiliary_metrics")
                    dm = ef.get("diversity_metrics")
                    print(f"    {BOLD}#{i+1}{NC}  {CYAN}{e.id}{NC}  {mv}  \"{summary}\"")
                    if aux and isinstance(aux, dict):
                        parts = [f"{k}={v}" for k, v in aux.items()]
                        print(f"          {DIM}aux: {', '.join(parts)}{NC}")
                    if dm and isinstance(dm, dict):
                        parts = [f"{k}={v}" for k, v in dm.items()]
                        print(f"          {DIM}div: {', '.join(parts)}{NC}")
                print()
        else:
            for i, e in enumerate(kept[:top_n]):
                ef = e.frontmatter
                mv = ef.get("metric_value", "?")
                cat = ef.get("change_category", "?")
                summary = e.title
                loop_ref = ef.get("loop", "?")
                aux = ef.get("auxiliary_metrics")
                mo = ef.get("model_origin")

                print(f"  {BOLD}#{i+1:>2}{NC}  {CYAN}{e.id}{NC}  {mv}  {cat}  "
                      f"\"{summary}\"  ({loop_ref})")
                if aux and isinstance(aux, dict):
                    parts = [f"{k}={v}" for k, v in aux.items()]
                    print(f"        {DIM}aux: {', '.join(parts)}{NC}")
                if mo:
                    print(f"        {DIM}origin: {mo}{NC}")

            print()

    return 0


def _run_log(root: Path, args: dict) -> int:
    loop_id = args.get("loop")
    artifacts = art_lib.discover_artifacts(root)
    id_index = art_lib.build_id_index(artifacts)
    loop = id_index.get(loop_id)
    if not loop or art_lib.get_prefix_from_id(loop.id) != "LOOP":
        print(f"{RED}✗ LOOP '{loop_id}' not found.{NC}")
        return 1

    status = args.get("status")
    metric_value = args.get("metric_value")
    change_category = args.get("change_category")
    summary = args.get("summary")
    title = args.get("title") or summary

    extra_fields = {}
    set_fields = args.get("set_fields") or []
    for entry in set_fields:
        if "=" not in entry:
            print(f"{RED}✗ Invalid --set value '{entry}'. Expected KEY=VALUE.{NC}")
            return 1
        key, raw = entry.split("=", 1)
        key = key.strip()
        if not key:
            print(f"{RED}✗ Invalid --set value '{entry}'. Empty key.{NC}")
            return 1
        try:
            extra_fields[key] = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            extra_fields[key] = raw

    comp_id = loop.frontmatter.get("competition")
    create_kwargs = {
        "loop": loop_id,
        "metric_value": metric_value if metric_value is not None else 0.0,
        "change_category": change_category,
        "summary": summary,
        "competition": comp_id,
        **extra_fields,
    }

    result = art_lib.create_artifact(
        root,
        artifact_type="experiment",
        title=title,
        status=status,
        body=f"""# {title}

{summary}
""",
        **create_kwargs,
    )
    if not result.get("ok"):
        print(f"{RED}✗ Failed to create EXPT: {result.get('error')}{NC}")
        return 1

    expt_id = result["id"]
    print(f"{GREEN}✓ Created {expt_id}{NC}")

    if args.get("no_update_loop"):
        return 0

    # Auto-update LOOP counters
    lf = loop.frontmatter
    ic = lf.get("iteration_count", 0) + 1
    kept = lf.get("kept_count", 0)
    discarded = lf.get("discarded_count", 0)
    if status == "kept":
        kept += 1
    elif status in ("discarded", "crashed"):
        discarded += 1

    updates: dict = {
        "iteration_count": ic,
        "kept_count": kept,
        "discarded_count": discarded,
    }

    # Update best metric if applicable
    if status == "kept" and metric_value is not None:
        comp = id_index.get(comp_id) if comp_id else None
        direction = "higher_is_better"
        if comp:
            direction = comp.frontmatter.get("metric_direction", "higher_is_better")
        best_metric = lf.get("best_metric")
        is_better = False
        if best_metric is None:
            is_better = True
        elif direction == "higher_is_better":
            is_better = metric_value > best_metric
        else:
            is_better = metric_value < best_metric
        if is_better:
            updates["best_metric"] = metric_value
            updates["best_experiment"] = expt_id

    up_result = art_lib.update_artifact(root, loop_id, **updates)
    if up_result.get("ok"):
        print(f"{GREEN}  ↳ Updated {loop_id}: iteration {ic}, kept {kept}, discarded {discarded}{NC}")
        if "best_metric" in updates:
            print(f"{GREEN}  ↳ New best metric: {updates['best_metric']} ({expt_id}){NC}")
    else:
        print(f"{YELLOW}  ⚠ LOOP update failed: {up_result.get('error')}{NC}")

    return 0


def _run_suggest_finds(root: Path, args: dict) -> int:
    loop_id = args.get("loop")
    artifacts = art_lib.discover_artifacts(root)
    id_index = art_lib.build_id_index(artifacts)
    loop = id_index.get(loop_id)
    if not loop or art_lib.get_prefix_from_id(loop.id) != "LOOP":
        print(f"{RED}✗ LOOP '{loop_id}' not found.{NC}")
        return 1

    expts = _find_expts_for_loop(root, loop_id)
    if not expts:
        print(f"{YELLOW}⚠ No EXPTs found for {loop_id}.{NC}")
        return 0

    # Group by change_category
    groups: dict[str, list[art_lib.Artifact]] = {}
    for e in expts:
        cat = e.frontmatter.get("change_category", "unspecified")
        groups.setdefault(cat, []).append(e)

    comp_id = loop.frontmatter.get("competition")
    what_worked: list[str] = []
    what_failed: list[str] = []
    next_steps: list[str] = []

    for cat, g_expts in sorted(groups.items()):
        kept = [e for e in g_expts if e.status == "kept"]
        discarded = [e for e in g_expts if e.status == "discarded"]
        crashed = [e for e in g_expts if e.status == "crashed"]
        best = None
        if kept:
            direction = "higher_is_better"
            if comp_id and comp_id in id_index:
                direction = id_index[comp_id].frontmatter.get("metric_direction", "higher_is_better")
            reverse = direction == "higher_is_better"
            best = max(kept, key=lambda e: float(e.frontmatter.get("metric_value", 0)))
            if not reverse:
                best = min(kept, key=lambda e: float(e.frontmatter.get("metric_value", 0)))

        if kept:
            refs = ", ".join(e.id for e in kept[:3])
            line = f"- {cat}: drove improvement ({refs})"
            if best:
                line += f" best={best.frontmatter.get('metric_value', '—')}"
            what_worked.append(line)
            # Next step: exploit if multiple keeps in same category
            if len(kept) >= 2:
                next_steps.append(f"- Exploit: refine {cat} further ({len(kept)} keeps)")
        elif discarded or crashed:
            refs = ", ".join(e.id for e in (discarded + crashed)[:3])
            what_failed.append(f"- {cat}: no successes ({refs})")
            next_steps.append(f"- Explore: avoid {cat} or try radically different approach")

    if not what_worked and not what_failed:
        print(f"{YELLOW}⚠ No actionable patterns in {loop_id} EXPTs.{NC}")
        return 0

    draft_fm = {
        "type": "finding",
        "status": "draft",
        "competition": comp_id,
        "source_loop": loop_id,
        "confidence": "low" if len(expts) < 5 else "medium",
        "summary": f"Synthesized from {len(expts)} experiments in {loop_id}",
        "what_worked": "\n".join(what_worked) if what_worked else None,
        "what_failed": "\n".join(what_failed) if what_failed else None,
        "next_steps": "\n".join(next_steps) if next_steps else None,
    }

    if args.get("write"):
        result = art_lib.create_artifact(
            root,
            artifact_type="finding",
            title=f"Findings from {loop_id}",
            status="draft",
            body="# Auto-suggested findings\n\nReview and refine before confirming.\n",
            competition=comp_id,
            source_loop=loop_id,
            confidence=draft_fm["confidence"],
            summary=draft_fm["summary"],
            what_worked=draft_fm["what_worked"],
            what_failed=draft_fm["what_failed"],
            next_steps=draft_fm["next_steps"],
        )
        if result.get("ok"):
            print(f"{GREEN}✓ Created {result['id']}{NC}")
        else:
            print(f"{RED}✗ Failed to create FIND: {result.get('error')}{NC}")
            return 1
    else:
        print(f"\n{BOLD}=== Suggested FIND for {loop_id} ==={NC}\n")
        print(f"{DIM}# Paste into `specflow create --type finding ...` or re-run with --write{NC}\n")
        print("---")
        for key, value in draft_fm.items():
            if value is None:
                continue
            if isinstance(value, list):
                print(f"{key}:")
                for item in value:
                    print(f"  - {item}")
            else:
                print(f"{key}: {value}")
        print("---")
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
    if sub == "log":
        return _run_log(root, args)
    if sub == "suggest-finds":
        return _run_suggest_finds(root, args)

    print(f"{RED}✗ Unknown autoresearch subcommand. "
          f"Use: plan, run, review, leaderboard, log, suggest-finds{NC}")
    return 1
