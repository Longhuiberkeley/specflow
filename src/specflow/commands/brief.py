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
from specflow.lib import lint as lint_lib
from specflow.lib.waves import compute_waves, filter_executable_stories
from specflow.lib.display import RED, GREEN, YELLOW, CYAN, BOLD, NC

# Category → the prefixes that belong to it, in lifecycle order.
_CATEGORY_ORDER = ["spec", "work", "review", "research", "ops"]


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


def _docs_summary(root: Path) -> dict | None:
    """Recognized docs surface — visibility, not lifecycle.

    Returns None when no docs exist so docless projects see no noise. Counts the
    surface, how many docs cite an artifact, the areas it spans, and the
    most-cited docs. Pure read of the filesystem via lib/docs.discover_docs.
    """
    from specflow.lib import docs as docs_lib

    rroot = Path(root).resolve()
    docs = docs_lib.discover_docs(root)
    if not docs:
        return None
    areas: set[str] = set()
    root_count = 0
    for d in docs:
        try:
            rel = d.path.relative_to(rroot)
        except ValueError:
            continue
        if len(rel.parts) <= 1:
            root_count += 1
        else:
            areas.add(rel.parts[0])
    citing = [d for d in docs if d.cites]
    top = sorted(citing, key=lambda d: len(d.cites), reverse=True)[:3]
    where = ", ".join(sorted(areas) + ([f"+{root_count} at root"] if root_count else []))
    return {
        "count": len(docs),
        "citing_count": len(citing),
        "where": where,
        "top_cited": [(str(d.path.relative_to(rroot)), len(d.cites)) for d in top],
    }


def _knowledge_summary(root: Path, artifacts: list[art_lib.Artifact]) -> dict:
    """Knowledge-surface health: proactive BP best-practices, reactive PREV patterns,
    research FINDs, review CHLs.

    Makes dormancy visible (accounting, not policing): a wired-but-empty surface is the
    silent failure mode of SpecFlow's learnings system. Always returns a summary because
    an entirely empty cupboard is the most important dormant state to expose. Pure read —
    artifacts for BP/FIND/CHL, and lib/learning.list_learned_patterns for PREV. NOTE: PREV files live in
    .specflow/checklists/learned/, NOT under _specflow/, so they are invisible to
    discover_artifacts unless surfaced here — this is the one place they become countable.
    """
    from specflow.lib import learning as learn_lib

    def _by_prefix(prefix: str) -> list[art_lib.Artifact]:
        return [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == prefix]

    bps = _by_prefix("BP")
    finds = _by_prefix("FIND")
    chls = _by_prefix("CHL")
    prevs = learn_lib.list_learned_patterns(root)

    bp_by_status: dict[str, int] = {}
    for b in bps:
        s = b.status or "draft"
        bp_by_status[s] = bp_by_status.get(s, 0) + 1

    # CHL "done" = addressed or accepted; open = open/stale (still actionable).
    chl_done = sum(1 for c in chls if c.status in ("addressed", "accepted"))
    chl_open = len(chls) - chl_done

    hints: list[str] = []
    active_bps = bp_by_status.get("active", 0) + bp_by_status.get("approved", 0)
    if active_bps == 0:
        hints.append(
            "no active/approved BPs — domain best-practices not captured; generate at "
            "/specflow-discover, or add one (`specflow create --type best-practice`) when "
            "you apply a reusable practice."
        )
    if not prevs:
        hints.append(
            "0 PREV — reactive learning never fired; patterns auto-capture from review "
            "findings (blocking/warning, learnable techniques) and `specflow done`."
        )

    return {
        "bp_total": len(bps),
        "bp_by_status": bp_by_status,
        "prev_count": len(prevs),
        "find_count": len(finds),
        "chl_open": chl_open,
        "chl_done": chl_done,
        "hints": hints,
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


def _recent_decisions(artifacts: list[art_lib.Artifact], limit: int = 5) -> list[tuple[str, str, str]]:
    """Most-recently-modified DEC artifacts as (id, title, rationale first line).

    Deterministic read of the artifact graph — DEC bodies live in _specflow/work/decisions/.
    Sorted by file mtime (most recent first). This IS the durable "why"; brief only
    surfaces it, never writes a separate log.
    """
    decs = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "DEC"]

    def _mtime(a: art_lib.Artifact) -> float:
        try:
            return a.path.stat().st_mtime
        except Exception:
            return 0.0

    decs.sort(key=_mtime, reverse=True)
    out: list[tuple[str, str, str]] = []
    for a in decs[:limit]:
        first = ""
        for ln in (a.body or "").splitlines():
            s = ln.strip()
            if s and not s.startswith("#"):
                first = s
                break
        out.append((a.id, a.title or "(untitled)", first[:140]))
    return out


