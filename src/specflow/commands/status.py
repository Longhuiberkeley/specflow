"""specflow status — Show project dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import config as config_lib
from specflow.lib.display import RED, GREEN, YELLOW, CYAN, NC

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


def _compute_coverage(artifacts: list[art_lib.Artifact]) -> dict[str, Any]:
    """Compute coverage metrics from artifact data."""
    id_index = art_lib.build_id_index(artifacts)

    reqs = [a for a in artifacts if a.type == "requirement"]
    req_with_stories = 0
    for req in reqs:
        for other in artifacts:
            for link in other.links:
                if link.target == req.id and link.role == "implements":
                    req_with_stories += 1
                    break
            else:
                continue
            break
    req_total = len(reqs)
    req_pct = (req_with_stories / req_total * 100) if req_total > 0 else None

    stories = [a for a in artifacts if a.type == "story"]
    story_with_test = 0
    total_tests = 0
    for story in stories:
        tests_for_story = 0
        for link in story.links:
            if link.role == "verified_by":
                tests_for_story += 1
        for other in artifacts:
            for olink in other.links:
                if olink.target == story.id and olink.role == "verified_by":
                    tests_for_story += 1
        if tests_for_story > 0:
            story_with_test += 1
            total_tests += tests_for_story
    story_total = len(stories)
    story_pct = (story_with_test / story_total * 100) if story_total > 0 else None
    avg_tests = (total_tests / story_total) if story_total > 0 else 0.0

    spec_types = list(art_lib.V_MODEL_PAIRS.keys())
    total_spec = 0
    verified_spec = 0
    for a in artifacts:
        if a.type in spec_types:
            total_spec += 1
            has_v = False
            for other in artifacts:
                for link in other.links:
                    if link.target == a.id and link.role == "verified_by":
                        has_v = True
                        break
                if has_v:
                    break
            if has_v:
                verified_spec += 1
    chain_pct = (verified_spec / total_spec * 100) if total_spec > 0 else None

    return {
        "req_total": req_total,
        "req_covered": req_with_stories,
        "req_pct": req_pct,
        "story_total": story_total,
        "story_tested": story_with_test,
        "story_pct": story_pct,
        "story_avg_tests": avg_tests,
        "chain_total": total_spec,
        "chain_verified": verified_spec,
        "chain_pct": chain_pct,
    }


def _count_issues(root: Path) -> int:
    """Count artifacts with suspect=true."""
    artifacts = art_lib.discover_artifacts(root)
    return sum(1 for a in artifacts if a.suspect)


def _suggest_action(root: Path, phase: str, artifact_counts: dict[str, int]) -> str:
    """Suggest next action based on current phase and artifact state."""
    total = sum(artifact_counts.values())

    if total == 0:
        return "Use /specflow-discover to capture your first requirement"

    req_count = artifact_counts.get("REQ", 0)
    arch_count = artifact_counts.get("ARCH", 0)
    story_count = artifact_counts.get("STORY", 0)

    if phase == "idle":
        return "Use /specflow-discover to begin discovery"
    elif phase == "discovering":
        return "Continue capturing requirements with /specflow-discover"
    elif phase == "specifying":
        if req_count > 0 and arch_count == 0:
            return "Use /specflow-plan to create architecture and stories"
        else:
            return "Review and approve requirements before planning"
    elif phase == "planning":
        if story_count == 0:
            return "Use /specflow-plan to decompose requirements into stories"
        else:
            return "Review architecture and stories, then use /specflow-execute"
    elif phase == "executing":
        return "Use /specflow-execute to implement story waves"
    elif phase == "verifying":
        return "Use /specflow-artifact-review to review artifacts"
    elif phase == "complete":
        return "Use /specflow-ship to close the phase"

    return "Run 'specflow artifact-lint' to check artifact integrity"


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

    # Coverage metrics
    all_artifacts = art_lib.discover_artifacts(root)
    coverage = _compute_coverage(all_artifacts)

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

    # Coverage
    cov_parts = []
    if coverage["req_pct"] is not None:
        cov_parts.append(f"REQ {coverage['req_pct']:.0f}% ({coverage['req_covered']}/{coverage['req_total']})")
    if coverage["story_pct"] is not None:
        cov_parts.append(f"STORY test {coverage['story_pct']:.0f}% ({coverage['story_tested']}/{coverage['story_total']}) | {coverage['story_avg_tests']:.1f} tests/story avg")
    if coverage["chain_pct"] is not None:
        cov_parts.append(f"Chain {coverage['chain_pct']:.0f}% ({coverage['chain_verified']}/{coverage['chain_total']})")
    if cov_parts:
        print(f"\n  Coverage: {' | '.join(cov_parts)}")

    # Issues
    if issues > 0:
        print(f"\n  {YELLOW}⚠ Issues: {issues} artifact(s) flagged as suspect{NC}")

    # Suggested next action
    suggestion = _suggest_action(root, phase, by_type)
    print(f"\n  → {suggestion}")
    print()

    return 0
