"""Wave computation algorithm for parallel story execution."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from specflow.lib.artifacts import Artifact


def build_dependency_graph(
    stories: list[Artifact],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Build forward and reverse dependency graphs from story links.

    Returns (depends_on, depended_by) where:
    - depends_on[A] = {B, C} means A depends on B and C
    - depended_by[A] = {D} means D depends on A

    Dependency rules:
    - derives_from link to another STORY -> hard dependency
    - Two stories sharing specified_by to the same DDD -> soft dependency (lower ID first)
    """
    story_ids = {s.id for s in stories}

    depends_on: dict[str, set[str]] = defaultdict(set)
    depended_by: dict[str, set[str]] = defaultdict(set)

    # Initialize all stories in the graph
    for s in stories:
        depends_on.setdefault(s.id, set())

    # Hard dependencies: derives_from links between stories
    for story in stories:
        for link in story.links:
            if link.role == "derives_from" and link.target in story_ids:
                depends_on[story.id].add(link.target)
                depended_by[link.target].add(story.id)

    # Soft dependencies: stories sharing the same DDD (specified_by)
    ddd_to_stories: dict[str, list[str]] = defaultdict(list)
    for story in stories:
        for link in story.links:
            if link.role == "specified_by":
                ddd_to_stories[link.target].append(story.id)

    for ddd_id, story_ids_for_ddd in ddd_to_stories.items():
        if len(story_ids_for_ddd) > 1:
            # Sort by ID so lower ID runs first
            sorted_ids = sorted(story_ids_for_ddd)
            for i in range(1, len(sorted_ids)):
                later = sorted_ids[i]
                earlier = sorted_ids[i - 1]
                depends_on[later].add(earlier)
                depended_by[earlier].add(later)

    return dict(depends_on), dict(depended_by)


def detect_cycles(depends_on: dict[str, set[str]]) -> list[str] | None:
    """Detect cycles in the dependency graph using DFS with coloring.

    Returns the cycle path if found, None otherwise.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {node: WHITE for node in depends_on}
    parent: dict[str, str | None] = {node: None for node in depends_on}

    def dfs(node: str) -> list[str] | None:
        color[node] = GRAY
        for dep in depends_on.get(node, set()):
            if dep not in color:
                continue
            if color[dep] == GRAY:
                # Found a cycle — reconstruct
                cycle = [dep, node]
                current = node
                while parent.get(current) and parent[current] != dep:
                    current = parent[current]  # type: ignore[assignment]
                    cycle.append(current)
                cycle.reverse()
                return cycle
            if color[dep] == WHITE:
                parent[dep] = node
                result = dfs(dep)
                if result:
                    return result
        color[node] = BLACK
        return None

    for node in depends_on:
        if color[node] == WHITE:
            result = dfs(node)
            if result:
                return result

    return None


def compute_waves(stories: list[Artifact]) -> dict[str, Any]:
    """Compute parallel execution waves from story dependencies.

    Uses Kahn's algorithm (topological sort) to group stories into waves
    where all stories in a wave can execute in parallel.

    Returns:
        {"ok": True, "waves": list[list[str]]} on success
        {"ok": False, "error": str, "cycle": list[str]} on cycle detection
    """
    if not stories:
        return {"ok": True, "waves": []}

    depends_on, depended_by = build_dependency_graph(stories)

    # Check for cycles
    cycle = detect_cycles(depends_on)
    if cycle:
        return {
            "ok": False,
            "error": f"Circular dependency detected: {' -> '.join(cycle)}",
            "cycle": cycle,
        }

    # Kahn's algorithm: compute in-degrees
    in_degree: dict[str, int] = {}
    for story in stories:
        in_degree[story.id] = len(depends_on.get(story.id, set()))

    waves: list[list[str]] = []
    remaining = set(in_degree.keys())

    while remaining:
        # Find all nodes with zero in-degree
        wave = sorted(sid for sid in remaining if in_degree[sid] == 0)

        if not wave:
            # Remaining nodes all have dependencies — cycle (shouldn't happen after check)
            return {
                "ok": False,
                "error": f"Unresolvable dependencies among: {sorted(remaining)}",
                "cycle": sorted(remaining),
            }

        waves.append(wave)

        # Remove wave nodes and decrement in-degrees
        for sid in wave:
            remaining.discard(sid)
            for dependent in depended_by.get(sid, set()):
                if dependent in in_degree:
                    in_degree[dependent] -= 1

    return {"ok": True, "waves": waves}


def filter_executable_stories(stories: list[Artifact]) -> list[Artifact]:
    """Filter to only stories with status: approved."""
    return [s for s in stories if s.status == "approved"]