def _pack_state_note(artifacts: list[art_lib.Artifact], active_packs: list[str]) -> str:
    """Optional second line: an actionable state in an active subsystem (pack).

    Only fires when the relevant pack is active, so projects without it see no
    noise. Pure read of the artifact inventory.
    """
    if "autoresearch" in active_packs:
        running_loops = sum(
            1 for a in artifacts
            if art_lib.get_prefix_from_id(a.id) == "LOOP" and a.status == "running"
        )
        if running_loops:
            return (f"{running_loops} LOOP(s) running (autoresearch) → log/review EXPTs "
                    f"or close the loop (`/specflow-autoresearch`).")
    if "ops" in active_packs:
        live_runs = sum(
            1 for a in artifacts
            if art_lib.get_prefix_from_id(a.id) == "RUN" and a.status == "live"
        )
        monitors = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "MON"]
        breached = sum(
            1 for a in monitors
            if a.status == "flagged" or (a.frontmatter or {}).get("health") == "breached"
        )
        if breached:
            return (f"{breached} breached MONITOR(s) (ops) → check drift / retrain "
                    f"(`/specflow-ops`, `specflow trace <RUN>`).")
        if live_runs and not monitors:
            return (f"{live_runs} live RUN(s) unobserved (ops) → record a MONITOR "
                    f"(`/specflow-ops`).")
    return ""


def _outcome_feedback_note(artifacts: list[art_lib.Artifact], active_packs: list[str]) -> str:
    """Optional note: real-world ops outcomes that never fed back into a DEF.

    Closes the traceability gap where a breached MONITOR can be hand-resolved
    leaving zero defect record (and thus zero prevention pattern downstream).
    Two deterministic counts over MONITOR artifacts via a TWO-DIRECTION graph
    walk — both directions must be checked or this crys-wolf:

      Forward (MONITOR's own links): does the MONITOR have an outgoing `informs`
        edge (e.g., → LOOP/DEC) recording a follow-up?
      Backward (any DEF's links): does a DEF point back at the MONITOR via
        `exposed_by` (the defect-from-monitor wire)?

    (i)  flagged/breached MONITORs with NO DEF backlink AND NO outgoing informs
         edge → "breach unaccountable" (routes to `specflow defect-from-monitor`).
    (ii) resolved MONITORs that were never linked to any DEF → "vanished without
         prevention record" (the breach left no closed-DEF → PREV trace).

    Gated on the ops pack being active AND at least one MONITOR existing, so
    non-ops projects and docless states see zero noise. Pure read-only graph
    queries — never blocking, never mutating.
    """
    if "ops" not in active_packs:
        return ""
    monitors = [a for a in artifacts if art_lib.get_prefix_from_id(a.id) == "MON"]
    if not monitors:
        return ""

    # Backward walk: every MONITOR id that some DEF points back at via exposed_by.
    backed_by_def: set[str] = set()
    for a in artifacts:
        if art_lib.get_prefix_from_id(a.id) != "DEF":
            continue
        for lk in a.links:
            if lk.role == "exposed_by":
                backed_by_def.add(lk.target)

    # Forward walk: every MONITOR that declared an outgoing informs follow-up.
    has_informs: set[str] = set()
    for m in monitors:
        for lk in m.links:
            if lk.role == "informs":
                has_informs.add(m.id)

    def _is_breached(m: art_lib.Artifact) -> bool:
        return m.status == "flagged" or (m.frontmatter or {}).get("health") == "breached"

    unaccountable = [
        m for m in monitors
        if _is_breached(m) and m.id not in backed_by_def and m.id not in has_informs
    ]
    vanished = [m for m in monitors if m.status == "resolved" and m.id not in backed_by_def]

    notes: list[str] = []
    if unaccountable:
        first = unaccountable[0].id
        more = f" (+{len(unaccountable) - 1} more)" if len(unaccountable) > 1 else ""
        notes.append(
            f"{len(unaccountable)} breached MONITOR(s) with no DEF (outcome unaccountable) "
            f"→ specflow defect-from-monitor {first} --req REQ-NNN{more}"
        )
    if vanished:
        notes.append(
            f"{len(vanished)} resolved MONITOR(s) never linked to a DEF "
            f"(vanished without prevention record)"
        )
    return "\n".join(notes)


