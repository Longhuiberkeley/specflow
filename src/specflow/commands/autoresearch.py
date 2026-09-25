"""specflow autoresearch -- Harness-agnostic research loop CLI.

Provides plan, run, review, and leaderboard subcommands for the autoresearch
pack.  The host LLM drives the iteration loop; this command handles state
mutations (artifact creation, LOOP updates, leaderboard rendering) and prints
protocol checklists that any harness can follow.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from datetime import date
from pathlib import Path

from specflow.lib import artifacts as art_lib
from specflow.lib.display import RED, GREEN, CYAN, YELLOW, NC, BOLD, DIM
from specflow.lib.domain_constants import DOMAIN_RECOMMENDED

# STORY-663: deterministic `autoresearch status` exit codes. The skill prompt
# rule is "if status fails, stop" — these codes are what "fails" means:
#   0 = clear · 3 = warn (proceed with caution) · 1/2 = fail (stop)
_STATUS_EXIT_FAIL = 2
_STATUS_EXIT_WARN = 3


def _git(root: Path, *argv: str) -> tuple[int, str]:
    """Run git in the project root; returns (returncode, combined output)."""
    try:
        proc = subprocess.run(
            ["git", *argv], cwd=str(root), capture_output=True, text=True,
            timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 1, "git unavailable"
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def _phase0_git_signals(root: Path) -> list[dict[str, str]]:
    """Phase 0 precondition checks (autonomous-loop-protocol.md), as signals.

    rev-parse failure is a FAIL (the loop commits every iteration — no git
    repo, no loop). Dirty tree / stale index.lock / detached HEAD are WARNs,
    matching the protocol's "log the warning, proceed with caution".
    """
    signals: list[dict[str, str]] = []

    def add(state: str, name: str, message: str, pointer: str = "") -> None:
        signals.append({"state": state, "name": name, "message": message, "pointer": pointer})

    rc, out = _git(root, "rev-parse", "--git-dir")
    if rc != 0:
        add("structural", "git-repo", "Not a git repository (git rev-parse failed)",
            "The loop commits every iteration — initialize git before research.")
        return signals
    add("ok", "git-repo", "Git repository present")

    rc, out = _git(root, "status", "--porcelain", "--untracked-files=no")
    if rc == 0 and out:
        changed = out.splitlines()
        add("warn", "dirty-tree",
            f"{len(changed)} uncommitted change(s) to tracked files "
            f"(e.g. {changed[0].strip()})",
            "Commit or stash before the loop's Phase 4 commits.")
    else:
        add("ok", "dirty-tree", "No uncommitted changes to tracked files")

    rc, git_dir_raw = _git(root, "rev-parse", "--absolute-git-dir")
    git_dir = Path(git_dir_raw) if rc == 0 and git_dir_raw else root / ".git"
    if (git_dir / "index.lock").exists():
        add("warn", "index-lock",
            f"{git_dir / 'index.lock'} exists — a git operation may be stuck",
            "Remove it only after confirming no git process is running.")
    else:
        add("ok", "index-lock", "No stale index lock")

    rc, out = _git(root, "symbolic-ref", "HEAD")
    if rc != 0:
        add("warn", "detached-head", "HEAD is detached",
            "Checkout a branch before iterating (commits must be reachable).")
    else:
        add("ok", "detached-head", f"On branch {out}")

    return signals


def _status_exit_code(signals: list[dict[str, str]]) -> int:
    """Fail dominates warn dominates clear."""
    states = {signal["state"] for signal in signals}
    if "structural" in states:
        return _STATUS_EXIT_FAIL
    if "warn" in states:
        return _STATUS_EXIT_WARN
    return 0


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


def _ordered_expts(expts: list[art_lib.Artifact]) -> list[art_lib.Artifact]:
    """EXPTs in loop order: iteration, then created, then id."""
    return sorted(
        expts,
        key=lambda e: (e.frontmatter.get("iteration", 0), e.frontmatter.get("created", ""), e.id),
    )


def _tail_run(
    expts: list[art_lib.Artifact], key: str
) -> tuple[object, list[art_lib.Artifact]]:
    """Return (final value, tail artifacts sharing it) in loop order."""
    if not expts:
        return None, []
    ordered = _ordered_expts(expts)
    value = ordered[-1].frontmatter.get(key) if key != "status" else ordered[-1].status
    tail: list[art_lib.Artifact] = []
    for expt in reversed(ordered):
        current = expt.frontmatter.get(key) if key != "status" else expt.status
        if current != value:
            break
        tail.append(expt)
    tail.reverse()
    return value, tail


# REQ-043: reassessment is bounded to the most recent attempts. A keep from
# earlier in the tail must never mask a line that has stopped producing
# evidence, so only the last RECENT_WINDOW artifacts can claim progress.
_RECENT_WINDOW = 3
_PROGRESS_FIELDS = ("evidence_ref", "finding", "next_decision")


def _progress_note(expt: art_lib.Artifact) -> dict[str, str] | None:
    """The EXPT's `research_progress` when it has the documented shape.

    Shape (all three non-empty strings): {evidence_ref, finding,
    next_decision}. Anything else — absent, non-mapping, empty, partial — is
    read conservatively as "no structured evidence claim".
    """
    raw = expt.frontmatter.get("research_progress")
    if not isinstance(raw, dict):
        return None
    note: dict[str, str] = {}
    for key in _PROGRESS_FIELDS:
        value = raw.get(key)
        if not isinstance(value, str) or not value.strip():
            return None
        note[key] = value.strip()
    return note


def _normalised(text: str) -> str:
    """Whitespace/case-insensitive comparison key for claims and refs."""
    return " ".join(text.split()).casefold()


def _normalised_ref(ref: str) -> str:
    """Comparison key for refs with the optional scheme stripped.

    ``commit:abc`` and ``abc`` are the same citation, so re-spelling the same
    ref (or flipping its scheme) can never register as new evidence.
    """
    body = ref.strip()
    for scheme in ("commit:", "path:", "artifact:"):
        if body.lower().startswith(scheme):
            body = body[len(scheme):].strip()
            break
    return _normalised(body)


_HEX_CHARS = frozenset("0123456789abcdef")


def _evidence_ref_is_anchored(
    expt: art_lib.Artifact, ref: str, root: Path
) -> bool:
    """True when `ref` points at this EXPT's own record (REQ-043).

    Accepted anchors, each narrowly bounded:
      - the EXPT's ID, exactly or with an explicit ``#fragment`` suffix
        (``EXPT-001#verify-log``) — a longer ID like ``EXPT-0010`` is a
        different experiment and never matches ``EXPT-001``;
      - the `commit` recorded on this EXPT, exactly or as a plausible
        abbreviation of at least 7 hex characters (``commit:`` scheme
        optional); ``commit:`` alone or a 1-char prefix never matches;
      - a repo-relative output path this EXPT logs *outside* its own
        `research_progress` note (a field/body mention plus the file on disk);
        the note cannot certify itself.

    This checks that the citation exists and is anchored to the current
    experiment — never that the evidence proves anything; the agent still
    reads the cited source.
    """
    ref_text = ref.strip()
    if not ref_text:
        return False

    # 1. The EXPT's own ID — exact, or an explicit `#fragment` (boundary).
    if expt.id and (
        ref_text == expt.id or ref_text.startswith(f"{expt.id}#")
    ):
        return True

    # 2. The commit recorded on this EXPT — exact or a >=7-char hex prefix.
    commit = expt.frontmatter.get("commit")
    if isinstance(commit, str) and commit.strip():
        commit_text = commit.strip()
        ref_body = ref_text
        for scheme in ("commit:", "path:", "artifact:"):
            if ref_body.lower().startswith(scheme):
                ref_body = ref_body[len(scheme):].strip()
        if ref_body:
            if ref_body == commit_text:
                return True
            lowered = ref_body.lower()
            if (
                len(ref_body) >= 7
                and all(char in _HEX_CHARS for char in lowered)
                and commit_text.lower().startswith(lowered)
            ):
                return True

    # 3. A repo-relative output path this EXPT logs elsewhere in its record.
    ref_body = ref_text
    for scheme in ("path:", "artifact:"):
        if ref_body.lower().startswith(scheme):
            ref_body = ref_body[len(scheme):].strip()
    if not ref_body or ref_body.startswith("/") or ".." in Path(ref_body).parts:
        return False
    record = {
        key: value for key, value in expt.frontmatter.items()
        if key != "research_progress"
    }
    record_text = json.dumps(record, sort_keys=True, default=str)
    if ref_body not in record_text and ref_body not in (expt.body or ""):
        return False
    return (root / ref_body).is_file()


def _note_repeats(note: dict[str, str], prior_expts: list[art_lib.Artifact]) -> bool:
    """True when this finding or evidence_ref already appeared in history.

    Compared against every earlier EXPT's note, including records outside the
    recent window: re-stating an old claim under a new ref (or vice versa) is
    not new evidence.
    """
    claim = _normalised(note["finding"])
    ref = _normalised_ref(note["evidence_ref"])
    for prior in prior_expts:
        prior_note = _progress_note(prior)
        if not prior_note:
            continue
        if claim == _normalised(prior_note["finding"]):
            return True
        if ref == _normalised_ref(prior_note["evidence_ref"]):
            return True
    return False


def _numeric(value: object) -> float | None:
    """Finite number or None — NaN/±Infinity are not measured numbers."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _keep_shows_improvement(
    expt: art_lib.Artifact, prior_expts: list[art_lib.Artifact], direction: str
) -> bool:
    """A keep counts only with a measured new best (delta is the fallback).

    Repeat keeps of the same value are accounting, not progress. When this
    EXPT carries a finite primary metric, the decision is the actual new-best
    comparison against prior kept values — a positive `delta` cannot override a
    metric that is not a new best (unchanged scores with `delta: 1` would
    otherwise suppress reassessment forever). A finite signed `delta` is
    accepted only as the fallback when no comparable primary metric exists on
    this EXPT. This reads the recorded numbers; it does not re-run the metric.
    """
    metric = _numeric(expt.frontmatter.get("metric_value"))
    if metric is not None:
        best: float | None = None
        for prior in prior_expts:
            if prior.status != "kept":
                continue
            value = _numeric(prior.frontmatter.get("metric_value"))
            if value is None:
                continue
            if best is None:
                best = value
            elif direction == "lower_is_better":
                best = min(best, value)
            else:
                best = max(best, value)
        if best is None:
            return True
        if direction == "lower_is_better":
            return metric < best
        return metric > best

    delta = _numeric(expt.frontmatter.get("delta"))
    if delta is None or delta == 0:
        return False
    if direction == "lower_is_better":
        return delta < 0
    return delta > 0


