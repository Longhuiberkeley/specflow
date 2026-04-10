"""specflow status — Show project dashboard."""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import config as config_lib

# Color codes
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
NC = "\033[0m"  # No Color

# Display labels for artifact types
TYPE_LABELS = {
    "specs/requirements": "REQ",
    "specs/architecture": "ARCH",
    "specs/detailed-design": "DDD",
    "specs/unit-tests": "UT",
    "specs/integration-tests": "IT",
    "specs/qualification-tests": "QT",
    "work/stories": "STORY",
    "work/spikes": "SPIKE",
    "work/decisions": "DEC",
    "work/defects": "DEF",
}


def _count_by_type(root: Path) -> dict[str, int]:
    """Count artifacts by their type prefix."""
    artifacts = art_lib.discover_artifacts(root)
    counts: dict[str, int] = {}

    for art in artifacts:
        prefix = art_lib.get_prefix_from_id(art.id)
        label = prefix if prefix else art.type
        counts[label] = counts.get(label, 0) + 1

    return counts


def _count_by_status(root: Path) -> dict[str, int]:
    """Count artifacts by their status."""
    artifacts = art_lib.discover_artifacts(root)
    counts: dict[str, int] = {}

    for art in artifacts:
        s = art.status if art.status else "draft"
        counts[s] = counts.get(s, 0) + 1

    return counts


def _count_link_health(root: Path) -> dict[str, int]:
    """Count broken links and orphans."""
    artifacts = art_lib.discover_artifacts(root)
    id_index = art_lib.build_id_index(artifacts)

    broken = 0
    for art in artifacts:
        for link in art.links:
            if link.target not in id_index:
                broken += 1

    orphans = len(art_lib.find_orphans(artifacts))
    missing_pairs = len(art_lib.find_missing_v_pairs(artifacts))

    return {"broken": broken, "orphans": orphans, "missing_pairs": missing_pairs}


def _count_issues(root: Path) -> int:
    """Count artifacts with suspect=true."""
    artifacts = art_lib.discover_artifacts(root)
    return sum(1 for a in artifacts if a.suspect)


def _suggest_action(root: Path, phase: str, artifact_counts: dict[str, int]) -> str:
    """Suggest next action based on current phase and artifact state."""
    total = sum(artifact_counts.values())

    if total == 0:
        return "Start with 'specflow-new' to capture your first requirement"

    req_count = artifact_counts.get("REQ", 0)
    arch_count = artifact_counts.get("ARCH", 0)
    story_count = artifact_counts.get("STORY", 0)

    if phase == "idle":
        return "Run 'specflow-new' to begin discovery"
    elif phase == "discovering":
        return "Continue capturing requirements with 'specflow-new'"
    elif phase == "specifying":
        if req_count > 0 and arch_count == 0:
            return "Run 'specflow-plan' to create architecture and stories"
        else:
            return "Review and approve requirements before planning"
    elif phase == "planning":
        if story_count == 0:
            return "Run 'specflow-plan' to decompose requirements into stories"
        else:
            return "Review architecture and stories, then run 'specflow-go'"
    elif phase == "executing":
        return "Run 'specflow-go' to execute story waves"
    elif phase == "verifying":
        return "Run 'specflow-check' to review artifacts"
    elif phase == "complete":
        return "Run 'specflow-done' to close the phase"

    return "Run 'specflow validate' to check artifact integrity"


def run(root: Path, args: dict) -> int:
    """Execute specflow status.

    Args:
        root: Project root directory
        args: Parsed arguments (currently unused)

    Returns:
        Exit code (0 = success, 1 = not initialized)
    """
    root = root.resolve()

    # Check if SpecFlow is initialized
    config = config_lib.read_config(root)
    state = config_lib.read_state(root)

    if not config or not state:
        print("SpecFlow is not initialized in this project.")
        print("Run 'uv run specflow init' to scaffold the project.")
        return 1

    project_name = config.get("project", {}).get("name", "unknown")
    phase = state.get("current", "idle")
    created = config.get("project", {}).get("created", "unknown")

    # Count artifacts
    by_type = _count_by_type(root)
    total = sum(by_type.values())

    # Count by status
    by_status = _count_by_status(root)

    # Link health
    health = _count_link_health(root)

    # Issues
    issues = _count_issues(root)

    # Print dashboard
    print(f"\n{CYAN}SpecFlow Status{NC}")
    print(f"{CYAN}{'─' * 50}{NC}")
    print(f"  Phase:     {phase}")
    print(f"  Project:   {project_name}")
    print(f"  Created:   {created}")

    # Specs
    spec_types = ["REQ", "ARCH", "DDD", "UT", "IT", "QT"]
    spec_parts = []
    for t in spec_types:
        c = by_type.get(t, 0)
        spec_parts.append(f"{c} {t}")
    print(f"\n  Specs:   {' | '.join(spec_parts)}")

    # Work
    work_types = ["STORY", "SPIKE", "DEC", "DEF"]
    work_parts = []
    for t in work_types:
        c = by_type.get(t, 0)
        work_parts.append(f"{c} {t}")
    print(f"  Work:    {' | '.join(work_parts)}")

    # Status distribution
    status_parts = []
    for s in ["draft", "approved", "implemented", "verified"]:
        c = by_status.get(s, 0)
        if c > 0:
            status_parts.append(f"{c} {s}")
    if status_parts:
        print(f"\n  Status:  {' | '.join(status_parts)}")

    # Link health
    print(f"\n  Links:   {health['broken']} broken | {health['orphans']} orphans | {health['missing_pairs']} missing verification pairs")

    # Issues
    if issues > 0:
        print(f"\n  {YELLOW}⚠ Issues: {issues} artifact(s) flagged as suspect{NC}")

    # Suggested next action
    suggestion = _suggest_action(root, phase, by_type)
    print(f"\n  → {suggestion}")
    print()

    return 0