def _next_skill_recommendation(
    phase: str,
    artifacts: list[art_lib.Artifact],
    suspects: list[art_lib.Artifact],
    next_wave: list[str],
    active_packs: list[str] | None = None,
) -> str:
    """Deterministic next-skill recommendation from phase + inventory.

    Pure read of state — no heuristics, no LLM. Returns one human-actionable line,
    plus an optional second line when an active subsystem (pack) has an
    actionable state (a running LOOP, a breached/stale MONITOR).
    """
    active_packs = active_packs or []

    def _count(prefix: str, status: str | None = None) -> int:
        n = 0
        for a in artifacts:
            if art_lib.get_prefix_from_id(a.id) == prefix and (status is None or a.status == status):
                n += 1
        return n

    if suspects:
        return (f"{len(suspects)} suspect(s) open — resolve first: "
                f"`specflow change-impact` to review, "
                f"`specflow defect-from-suspect <ID> --req <REQ>` to file.")

    reqs = _count("REQ")
    reqs_draft = _count("REQ", "draft")
    archs = _count("ARCH")
    stories = _count("STORY")

    if phase in ("idle", "discovering"):
        if reqs == 0:
            core = "No REQs yet → /specflow-discover (capture requirements)."
        elif reqs_draft:
            core = (f"{reqs_draft} REQ(s) in draft → confirm with the user, then approve "
                    f"(`specflow approve --type REQ`), then /specflow-plan.")
        else:
            core = "REQs approved, no ARCH yet → /specflow-plan (decompose into architecture & stories)."
    elif phase == "specifying":
        core = (f"{reqs_draft} REQ(s) still draft → approve before planning."
                if reqs_draft else "REQs approved → /specflow-plan.")
    elif phase == "planning":
        if not archs:
            core = "No ARCH yet → continue /specflow-plan (architecture decomposition)."
        elif _count("STORY", "draft") or not stories:
            core = "Stories not approved yet → finish /specflow-plan and approve STORYs."
        else:
            core = "ARCH + STORY approved → /specflow-execute (run the waves)."
    elif phase == "executing":
        if next_wave:
            core = f"Next wave ready ({len(next_wave)} stories) → /specflow-execute (or `specflow go`)."
        elif stories and _count("STORY", "implemented") >= stories:
            # Lifecycle is execute → artifact-review → ship. The router used to jump
            # straight to ship here, silently dropping the artifact-review step that
            # /specflow-execute's own exit message and AGENTS.md both document. If the
            # stories are already verified or V-model tests (UT/IT/QT) exist, review has
            # happened — otherwise insert /specflow-artifact-review before ship.
            reviewed = _count("STORY", "verified") or (_count("UT") + _count("IT") + _count("QT"))
            if reviewed:
                core = "All stories implemented & reviewed → /specflow-ship (release)."
            else:
                core = ("All stories implemented → /specflow-artifact-review "
                        "(review + V-model tests UT/IT/QT), then /specflow-ship.")
        else:
            core = "Continue /specflow-execute."
    elif phase in ("verifying", "complete"):
        core = "Ready to release → /specflow-ship (or /specflow-audit for a health check first)."
    else:
        core = f"Phase '{phase}' — run `specflow brief` for the full digest."

    notes: list[str] = []
    pack_note = _pack_state_note(artifacts, active_packs)
    if pack_note:
        notes.append(pack_note)
    outcome_note = _outcome_feedback_note(artifacts, active_packs)
    if outcome_note:
        notes.append(outcome_note)

    # Backlog-aware advisory: a strategic rewind to specifying/planning can leave
    # implemented/verified stories in the backlog. The phase-based primary line
    # still points at plan/discover; this note reminds the user the backlog still
    # has work, so the router doesn't look like it forgot. Fires on backlog
    # presence (>=3 done stories), NOT on next_wave — next_wave only holds
    # *approved* stories, so the motivating case (a rewound project with a deep
    # implemented backlog and nothing newly queued) would never fire otherwise.
    if phase in ("specifying", "planning"):
        implemented = _count("STORY", "implemented")
        verified = _count("STORY", "verified")
        done = implemented + verified
        if done >= 3:
            noun = "story" if done == 1 else "stories"
            if verified and not implemented:
                # Backlog is all verified — it wants review/ship, not more execute.
                action = "/specflow-artifact-review (then /specflow-ship) for the backlog"
            else:
                action = "/specflow-execute for the backlog"
            notes.append(
                f"Note: {done} {noun} remain implemented after rewind — "
                f"{action}, or /specflow-plan for the pivot scope."
            )

    # Verification-contract advisory: an implemented/verified test (UT/IT/QT) or
    # STORY that DECLARES a verify_command but carries no recorded run evidence
    # (or a recorded run whose exit code diverged from the declared expected
    # code) wants `specflow verify`. This is the deterministic frontmatter query
    # behind the /specflow-start router's verify nudge — accounting, not
    # policing: one advisory line, never blocking, never changes the exit code.
    # It fires only when a verify_command is actually declared, so projects that
    # don't use verification contracts see zero noise.
    verify_types = {"UT", "IT", "QT", "STORY"}
    needs_verify: list[str] = []
    for a in artifacts:
        if art_lib.get_prefix_from_id(a.id) not in verify_types:
            continue
        if a.status not in ("implemented", "verified"):
            continue
        fm = getattr(a, "frontmatter", None) or {}
        if not fm.get("verify_command"):
            continue
        ran_at = fm.get("verify_run_at")
        expected = fm.get("verify_exit_code")
        recorded = fm.get("verify_run_exit_code")
        # Needs (re-)verification when never run, or when a recorded run diverged
        # from the declared expected exit code (str compare tolerates 0/"0").
        diverged = (
            expected is not None
            and recorded is not None
            and str(expected) != str(recorded)
        )
        if not ran_at or diverged:
            needs_verify.append(a.id)
    if needs_verify:
        shown = ", ".join(needs_verify[:5])
        more = f" (+{len(needs_verify) - 5} more)" if len(needs_verify) > 5 else ""
        notes.append(
            f"{len(needs_verify)} artifact(s) declare a verify_command with no "
            f"matching verify_run evidence ({shown}{more}) → "
            f"`specflow verify <ID>` (or `specflow verify --all`)."
        )

    return core + "".join(f"\n{n}" for n in notes)