def _has_meaningful_progress(
    expt: art_lib.Artifact,
    prior_expts: list[art_lib.Artifact],
    root: Path,
    direction: str,
) -> bool:
    """Existence check for one EXPT's evidence claim (REQ-043).

    Meaningful progress is either an anchored, non-repeated `research_progress`
    note, or a keep that shows a measured improvement. Outcome labels alone and
    absent/legacy annotations do not count; no predicate here claims truth.
    """
    note = _progress_note(expt)
    if (
        note
        and _evidence_ref_is_anchored(expt, note["evidence_ref"], root)
        and not _note_repeats(note, prior_expts)
    ):
        return True
    return expt.status == "kept" and _keep_shows_improvement(expt, prior_expts, direction)


def _window_has_progress(
    tail: list[art_lib.Artifact],
    ordered: list[art_lib.Artifact],
    root: Path,
    direction: str,
) -> bool:
    """True when the tail's last `_RECENT_WINDOW` EXPTs show new evidence."""
    window_ids = {expt.id for expt in tail[-_RECENT_WINDOW:]}
    for index, expt in enumerate(ordered):
        if expt.id not in window_ids:
            continue
        if _has_meaningful_progress(expt, ordered[:index], root, direction):
            return True
    return False


def _assess_loop(
    root: Path,
    comp: art_lib.Artifact,
    loop: art_lib.Artifact,
) -> list[dict[str, str]]:
    """Derive deterministic accounting signals without making research choices.

    REQ-043 semantics: warnings surface *evidence gaps* (missing agenda,
    evidence-free streaks, decisions without a progress note), never a
    count-based rotation or kill. A streak is examined over the recent window
    only (`_window_has_progress`), so progress must be recent, anchored, and
    novel; budget exhaustion stays structural because it is a hard loop bound,
    not a judgment about the research.
    """
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

    if fm.get("eda_completed"):
        add("ok", "eda", "EDA is recorded")
    else:
        add("advisory", "eda", "No completed EDA is recorded",
            f"specflow update {loop.id} --set eda_completed=true --set eda_summary=\"...\"")

    # REQ-043: decomposition is a hypothesis, not a quota. The agenda just has
    # to be recorded — its direction count is not a gate. Quick tier no longer
    # changes the check (the tier still lightens the Phase 0.7 walk).
    agenda = fm.get("research_agenda") or []
    agenda_entries = [entry for entry in agenda if isinstance(entry, dict)] if isinstance(agenda, list) else []
    if agenda_entries:
        add("ok", "agenda", f"Research agenda has {len(agenda_entries)} recorded direction(s)")
    else:
        # STORY-663/REQ-043: exit-code-bearing warn — status exits 3 while the
        # Phase 0.7 reasoning is missing entirely.
        add("warn", "agenda", "No research agenda recorded (Phase 0.7 decomposition missing)",
            f"specflow update {loop.id} --set research_agenda='[...]'")

    missing_progress = [
        str(entry.get("direction", "?"))
        for entry in agenda_entries
        if entry.get("priority") in _AGENDA_PRIORITIES and not entry.get("progress")
    ]
    if missing_progress:
        add("advisory", "progress",
            f"{len(missing_progress)} prioritized direction(s) without a progress note",
            "Record new evidence + the next decision (`progress`) on each prioritized direction.")

    if fm.get("knowledge_input"):
        add("ok", "knowledge", "Prior findings are loaded")
    elif _find_findings_for_comp(root, comp.id):
        add("advisory", "knowledge", "Competition has FINDs but LOOP knowledge_input is empty",
            f"specflow update {loop.id} --set knowledge_input='[\"FIND-NNN\"]'")
    else:
        add("ok", "knowledge", "No prior findings are available")

    # REQ-043: reassessment is evidence-sensitive and bounded to the last few
    # attempts. A sustained streak is only surfaced when its recent window
    # produced no meaningful progress — never because a count hit a
    # rotation/lock threshold (the old 2/3 category gate and 5-discard switch
    # are gone). An older keep cannot suppress the warning. Reassessment is a
    # warn: accounting, not a kill.
    expts = _find_expts_for_loop(root, loop.id)
    ordered = _ordered_expts(expts)
    direction = comp.frontmatter.get("metric_direction", "higher_is_better")
    _, category_tail = _tail_run(expts, "change_category")
    nonkept_tail: list[art_lib.Artifact] = []
    for expt in reversed(ordered):
        if expt.status not in ("discarded", "crashed"):
            break
        nonkept_tail.append(expt)
    nonkept_tail.reverse()

    reassess_reasons: list[str] = []
    if len(category_tail) >= 3 and not _window_has_progress(
        category_tail, ordered, root, direction
    ):
        category = category_tail[-1].frontmatter.get("change_category", "unspecified")
        reassess_reasons.append(
            f"{len(category_tail)} consecutive '{category}' experiments with no new evidence"
        )
    if len(nonkept_tail) >= 3 and not _window_has_progress(
        nonkept_tail, ordered, root, direction
    ):
        reassess_reasons.append(
            f"{len(nonkept_tail)} consecutive non-kept experiments with no new evidence"
        )
    if reassess_reasons:
        add("warn", "reassess", "; ".join(reassess_reasons),
            "Reassess the formulation; record `research_progress` on the recent EXPTs "
            "(an `evidence_ref` anchored to that EXPT, a distinct finding, the next "
            "decision) or a measured primary-metric improvement before another "
            "similar iteration.")
    else:
        add("ok", "reassess", "No evidence-free streak detected")

    if expts and iteration_count and iteration_count % 10 == 0 and not fm.get("condensation_briefs"):
        add("advisory", "condensation", "No condensation brief recorded at this checkpoint",
            f"specflow update {loop.id} --set condensation_briefs='[...]'")
    return signals


