"""Reactive learning engine and phase closure via specflow done."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from specflow.lib.artifacts import Artifact, discover_artifacts
from specflow.lib.config import read_state, write_state


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

    write_state(root, state)

    # Count artifacts by status
    all_artifacts = discover_artifacts(root)
    status_counts: dict[str, int] = {}
    for art in all_artifacts:
        status_counts[art.status] = status_counts.get(art.status, 0) + 1

    return {
        "ok": True,
        "phase_closed": current_phase,
        "artifact_counts": status_counts,
        "history_entries": len(history),
    }


def suggest_next_phase(root: Path) -> str:
    """Suggest the next phase based on current state."""
    state = read_state(root)
    current = state.get("current", "idle")

    phase_order = [
        "idle",
        "discovering",
        "specifying",
        "planning",
        "executing",
        "verifying",
        "complete",
    ]

    try:
        idx = phase_order.index(current)
        if idx < len(phase_order) - 1:
            next_phase = phase_order[idx + 1]
            return f"Suggested next phase: {next_phase}"
        return "Project is complete."
    except ValueError:
        return f"Unknown current phase: {current}"