def _health_nags(
    root: Path,
    config: dict,
    artifacts: list[art_lib.Artifact],
    adoption: dict | None,
) -> list[str]:
    """One-time-setup and subsystem-decay nags for the session-entry digest.

    Returns an empty list for a healthy project (zero noise). Pointer-style —
    accounting, not policing: each line names the problem and the command that
    fixes it. Surfaces things that otherwise fail silently: an unset domain
    disabling domain-aware checklists/review, stale fingerprints undermining the
    impact-log/suspect baseline, and an adoption handshake that never cut a
    baseline.
    """
    nags: list[str] = []

    # domain unset silently disables domain-aware checklists + review synthesis.
    if not config.get("project", {}).get("domain"):
        nags.append(
            "domain not set — domain-aware checklists/review disabled "
            "→ `specflow domain suggest`"
        )

    # Stale stored fingerprints make future suspect classification unreliable;
    # reuse the same check artifact-lint runs, do not recompute ad hoc.
    stale = sum(
        1 for a in artifacts
        if a.fingerprint and not lint_lib.validate_fingerprint(a)["match"]
    )
    if stale:
        nags.append(
            f"{stale} fingerprint(s) stale — recompute with "
            f"`specflow fingerprint-refresh <FILE>` or `specflow rebuild-index`"
        )

    # Adoption started (backfilled artifacts exist) but no baseline was ever cut.
    if adoption is not None and adoption.get("backfilled_count", 0) > 0:
        baselines_dir = root / ".specflow" / "baselines"
        has_baseline = baselines_dir.exists() and any(baselines_dir.iterdir())
        if not has_baseline:
            nags.append(
                "adoption handshake incomplete: no baseline cut → "
                "`specflow baseline create` / `specflow adopt status`"
            )

    return nags