def _render_signals(
    signals: list[dict[str, str]], title: str = "Deterministic accounting:"
) -> None:
    icons = {
        "ok": f"{GREEN}✓{NC}",
        "advisory": f"{YELLOW}⚠{NC}",
        "warn": f"{YELLOW}⚠{NC}",
        "structural": f"{RED}✗{NC}",
    }
    print(f"{BOLD}{title}{NC}")
    for signal in signals:
        print(f"  {icons[signal['state']]} {signal['name']}: {signal['message']}")
        if signal["pointer"]:
            print(f"      {DIM}→ {signal['pointer']}{NC}")
    print()


def _has_structural(signals: list[dict[str, str]]) -> bool:
    return any(signal["state"] == "structural" for signal in signals)


# REQ-043: agenda `status` is the lifecycle state; `priority` is the decision
# and is deliberately separate from evidence. deprioritize/blocked close a
# direction out of the open list; revisit stays open (parked with intent).
_OPEN_AGENDA_STATUSES = frozenset({"unexplored", "in_progress", "promising"})
_AGENDA_PRIORITIES = frozenset({"pursue", "deprioritize", "blocked", "revisit"})
_CLOSED_AGENDA_PRIORITIES = frozenset({"deprioritize", "blocked"})
_LOOP_CENSUS_STATUSES = ("draft", "running", "completed", "plateaued", "aborted")
_OPEN_DIRECTION_LIST_CAP = 8


