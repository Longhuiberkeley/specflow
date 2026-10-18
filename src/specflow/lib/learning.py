"""Reactive learning engine and phase closure via specflow done."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from specflow.lib.artifacts import Artifact, _normalize_str_list, discover_artifacts
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
    # Research lenses (autoresearch COMP/LOOP/EXPT/FIND); same catalog,
    # same PREV capture path (F-134).
    "leakage_audit",
    "overfitting_multiple_comparisons",
    "baseline_sanity",
    "distribution_shift",
    "ablation_attribution",
    "metric_validity",
    "reproducibility",
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


def create_pattern_from_divergence(
    root: Path,
    artifact: Artifact,
    *,
    actual: int,
    expected: int,
) -> Path | None:
    """Seed a PREV prevention pattern from a divergent ``verify_run``.

    STORY-624 outcome feedback loop: when a verification contract records a
    divergent exit code (``actual != expected``), feed it into the EXISTING
    learnings surface so a repeated failure mode informs the next wave.
    Reuses :func:`extract_prevention_pattern` + :func:`persist_prevention_pattern`
    — no new artifact type, no new link roles (D-18 respected). The caller
    gates this on an opt-in flag (``verify --seed-prev``); it never blocks
    (``verify`` still exits 0).

    A ``source: verify-divergence`` provenance marker distinguishes
    verify-sourced PREVs from review-sourced ones without changing the
    PREV schema (the YAML checklist has no schema-strictness).

    Returns the created Path, or None if persistence failed.
    """
    pattern = extract_prevention_pattern(
        story=artifact,
        pattern_description=(
            f"Prevent recurrence: {artifact.id} verification contract divergence"
        ),
        check_text=(
            f"the {artifact.id} verify_command exit code matches "
            f"verify_exit_code (recorded divergence: exit={actual}, "
            f"expected={expected})"
        ),
    )
    pattern["items"][0]["severity"] = "warning"
    pattern["mode"] = "reactive"
    pattern["source"] = "verify-divergence"
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
    """Write a prevention pattern to .specflow/checklists/learned/.

    The PREV number is allocated by exclusive create under the mutation lock
    (DEC-093): a concurrent writer that took the same number makes this one
    move on to the next, never replace the other's pattern.
    """
    from specflow.lib import locks as locks_lib

    learned_dir = root / ".specflow" / "checklists" / "learned"
    learned_dir.mkdir(parents=True, exist_ok=True)

    with locks_lib.mutation_lock(root, holder="prev-pattern"):
        num = _next_prev_number(root)
        while True:
            pattern_id = f"PREV-{num:03d}"
            pattern["id"] = pattern_id
            # Assign item IDs
            for i, item in enumerate(pattern.get("items", [])):
                item["id"] = f"{pattern_id}-{i+1:02d}"
            path = learned_dir / f"{pattern_id}.yaml"
            text = yaml.dump(pattern, default_flow_style=False, sort_keys=False)
            if locks_lib.exclusive_write(path, text):
                return path
            num += 1


def list_learned_patterns(root: Path, *, include_retired: bool = False) -> list[dict[str, Any]]:
    """Read all PREV-*.yaml from .specflow/checklists/learned/.

    Retired patterns (``retired: true``, set by ``specflow patterns retire``)
    are skipped unless ``include_retired`` — their files stay on disk so the
    PREV number is never reused.
    """
    learned_dir = root / ".specflow" / "checklists" / "learned"
    if not learned_dir.exists():
        return []

    patterns: list[dict[str, Any]] = []
    for f in sorted(learned_dir.glob("PREV-*.yaml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                if not include_retired and is_retired(data):
                    continue
                patterns.append(data)
        except Exception:
            continue

    return patterns


# Release tags (``v1.17``, ``v1.17.5``) mark WHEN an artifact shipped, not
# WHAT it touches — a PREV keyed on one never matches the next release's work.
_RELEASE_TAG = re.compile(r"^v\d")
_PREV_ID = re.compile(r"PREV-\d+")


def is_retired(pattern: dict[str, Any]) -> bool:
    return pattern.get("retired") is True


def pattern_tags(pattern: dict[str, Any]) -> list[str]:
    """The pattern's ``applies_to.tags`` as a normalized ``list[str]``."""
    applies_to = pattern.get("applies_to")
    if not isinstance(applies_to, dict):
        return []
    return _normalize_str_list(applies_to.get("tags", []))


