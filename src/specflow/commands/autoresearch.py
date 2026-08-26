"""specflow autoresearch -- Harness-agnostic research loop CLI.

Provides plan, run, review, and leaderboard subcommands for the autoresearch
pack.  The host LLM drives the iteration loop; this command handles state
mutations (artifact creation, LOOP updates, leaderboard rendering) and prints
protocol checklists that any harness can follow.
"""

from __future__ import annotations

import json
import sys
from datetime import date
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


def _resolve_loop(
    root: Path,
    comp: art_lib.Artifact,
    args: dict,
) -> art_lib.Artifact | None:
    """Resolve an explicit LOOP or the single active/draft LOOP for a COMP."""
    loops = _find_loops_for_comp(root, comp.id)
    loop_id = args.get("loop")
    if loop_id:
        target = next((loop for loop in loops if loop.id == loop_id), None)
        if not target:
            print(f"{RED}✗ LOOP '{loop_id}' not found under {comp.id}.{NC}")
        return target

    running = [loop for loop in loops if loop.status == "running"]
    draft = [loop for loop in loops if loop.status == "draft"]
    if len(running) == 1:
        return running[0]
    if not running and len(draft) == 1:
        return draft[0]
    if len(running) > 1:
        return running[0]  # The assessor reports the structural conflict.
    if len(draft) > 1:
        print(f"{YELLOW}Multiple draft LOOPs found. Specify --loop <ID>.{NC}")
        return None
    print(f"{RED}✗ No running or draft LOOP found for {comp.id}. Create one first.{NC}")
    return None


def _consecutive_tail(expts: list[art_lib.Artifact], key: str) -> tuple[object, int]:
    """Return the final value and its consecutive run length by iteration/order."""
    if not expts:
        return None, 0
    ordered = sorted(
        expts,
        key=lambda e: (e.frontmatter.get("iteration", 0), e.frontmatter.get("created", ""), e.id),
    )
    value = ordered[-1].frontmatter.get(key) if key != "status" else ordered[-1].status
    count = 0
    for expt in reversed(ordered):
        current = expt.frontmatter.get(key) if key != "status" else expt.status
        if current != value:
            break
        count += 1
    return value, count


def _assess_loop(
    root: Path,
    comp: art_lib.Artifact,
    loop: art_lib.Artifact,
) -> list[dict[str, str]]:
    """Derive deterministic accounting signals without making research choices."""
    signals: list[dict[str, str]] = []

    def add(state: str, name: str, message: str, pointer: str = "") -> None:
        signals.append({"state": state, "name": name, "message": message, "pointer": pointer})

    loops = _find_loops_for_comp(root, comp.id)
    running = [candidate for candidate in loops if candidate.status == "running"]
    if len(running) > 1:
        ids = ", ".join(candidate.id for candidate in running)
        add("structural", "concurrency", f"Multiple running LOOPs: {ids}",
            "Abort all but one running LOOP before continuing.")
    else:
        add("ok", "concurrency", "At most one LOOP is running for this competition")

    fm = loop.frontmatter
    budget = fm.get("budget")
    iteration_count = fm.get("iteration_count", 0)
    if isinstance(budget, int) and iteration_count >= budget:
        add("structural", "budget", f"Budget exhausted ({iteration_count}/{budget})",
            "Complete or plateau this LOOP; create a new LOOP to continue.")
    else:
        add("ok", "budget", f"Iteration budget {iteration_count}/{budget if budget is not None else '?'}")

    quick = isinstance(budget, int) and budget <= 5
    if fm.get("eda_completed"):
        add("ok", "eda", "EDA is recorded")
    else:
        add("advisory", "eda", "No completed EDA is recorded",
            f"specflow update {loop.id} --set eda_completed=true --set eda_summary=\"...\"")

    agenda = fm.get("research_agenda") or []
    agenda_min = 2 if quick else 5
    if isinstance(agenda, list) and len(agenda) >= agenda_min:
        add("ok", "agenda", f"Research agenda has {len(agenda)} directions")
    else:
        add("advisory", "agenda", f"Research agenda has fewer than {agenda_min} directions",
            f"specflow update {loop.id} --set research_agenda='[...]'")

    if fm.get("knowledge_input"):
        add("ok", "knowledge", "Prior findings are loaded")
    elif _find_findings_for_comp(root, comp.id):
        add("advisory", "knowledge", "Competition has FINDs but LOOP knowledge_input is empty",
            f"specflow update {loop.id} --set knowledge_input='[\"FIND-NNN\"]'")
    else:
        add("ok", "knowledge", "No prior findings are available")

    expts = _find_expts_for_loop(root, loop.id)
    category, category_count = _consecutive_tail(expts, "change_category")
    threshold = 2 if fm.get("mode", "explore") == "explore" else 3
    if category and category_count >= threshold:
        add("advisory", "diversity", f"{category_count} consecutive '{category}' experiments",
            "Review an orthogonal research-agenda direction before another similar iteration.")
    else:
        add("ok", "diversity", "No repeated-category streak detected")

    failure_count = 0
    for expt in reversed(sorted(expts, key=lambda e: (e.frontmatter.get("iteration", 0), e.id))):
        if expt.status not in ("discarded", "crashed"):
            break
        failure_count += 1
    if failure_count >= 5:
        add("advisory", "stuck", f"{failure_count} consecutive discarded/crashed experiments",
            "Switch category or revisit the highest-impact assumption.")
    else:
        add("ok", "stuck", "No 5-experiment failure streak detected")

    if expts and iteration_count and iteration_count % 10 == 0 and not fm.get("condensation_briefs"):
        add("advisory", "condensation", "No condensation brief recorded at this checkpoint",
            f"specflow update {loop.id} --set condensation_briefs='[...]'")
    return signals