def _open_agenda_directions(loops: list[art_lib.Artifact]) -> list[str]:
    """Deduped open research_agenda direction strings across all LOOPs."""
    seen: set[str] = set()
    ordered: list[str] = []
    for loop in sorted(loops, key=lambda a: a.id):
        agenda = loop.frontmatter.get("research_agenda") or []
        if not isinstance(agenda, list):
            continue
        for entry in agenda:
            if not isinstance(entry, dict):
                continue
            if entry.get("status") not in _OPEN_AGENDA_STATUSES:
                continue
            if entry.get("priority") in _CLOSED_AGENDA_PRIORITIES:
                continue
            direction = entry.get("direction")
            if not isinstance(direction, str) or not direction.strip():
                continue
            if direction in seen:
                continue
            seen.add(direction)
            ordered.append(direction)
    return ordered


def _render_closure_readiness(root: Path, comp: art_lib.Artifact) -> None:
    """Print COMP-level closure facts. No goal-met / ready-to-close judgment."""
    print(f"Competition: {CYAN}{comp.id}{NC}  {comp.title}  [{comp.status}]")
    print()
    print(f"{BOLD}Closure-readiness:{NC}")

    goals = comp.frontmatter.get("goals")
    if isinstance(goals, list) and goals:
        print("  Goals:")
        for goal in goals:
            print(f"    - {goal}")
    else:
        print("  Goals: no goals recorded")

    findings = _find_findings_for_comp(root, comp.id)
    confirmed = [finding for finding in findings if finding.status == "confirmed"]
    print(f"  Findings: {len(confirmed)} confirmed / {len(findings)} total")

    window_end = comp.frontmatter.get("window_end")
    if window_end:
        try:
            end = date.fromisoformat(str(window_end))
        except ValueError:
            end = None
        if end is None:
            print(f"  Evaluation window: ends {window_end} "
                  f"(unparsed — use ISO YYYY-MM-DD)")
        elif date.today() > end:
            print(f"{YELLOW}⚠{NC}   Evaluation window elapsed {window_end} — advance "
                  f"via a successor COMP (churn rule; see rolling-evaluation.md)")
        else:
            print(f"  Evaluation window: ends {window_end}")

    loops = _find_loops_for_comp(root, comp.id)
    directions = _open_agenda_directions(loops)
    if not directions:
        print("  Open directions: no open agenda directions")
    else:
        print(f"  Open directions ({len(directions)}):")
        shown = directions[:_OPEN_DIRECTION_LIST_CAP]
        for direction in shown:
            print(f"    - {direction}")
        overflow = len(directions) - len(shown)
        if overflow:
            print(f"    +{overflow} more")

    counts = {status: 0 for status in _LOOP_CENSUS_STATUSES}
    for loop in loops:
        if loop.status in counts:
            counts[loop.status] += 1
    census = "  ".join(
        f"{status}={counts[status]}" for status in _LOOP_CENSUS_STATUSES
    )
    print(f"  LOOPs: {census}")
    print()