def is_inert(pattern: dict[str, Any]) -> bool:
    """A live PREV with no tags never matches an artifact (set intersection),
    so checklist assembly can never surface it. The one shared definition used
    by DEF closure, ``project-audit`` (prev/inert) and ``brief``."""
    return not is_retired(pattern) and not pattern_tags(pattern)


def inert_patterns(root: Path) -> list[dict[str, Any]]:
    return [p for p in list_learned_patterns(root) if is_inert(p)]


def inherited_tags(root: Path, defect: Artifact) -> list[str]:
    """Matchable tags for a PREV seeded from ``defect`` (REQ-067 OBL-3).

    The DEF's own tags plus the tags of every REQ it ``fails_to_meet``,
    order-preserving and de-duplicated, minus release tags (``^v\\d``).
    """
    from specflow.lib import artifacts as art_lib

    collected: list[str] = list(_normalize_str_list(defect.tags))
    for link in defect.links:
        if link.role != "fails_to_meet":
            continue
        path = art_lib.resolve_link_target(root, link.target)
        req = art_lib.parse_artifact(path) if path else None
        if req is not None:
            collected.extend(_normalize_str_list(req.tags))
    out: list[str] = []
    for tag in collected:
        if tag and not _RELEASE_TAG.match(tag) and tag not in out:
            out.append(tag)
    return out


def _learned_pattern_path(root: Path, pattern_id: str) -> Path:
    if not _PREV_ID.fullmatch(pattern_id or ""):
        raise ValueError(f"'{pattern_id}' is not a PREV id (expected PREV-NNN)")
    path = root / ".specflow" / "checklists" / "learned" / f"{pattern_id}.yaml"
    if not path.is_file():
        raise ValueError(f"pattern {pattern_id} not found under .specflow/checklists/learned/")
    return path


def _rewrite_pattern(root: Path, pattern_id: str, mutate) -> dict[str, Any]:
    """Read-modify-write one PREV YAML under the mutation lock (atomic replace)."""
    from specflow.lib import locks as locks_lib

    with locks_lib.mutation_lock(root, holder="prev-pattern"):
        path = _learned_pattern_path(root, pattern_id)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"pattern {pattern_id} is not a YAML mapping")
        mutate(data)
        locks_lib.atomic_write(
            path, yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        )
        return data


def update_pattern_tags(root: Path, pattern_id: str, tags: list[str]) -> dict[str, Any]:
    """Set a PREV's ``applies_to.tags`` to exactly ``tags`` (order kept, deduped)."""
    clean: list[str] = []
    for tag in tags:
        tag = str(tag).strip()
        if tag and tag not in clean:
            clean.append(tag)
    if not clean:
        raise ValueError("at least one non-empty tag is required (empty tags leave the pattern inert)")

    def _set(data: dict[str, Any]) -> None:
        applies_to = data.get("applies_to")
        if not isinstance(applies_to, dict):
            applies_to = {}
            data["applies_to"] = applies_to
        applies_to["tags"] = clean

    return _rewrite_pattern(root, pattern_id, _set)


def retire_pattern(root: Path, pattern_id: str) -> dict[str, Any]:
    """Mark a PREV ``retired: true``; listing and checklist assembly skip it."""
    return _rewrite_pattern(root, pattern_id, lambda data: data.__setitem__("retired", True))


def close_phase(root: Path) -> dict[str, Any]:
    """Close the current phase: archive to history, clear execution state.

    The state.yaml read-modify-write runs under the repo-wide mutation lock,
    so a concurrent state writer's update is never lost (STORY-696 AC2).

    Returns summary dict.
    """
    from specflow.lib import locks as locks_lib

    with locks_lib.mutation_lock(root, holder="close-phase"):
        return _close_phase_locked(root)


def _close_phase_locked(root: Path) -> dict[str, Any]:
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

    The state.yaml read-modify-write runs under the repo-wide mutation lock
    (STORY-696 AC2).

    Returns {"ok": False, "error": ...} for an unrecognized phase or unreadable
    state, else {"ok": True, "old_phase", "new_phase", "rewind"}.
    """
    from specflow.lib import locks as locks_lib

    with locks_lib.mutation_lock(root, holder="phase-set"):
        return _set_phase_locked(root, target, reason)


def _set_phase_locked(root: Path, target: str, reason: str | None) -> dict[str, Any]:
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