def _render_signals(signals: list[dict[str, str]]) -> None:
    icons = {"ok": f"{GREEN}✓{NC}", "advisory": f"{YELLOW}⚠{NC}", "structural": f"{RED}✗{NC}"}
    print(f"{BOLD}Deterministic accounting:{NC}")
    for signal in signals:
        print(f"  {icons[signal['state']]} {signal['name']}: {signal['message']}")
        if signal["pointer"]:
            print(f"      {DIM}→ {signal['pointer']}{NC}")
    print()


def _has_structural(signals: list[dict[str, str]]) -> bool:
    return any(signal["state"] == "structural" for signal in signals)


def _run_status(root: Path, args: dict) -> int:
    comp = _resolve_comp(root, args)
    if not comp:
        return 1
    loop = _resolve_loop(root, comp, args)
    if not loop:
        return 1
    print(f"\n{BOLD}=== Autoresearch Status ==={NC}\n")
    print(f"Competition: {CYAN}{comp.id}{NC}  {comp.title}")
    print(f"LOOP:        {CYAN}{loop.id}{NC}  [{loop.status}]\n")
    signals = _assess_loop(root, comp, loop)
    _render_signals(signals)
    return 2 if _has_structural(signals) else 0


def _running_loops_for_comp(
    root: Path, comp_id: str, exclude: str | None = None
) -> list[art_lib.Artifact]:
    """Return LOOPs in `running` status for a COMP (optionally excluding one ID).

    Accounting helper: it only reports state, never mutates. The concurrent-LOOP
    gate (STORY-SMALLFIX-621b AC1) consults this to refuse starting a second
    active LOOP on the same COMP.
    """
    loops = _find_loops_for_comp(root, comp_id)
    return [l for l in loops if l.status == "running" and l.id != exclude]


def _print_concurrent_blocker(
    running_loops: list[art_lib.Artifact], comp_id: str
) -> int:
    """Render the concurrent-LOOP gate refusal. Returns exit code 2."""
    ids = ", ".join(l.id for l in running_loops)
    print(f"{RED}✗ Concurrent-LOOP gate: cannot start a running LOOP on {comp_id}.{NC}")
    print(f"  Already active: {CYAN}{ids}{NC}")
    print(f"  {DIM}Complete, plateau, or abort the active LOOP first, e.g.{NC}")
    print(f"  {DIM}  specflow update {running_loops[0].id} --status completed{NC}")
    return 2


def _parse_knowledge_input(raw: str | None) -> list[str] | None:
    """Accept a JSON list or comma-separated FIND IDs → list[str]."""
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    except (json.JSONDecodeError, ValueError):
        pass
    return [item.strip() for item in raw.split(",") if item.strip()]