def _run_status(root: Path, args: dict) -> int:
    """COMP-level closure-readiness first; LOOP accounting only if a LOOP resolves.

    STORY-663 exit codes: 0 clear · 3 warn · 1/2 fail (the skill rule is
    "if status fails, stop"). Phase 0 git preconditions and the LOOP
    readiness warnings (draft LOOP, missing agenda, evidence-free streak)
    are the warn sources; a prioritized direction without a progress note is
    an advisory (exit 0, never a warn). Only structural problems (no git
    repo, multiple running LOOPs, budget exhausted) fail.
    """
    comp = _resolve_comp(root, args)
    if not comp:
        return 1

    print(f"\n{BOLD}=== Autoresearch Status ==={NC}\n")
    _render_closure_readiness(root, comp)

    # Phase 0 preconditions (STORY-663): git checks + COMP existence.
    signals = _phase0_git_signals(root)
    signals.append({
        "state": "ok", "name": "comp",
        "message": f"{comp.id} exists", "pointer": "",
    })
    _render_signals(signals, title="Phase 0 preconditions:")

    loops = _find_loops_for_comp(root, comp.id)
    explicit = args.get("loop")
    has_resolvable = explicit or any(
        loop.status in ("running", "draft") for loop in loops
    )
    if not has_resolvable:
        print(f"{YELLOW}⚠{NC} no active LOOP — COMP idle; create a LOOP to continue")
        print()
        return _status_exit_code(signals)

    loop = _resolve_loop(root, comp, args)
    if not loop:
        # Ambiguous (multiple drafts) or explicit-but-missing: a failure.
        return 1

    print(f"LOOP:        {CYAN}{loop.id}{NC}  [{loop.status}]\n")
    loop_signals: list[dict[str, str]] = []
    if loop.status == "draft":
        loop_signals.append({
            "state": "warn", "name": "loop-draft",
            "message": f"{loop.id} is still draft — start it before iterating",
            "pointer": f"specflow autoresearch run --competition {comp.id}",
        })
    else:
        loop_signals.append({
            "state": "ok", "name": "loop-draft",
            "message": f"{loop.id} is {loop.status}", "pointer": "",
        })
    loop_signals.extend(_assess_loop(root, comp, loop))
    _render_signals(loop_signals)
    return _status_exit_code(signals + loop_signals)


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
    print("  Phase 2: Ideate — Reassess the evidence; pick the next formulation by mission value")
    print("  Phase 3: Modify — Implement ONE coherent hypothesis (coordinated changes allowed when logged)")
    print("  Phase 4: Commit — git add <files> && git commit -m 'experiment(<scope>): ...'")
    print("  Phase 5: Verify — Run COMP.verify_command, extract metric")
    print("  Phase 5.1: Noise — Multi-run median if metric is noisy")
    print("  Phase 5.5: Guard — Run guard_command if defined on COMP")
    print("  Phase 6: Decide — kept / discarded / crashed / no_op; log hypothesis_outcome "
          "(supported/not_supported/inconclusive/invalid) + next decision")
    print("  Phase 7: Log — Create EXPT artifact (add --research-progress when the "
          "iteration produced evidence), update LOOP totals")
    print("  Phase 8: Repeat or Complete — Reassess an evidence-free line over the last 3 "
          "attempts; budget bounds; condense every 10")
    print(f"{DIM}No rotation quota and no failure-count kill: counts are accounting, not judgment.{NC}")
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


