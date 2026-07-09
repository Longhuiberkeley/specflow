"""specflow phase-status — read-only advisory on whether the current phase is ready to close.

Aggregates existing primitives (artifact status counts, unresolved suspects, the next
executable wave, and the matching phase-gate's automated checks) into a single advisory:
ready to close / blocked on X / suspects open Y. This is accounting, not policing — it
advises only; `specflow done` remains the act that actually closes a phase.
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
from typing import Any

from specflow.lib import artifacts as art_lib
from specflow.lib import config as config_lib
from specflow.lib.learning import suggest_next_phase
from specflow.lib.waves import compute_waves, filter_executable_stories
from specflow.lib.display import RED, GREEN, YELLOW, CYAN, BOLD, NC

# phase → the gate consulted when leaving that phase (advisory — accounting, not
# policing). All six REQ-004 §6 transitions are mapped so every phase-gate
# checklist template is reachable; `phase-status` advises, it never blocks.
_GATE_FOR_PHASE = {
    "idle": "idle-to-discovering",
    "discovering": "discovering-to-specifying",
    "specifying": "specifying-to-planning",
    "planning": "planning-to-executing",
    "executing": "executing-to-verifying",
    "verifying": "verifying-to-complete",
}


def _gate_result(root: Path, phase: str) -> tuple[bool, str] | None:
    """Run the matching phase gate's automated checks; return (green, detail) or None.

    Best-effort: returns None if there is no gate for this phase or it cannot run.
    """
    gate = _GATE_FOR_PHASE.get(phase)
    if not gate:
        return None
    try:
        from specflow.commands import artifact_lint as lint_cmd
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = lint_cmd._run_gate_check(root, gate)  # noqa: SLF001 (same-package reuse)
    except Exception:
        return None
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    summary = lines[-1] if lines else ("PASS" if rc == 0 else "FAIL")
    return (rc == 0, summary)


def run(root: Path, args: dict[str, Any]) -> int:
    root = root.resolve()
    config = config_lib.read_config(root)
    state = config_lib.read_state(root)
    if not config or not state:
        print(f"{RED}✗ SpecFlow is not initialized here. Run 'uv run specflow init'.{NC}")
        return 1

    phase = state.get("current", "idle")
    artifacts = art_lib.discover_artifacts(root)

    status_counts: dict[str, int] = {}
    for a in artifacts:
        s = a.status or "draft"
        status_counts[s] = status_counts.get(s, 0) + 1

    suspects = [a for a in artifacts if a.suspect]

    stories = filter_executable_stories(art_lib.discover_artifacts(root, "story"))
    next_wave: list[str] = []
    if stories:
        wr = compute_waves(stories)
        if wr.get("ok") and wr.get("waves"):
            next_wave = wr["waves"][0]

    gate = _gate_result(root, phase)

    print(f"\n{CYAN}SpecFlow Phase Status{NC} — phase: {BOLD}{phase}{NC}")
    print(f"{CYAN}{'─' * 50}{NC}")

    print(f"\n  {BOLD}Artifacts by status{NC}")
    if status_counts:
        for s, n in sorted(status_counts.items()):
            print(f"    {s}: {n}")
    else:
        print(f"    (none)")

    if suspects:
        ids = ", ".join(a.id for a in suspects[:8])
        more = f" (+{len(suspects) - 8} more)" if len(suspects) > 8 else ""
        print(f"\n  {YELLOW}⚠ Suspects open: {len(suspects)}{NC} — {ids}{more}")
    else:
        print(f"\n  {GREEN}✓ No unresolved suspects{NC}")

    if next_wave:
        print(f"\n  {BOLD}Next executable wave{NC}: {len(next_wave)} story(ies) — {', '.join(next_wave)}")
    else:
        print(f"\n  {BOLD}Next executable wave{NC}: (none ready)")

    if gate is not None:
        green, detail = gate
        mark = f"{GREEN}✓ green (automated blocking checks pass){NC}" if green \
            else f"{RED}✗ not green (blocking checks failing){NC}"
        print(f"\n  {BOLD}Phase gate ({phase}){NC}: {mark}")
        print(f"    {detail}")

    # Advisory verdict — accounting, not policing.
    print(f"\n  {BOLD}Advisory{NC}")
    blockers: list[str] = []
    if suspects:
        blockers.append(f"{len(suspects)} suspect(s) open")
    if gate is not None and not gate[0]:
        blockers.append(f"phase gate ({phase}) not green")
    if blockers:
        print(f"    {YELLOW}Not ready to close — blocked on: {', '.join(blockers)}.{NC}")
        print(f"    Resolve, then `specflow done` to close the phase.")
    else:
        print(f"    {GREEN}Ready to close — run `specflow done` when you intend to advance.{NC}")

    try:
        suggestion = suggest_next_phase(root)
        if suggestion:
            print(f"    {suggestion}")
    except Exception:
        pass
    print()
    return 0