def _render_loop_summary(root: Path, comp: art_lib.Artifact, loop_id: str) -> None:
    artifacts = art_lib.discover_artifacts(root)
    id_index = art_lib.build_id_index(artifacts)
    loop = id_index.get(loop_id)
    if not loop:
        return
    lf = loop.frontmatter
    fm = comp.frontmatter
    print(f"  {CYAN}{loop.id}{NC}  [{loop.status}]")
    print(f"    competition: {comp.id}  metric: {fm.get('metric_name', '?')} "
          f"({fm.get('metric_direction', '?')})")
    print(f"    mode={lf.get('mode', '?')}  budget={lf.get('budget', '?')}  "
          f"iterations={lf.get('iteration_count', 0)}")
    ki = lf.get("knowledge_input")
    if ki:
        print(f"    knowledge_input: {ki}")
    print()


def _run_plan(root: Path, args: dict) -> int:
    """plan = create/update a LOOP (AC1) when mode/budget given, else checklist."""
    comp = _resolve_comp(root, args)
    if not comp:
        return 1

    mode = args.get("mode")
    budget = args.get("budget")
    has_create_intent = (
        mode is not None
        or budget is not None
        or args.get("knowledge_input") is not None
        or bool(args.get("create", False))
    )

    if not has_create_intent:
        return _run_plan_info(root, comp, args)

    # ── Create / update path (STORY-ADDCLI-0e15 AC1) ──
    target_status = args.get("status") or "draft"
    if target_status not in ("draft", "running"):
        print(f"{RED}✗ --status must be 'draft' or 'running' (got '{target_status}').{NC}")
        return 1

    loops = _find_loops_for_comp(root, comp.id)
    existing: art_lib.Artifact | None = None
    explicit = args.get("loop")
    if explicit:
        existing = next((l for l in loops if l.id == explicit), None)
        if not existing:
            print(f"{RED}✗ LOOP '{explicit}' not found under {comp.id}.{NC}")
            return 1
    else:
        draft_loops = [l for l in loops if l.status == "draft"]
        if len(draft_loops) == 1:
            existing = draft_loops[0]

    # Concurrent-LOOP gate (STORY-SMALLFIX-621b AC1): refuse to bring up a
    # second running LOOP on the same COMP. Accounting-friendly: reports state,
    # never corrupts. Drafting a LOOP while another runs is allowed (planning
    # the next loop); only *starting* a second active loop is blocked.
    will_run = target_status == "running" or bool(args.get("start", False))
    exclude = existing.id if existing else None
    if will_run:
        blockers = _running_loops_for_comp(root, comp.id, exclude=exclude)
        if blockers:
            return _print_concurrent_blocker(blockers, comp.id)

    if not existing and (mode is None or budget is None):
        print(f"{RED}✗ Creating a LOOP requires --mode and --budget.{NC}")
        print(f"  {DIM}e.g. specflow autoresearch plan --competition {comp.id} "
              f"--mode explore --budget 50{NC}")
        return 1

    knowledge_input = _parse_knowledge_input(args.get("knowledge_input"))
    fields: dict = {}
    if mode is not None:
        fields["mode"] = mode
    if budget is not None:
        fields["budget"] = int(budget)
    if knowledge_input is not None:
        fields["knowledge_input"] = knowledge_input

    if existing:
        updates = dict(fields)
        if will_run and existing.status == "draft":
            updates["status"] = "running"
            updates["started_at"] = date.today().isoformat()
        # STORY-636: repair/upkeep — ensure the operates_on link edge exists
        # even on LOOPs created by older versions that only wrote the
        # frontmatter field. Merge, never replace.
        existing_links = [
            {"target": l.target, "role": l.role} for l in existing.links
        ]
        if not any(
            l["target"] == comp.id and l["role"] == "operates_on"
            for l in existing_links
        ):
            existing_links.append({"target": comp.id, "role": "operates_on"})
            updates["links"] = existing_links
        result = art_lib.update_artifact(root, existing.id, **updates)
        if not result.get("ok"):
            print(f"{RED}✗ Failed to update {existing.id}: {result.get('error')}{NC}")
            return 1
        verb = "Started" if ("status" in updates) else "Updated"
        print(f"\n{GREEN}✓ {verb} {existing.id}{NC}\n")
        _render_loop_summary(root, comp, existing.id)
        return 0

    title = args.get("title") or f"{mode or 'Explore'} loop on {comp.id}"
    create_status = "running" if will_run else "draft"
    create_kwargs: dict = {
        "competition": comp.id,
        # Trace edge: LOOP operates_on COMP. The frontmatter `competition`
        # field alone is invisible to `specflow trace` — the link edge is
        # what makes the research hierarchy traversable (STORY-636).
        "links": [{"target": comp.id, "role": "operates_on"}],
        **fields,
    }
    if will_run:
        create_kwargs["started_at"] = date.today().isoformat()
    result = art_lib.create_artifact(
        root,
        artifact_type="loop",
        title=title,
        status=create_status,
        body=f"# {title}\n\nAutoresearch loop on {comp.id}.\n",
        **create_kwargs,
    )
    if not result.get("ok"):
        print(f"{RED}✗ Failed to create LOOP: {result.get('error')}{NC}")
        return 1
    loop_id = result["id"]
    verb = "Started" if will_run else "Planned"
    print(f"\n{GREEN}✓ {verb} {loop_id}{NC}\n")
    _render_loop_summary(root, comp, loop_id)
    return 0