def _parse_research_progress(raw: str | None) -> dict[str, str] | None:
    """Parse `autoresearch log --research-progress` JSON (REQ-043).

    Returns None when the flag is absent. Raises ValueError when the payload
    is not a JSON object with non-empty string `evidence_ref`, `finding`, and
    `next_decision` — the producer fails fast so a malformed record never
    reaches the status accounting (which reads malformed records as no
    evidence).
    """
    if raw is None:
        return None
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("must be a JSON object")
    note: dict[str, str] = {}
    for key in _PROGRESS_FIELDS:
        value = parsed.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"missing non-empty string field '{key}'")
        note[key] = value.strip()
    return note


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

    try:
        research_progress = _parse_research_progress(args.get("research_progress"))
    except ValueError as exc:
        print(f"{RED}✗ Invalid --research-progress: {exc}.{NC}")
        print(f"{DIM}  Expected JSON: "
              f'{{"evidence_ref": "EXPT-NNN | commit:<sha> | <logged path>", '
              f'"finding": "...", "next_decision": "pursue|deprioritize|blocked|revisit"}}{NC}')
        return 1

    extra_fields = {}
    set_fields = args.get("set_fields") or []
    # Reserved: these keys are owned by the command itself (traceability edges
    # and parent fields — STORY-636/637). A --set override could silently
    # strip the belongs_to link edge or desync frontmatter from it. REQ-043
    # adds `research_progress` to the reserved set: the dedicated
    # --research-progress flag is the one validated producer.
    reserved = {
        "links", "loop", "competition", "status", "id", "type", "title",
        "research_progress",
    }
    for entry in set_fields:
        if "=" not in entry:
            print(f"{RED}✗ Invalid --set value '{entry}'. Expected KEY=VALUE.{NC}")
            return 1
        key, raw = entry.split("=", 1)
        key = key.strip()
        if not key:
            print(f"{RED}✗ Invalid --set value '{entry}'. Empty key.{NC}")
            return 1
        if key in reserved:
            print(
                f"{RED}✗ --set {key} is reserved (owned by 'autoresearch log'; "
                f"use the dedicated flags or 'specflow update <ID> --add-link').{NC}"
            )
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
    if research_progress is not None:
        create_kwargs["research_progress"] = research_progress

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
