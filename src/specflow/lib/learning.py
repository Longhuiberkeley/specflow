"""Reactive learning engine and phase closure via specflow done."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from specflow.lib.artifacts import Artifact, discover_artifacts
from specflow.lib.config import read_config, read_state, write_state


# Canonical lifecycle phase order (REQ-004 §6 / ARCH-002). Single source of
# truth: close_phase() advances `current` along this list and suggest_next_phase()
# reads the next entry. Accounting only — nothing here gates or blocks a transition
# (frozen accounting-not-policing); advisory readiness is `specflow phase-status`.
PHASE_ORDER: list[str] = [
    "idle",
    "discovering",
    "specifying",
    "planning",
    "executing",
    "verifying",
    "complete",
]


def next_phase(current: str) -> str:
    """Return the phase that follows ``current`` in PHASE_ORDER.

    Returns ``current`` unchanged if it is the terminal phase (``complete``) or
    not in PHASE_ORDER, so the machine never invents a phase — it records only.
    """
    try:
        idx = PHASE_ORDER.index(current)
    except ValueError:
        return current
    if idx < len(PHASE_ORDER) - 1:
        return PHASE_ORDER[idx + 1]
    return current


def extract_prevention_pattern(
    story: Artifact,
    pattern_description: str,
    check_text: str,
) -> dict[str, Any]:
    """Build a PREV-*.yaml prevention pattern structure.

    Returns the dict ready for persist_prevention_pattern().
    """
    return {
        "id": "",  # Assigned during persist
        "name": pattern_description,
        "discovered_from": story.id,
        "mode": "reactive",
        "pattern": pattern_description,
        "applies_to": {
            "tags": list(story.tags),
        },
        "items": [
            {
                "id": "",  # Assigned during persist
                "check": check_text,
                "severity": "warning",
                "automated": False,
                "mode": "reactive",
            }
        ],
    }


LEARNABLE_SEVERITIES = {"blocking", "warning"}
DEFAULT_LEARNABLE_TECHNIQUES = {
    "checklist-run",
    "devils_advocate",
    "premortem",
    "assumption_surfacing",
    "red_blue_team",
    "stress_scale",
    "dependency_shock",
    "reversal",
    "five_whys",
    "outside_view",
    "worst_case_user",
    "regulator",
    "temporal_drift",
    "composition",
    "inversion",
    "competitor_framing",
    "cost_scaling",
    "audit-horizontal",
    "audit-vertical",
    "audit-cross-cutting",
}


def learnable_techniques(root: Path) -> set[str]:
    cfg = read_config(root)
    if not isinstance(cfg, dict):
        return DEFAULT_LEARNABLE_TECHNIQUES
    learning_cfg = cfg.get("learning", {})
    if not isinstance(learning_cfg, dict):
        return DEFAULT_LEARNABLE_TECHNIQUES
    custom = learning_cfg.get("learnable_techniques")
    if isinstance(custom, list) and custom:
        return set(custom)
    return DEFAULT_LEARNABLE_TECHNIQUES


def max_patterns_per_session(root: Path) -> int:
    """Return max patterns to create per review session (configurable)."""
    cfg = read_config(root)
    if not isinstance(cfg, dict):
        return 3
    learning_cfg = cfg.get("learning", {})
    if not isinstance(learning_cfg, dict):
        return 3
    max_val = learning_cfg.get("max_patterns_per_session")
    if isinstance(max_val, int) and max_val > 0:
        return max_val
    return 3


def create_pattern_from_finding(
    root: Path,
    artifact: Artifact,
    check_text: str,
    reason: str,
    severity: str,
) -> Path | None:
    """Create a PREV-*.yaml from a review finding.

    Only creates patterns for severity in (blocking, warning).
    Returns the Path of the created file, or None if skipped.
    """
    if severity not in LEARNABLE_SEVERITIES:
        return None

    pattern = extract_prevention_pattern(
        story=artifact,
        pattern_description=f"Prevent recurrence: {check_text}",
        check_text=f"Verify that {reason}",
    )
    pattern["items"][0]["severity"] = severity
    return persist_prevention_pattern(root, pattern)


def _next_prev_number(root: Path) -> int:
    """Determine the next PREV number from existing learned patterns."""
    learned_dir = root / ".specflow" / "checklists" / "learned"
    if not learned_dir.exists():
        return 1

    max_num = 0
    for f in learned_dir.glob("PREV-*.yaml"):
        try:
            num_str = f.stem.split("-")[1]
            num = int(num_str)
            if num > max_num:
                max_num = num
        except (IndexError, ValueError):
            continue

    return max_num + 1


def persist_prevention_pattern(root: Path, pattern: dict[str, Any]) -> Path:
    """Write a prevention pattern to .specflow/checklists/learned/."""
    learned_dir = root / ".specflow" / "checklists" / "learned"
    learned_dir.mkdir(parents=True, exist_ok=True)

    num = _next_prev_number(root)
    pattern_id = f"PREV-{num:03d}"
    pattern["id"] = pattern_id

    # Assign item IDs
    for i, item in enumerate(pattern.get("items", [])):
        item["id"] = f"{pattern_id}-{i+1:02d}"

    filename = f"{pattern_id}.yaml"
    path = learned_dir / filename

    path.write_text(
        yaml.dump(pattern, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return path


def list_learned_patterns(root: Path) -> list[dict[str, Any]]:
    """Read all PREV-*.yaml from .specflow/checklists/learned/."""
    learned_dir = root / ".specflow" / "checklists" / "learned"
    if not learned_dir.exists():
        return []

    patterns: list[dict[str, Any]] = []
    for f in sorted(learned_dir.glob("PREV-*.yaml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                patterns.append(data)
        except Exception:
            continue

    return patterns


def close_phase(root: Path) -> dict[str, Any]:
    """Close the current phase: archive to history, clear execution state.

    Returns summary dict.
    """
    state = read_state(root)
    if not state:
        return {"ok": False, "error": "Cannot read state.yaml"}

    current_phase = state.get("current", "idle")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Archive current phase to history
    history = state.get("history", [])
    if not isinstance(history, list):
        history = []

    # Find existing history entry for current phase and add exit date
    updated = False
    for entry in history:
        if isinstance(entry, dict) and entry.get("phase") == current_phase and "exited" not in entry:
            entry["exited"] = now
            updated = True
            break

    if not updated:
        history.append({"phase": current_phase, "entered": now, "exited": now})

    state["history"] = history

    # Clear execution state if present
    if "execution" in state:
        del state["execution"]

    # Advance the phase (accounting — record progression; never a gate/block).
    # Closing the current phase moves `current` to the next phase so the machine
    # honestly tracks where the project is (REQ-004 §6 / ARCH-002). Advisory
    # readiness is `specflow phase-status`'s job; `done` only records the advance.
    new_phase = next_phase(current_phase)
    if new_phase != current_phase:
        state["current"] = new_phase
        # Record entry into the new phase (ARCH-002 entered/exited history model).
        history.append({"phase": new_phase, "entered": now})
        state["history"] = history

    write_state(root, state)

    # Count artifacts by status
    all_artifacts = discover_artifacts(root)
    status_counts: dict[str, int] = {}
    for art in all_artifacts:
        status_counts[art.status] = status_counts.get(art.status, 0) + 1

    return {
        "ok": True,
        "phase_closed": current_phase,
        "phase_entered": new_phase,
        "artifact_counts": status_counts,
        "history_entries": len(history),
    }


def set_phase(root: Path, target: str, reason: str | None = None) -> dict[str, Any]:
    """Record a phase transition to ``target`` — forward or reverse.

    Accounting-not-policing (frozen philosophy): this RECORDS a transition, it
    never gates one. Unlike ``close_phase`` (which always advances to
    ``next_phase(current)``), this lets the machine be pointed at any phase in
    PHASE_ORDER, including one earlier than the current phase (a "rewind" —
    e.g. "go back to requirements"), so `state.current` stays honest and
    `brief --next` routes correctly after a reverse-lifecycle move.

    Mirrors close_phase()'s history bookkeeping: the current phase's open
    history entry gets an "exited" stamp, and a new entry for `target` is
    appended with "entered". When `reason` is given it is recorded on that new
    entry; when `target` is earlier than the current phase in PHASE_ORDER, the
    entry is also stamped "rewind": true.

    Returns {"ok": False, "error": ...} for an unrecognized phase or unreadable
    state, else {"ok": True, "old_phase", "new_phase", "rewind"}.
    """
    if target not in PHASE_ORDER:
        return {
            "ok": False,
            "error": f"Unknown phase '{target}'. Valid phases: {', '.join(PHASE_ORDER)}",
        }

    state = read_state(root)
    if not state:
        return {"ok": False, "error": "Cannot read state.yaml"}

    current_phase = state.get("current", "idle")

    if target == current_phase:
        return {"ok": True, "old_phase": current_phase, "new_phase": target, "rewind": False}

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    history = state.get("history", [])
    if not isinstance(history, list):
        history = []

    # Stamp "exited" on the current phase's open history entry (mirrors close_phase).
    updated = False
    for entry in history:
        if isinstance(entry, dict) and entry.get("phase") == current_phase and "exited" not in entry:
            entry["exited"] = now
            updated = True
            break
    if not updated:
        history.append({"phase": current_phase, "entered": now, "exited": now})

    try:
        cur_idx = PHASE_ORDER.index(current_phase)
        target_idx = PHASE_ORDER.index(target)
        rewind = target_idx < cur_idx
    except ValueError:
        # current_phase isn't a recognized phase — can't tell direction; not a rewind.
        rewind = False

    new_entry: dict[str, Any] = {"phase": target, "entered": now}
    if reason:
        new_entry["reason"] = reason
    if rewind:
        new_entry["rewind"] = True
    history.append(new_entry)

    state["history"] = history
    state["current"] = target

    # Leaving `executing` (in either direction) invalidates any in-flight execution state.
    if current_phase == "executing" and "execution" in state:
        del state["execution"]

    write_state(root, state)

    return {"ok": True, "old_phase": current_phase, "new_phase": target, "rewind": rewind}


def suggest_next_phase(root: Path) -> str:
    """Suggest the next phase based on current state."""
    state = read_state(root)
    current = state.get("current", "idle")

    nxt = next_phase(current)
    if nxt == current and current == "complete":
        return "Project is complete."
    if nxt == current:
        return f"Unknown current phase: {current}"
    return f"Suggested next phase: {nxt}"