def _run_plan_info(root: Path, comp: art_lib.Artifact, args: dict) -> int:
    """Informational setup checklist (no artifact mutation)."""
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
        print(f"  specflow autoresearch plan --competition {comp.id} "
              f"--mode explore --budget 50")
        print()

    return 0


def _run_run(root: Path, args: dict) -> int:
    comp = _resolve_comp(root, args)
    if not comp:
        return 1

    target_loop = _resolve_loop(root, comp, args)
    if not target_loop:
        return 1

    allow_start = not bool(args.get("no_start", False))

    # Concurrent-LOOP gate (STORY-SMALLFIX-621b AC1): refuse to start a second
    # LOOP on the same COMP while one is active. `run` starts a draft LOOP
    # (draft→running) unless --no-start is passed; if another LOOP is already
    # running, that start is blocked here. Accounting-friendly: reports state,
    # never corrupts the existing active LOOP.
    if target_loop.status == "draft" and allow_start:
        blockers = _running_loops_for_comp(root, comp.id, exclude=target_loop.id)
        if blockers:
            _render_signals(_assess_loop(root, comp, target_loop))
            return _print_concurrent_blocker(blockers, comp.id)

    signals = _assess_loop(root, comp, target_loop)
    _render_signals(signals)
    if _has_structural(signals):
        print(f"{RED}✗ Resolve structural LOOP state before continuing.{NC}\n")
        return 2

    # Start the draft LOOP (draft→running) unless the user opted out.
    if target_loop.status == "draft" and allow_start:
        started = art_lib.update_artifact(
            root, target_loop.id,
            status="running", started_at=date.today().isoformat(),
        )
        if started.get("ok"):
            print(f"{GREEN}✓ Started {target_loop.id} (draft → running){NC}\n")
            refreshed = art_lib.resolve_link_target(root, target_loop.id)
            if refreshed:
                target_loop = art_lib.parse_artifact(refreshed)
        else:
            print(f"{YELLOW}⚠ Could not start {target_loop.id}: "
                  f"{started.get('error')}{NC}")

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
        # STORY-636: trace edge — EXPT belongs_to LOOP (frontmatter `loop`
        # alone is invisible to `specflow trace`).
        "links": [{"target": loop_id, "role": "belongs_to"}],
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

    coverage = dict(lf.get("category_coverage") or {})
    if change_category:
        coverage[change_category] = int(coverage.get(change_category, 0)) + 1
    updates: dict = {
        "iteration_count": ic,
        "kept_count": kept,
        "discarded_count": discarded,
        "category_coverage": coverage,
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
            # STORY-636: trace edges — FIND belongs_to COMP and condenses
            # LOOP (frontmatter fields alone are invisible to `specflow trace`).
            links=[
                {"target": comp_id, "role": "belongs_to"},
                {"target": loop_id, "role": "condenses"},
            ],
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
    if sub == "status":
        return _run_status(root, args)
    if sub == "review":
        return _run_review(root, args)
    if sub == "leaderboard":
        return _run_leaderboard(root, args)
    if sub == "log":
        return _run_log(root, args)
    if sub == "suggest-finds":
        return _run_suggest_finds(root, args)

    print(f"{RED}✗ Unknown autoresearch subcommand. "
          f"Use: plan, run, status, review, leaderboard, log, suggest-finds{NC}")
    return 1