def run(root: Path, args: dict[str, Any]) -> int:
    root = root.resolve()
    since = args.get("since") or "7 days ago"

    config = config_lib.read_config(root)
    state = config_lib.read_state(root)
    if not config or not state:
        print(f"{RED}✗ SpecFlow is not initialized here. Run 'specflow init'.{NC}")
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

    # In-scope wave (next executable wave), best-effort. Reuse the parsed inventory.
    story_artifacts = [
        artifact
        for artifact in artifacts
        if art_lib.get_prefix_from_id(artifact.id) == "STORY"
    ]
    stories = filter_executable_stories(story_artifacts)
    next_wave: list[str] = []
    if stories:
        wave_result = compute_waves(stories)
        if wave_result.get("ok") and wave_result.get("waves"):
            next_wave = wave_result["waves"][0]

    recent = _recent_changes(root, since)
    adoption = _adoption_summary(root, artifacts)

    # --next: emit only the deterministic next-skill recommendation and stop.
    if args.get("next"):
        active_packs = config.get("active_packs", []) or []
        print(_next_skill_recommendation(phase, artifacts, suspects, next_wave, active_packs))
        return 0

    docs_sum = _docs_summary(root)
    knowledge = _knowledge_summary(root, artifacts)

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

    health = _health_nags(root, config, artifacts, adoption)
    if health:
        print(f"\n  {YELLOW}⚠ Health{NC}")
        for n in health:
            print(f"    {n}")

    if docs_sum is not None:
        print(f"\n  {BOLD}Docs surface{NC}")
        print(f"    {docs_sum['count']} docs ({docs_sum['where']})   "
              f"{docs_sum['citing_count']} cite an artifact")
        if docs_sum["top_cited"]:
            tc = ", ".join(f"{p} ({n})" for p, n in docs_sum["top_cited"])
            print(f"    Top cited: {tc}")
        print(f"    {CYAN}specflow detect stale-docs{NC} to flag docs citing superseded artifacts")

    bp_parts = [f"{n} {s}" for s, n in sorted(knowledge["bp_by_status"].items())] or ["none"]
    print(f"\n  {BOLD}Knowledge surfaces{NC}")
    print(f"    BP {knowledge['bp_total']} ({', '.join(bp_parts)})   "
          f"PREV {knowledge['prev_count']}   "
          f"FIND {knowledge['find_count']}   "
          f"CHL {knowledge['chl_open']} open / {knowledge['chl_done']} done")
    for h in knowledge["hints"]:
        print(f"    {YELLOW}⚠ {h}{NC}")

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

    decs = _recent_decisions(artifacts)
    print(f"\n  {BOLD}Recent decisions{NC} (DEC — the durable 'why')")
    if decs:
        for did, title, rationale in decs:
            print(f"    {did} — {title}")
            if rationale:
                print(f"        {rationale}")
    else:
        print(f"    (none)")

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
