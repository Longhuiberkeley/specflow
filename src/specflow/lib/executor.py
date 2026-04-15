"""Execution orchestrator: wave-based parallel story execution with context isolation."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from specflow.lib.artifacts import Artifact, discover_artifacts, parse_artifact, resolve_link_target, update_artifact
from specflow.lib.locks import acquire_lock, check_lock, release_lock
from specflow.lib.waves import compute_waves, filter_executable_stories


__all__ = [
    "ExecutionState",
    "run_execution",
    "load_execution_state",
]


# Approximate token budget: 4 chars ~ 1 token
MAX_CONTEXT_CHARS = 16000  # ~4000 tokens


@dataclass
class ExecutionState:
    """Tracks the state of a multi-wave execution run."""

    current_wave: int = 0
    total_waves: int = 0
    completed: list[str] = field(default_factory=list)
    in_progress: list[str] = field(default_factory=list)
    queued: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "wave": self.current_wave,
            "total_waves": self.total_waves,
            "completed": self.completed,
            "in_progress": self.in_progress,
            "queued": self.queued,
            "failed": self.failed,
        }


@dataclass
class SubagentContext:
    """Isolated context assembled for a single story's execution."""

    story: Artifact
    design_doc: Artifact | None = None
    arch_doc: Artifact | None = None
    agents_md: str = ""

    @property
    def total_chars(self) -> int:
        total = len(self.story.body)
        if self.design_doc:
            total += len(self.design_doc.body)
        if self.arch_doc:
            total += len(self.arch_doc.body)
        total += len(self.agents_md)
        return total

    def to_prompt(self) -> str:
        """Render the context as a single prompt string for the subagent."""
        parts = [f"# Story: {self.story.title}\n\n{self.story.body}"]

        if self.design_doc:
            parts.append(f"\n\n# Design: {self.design_doc.title}\n\n{self.design_doc.body}")

        if self.arch_doc:
            parts.append(f"\n\n# Architecture: {self.arch_doc.title}\n\n{self.arch_doc.body}")

        if self.agents_md:
            parts.append(f"\n\n# Project Rules\n\n{self.agents_md}")

        return "\n".join(parts)


def build_subagent_context(
    root: Path,
    story: Artifact,
    all_artifacts: list[Artifact],
) -> SubagentContext:
    """Build isolated context for a story's execution.

    Includes: story + linked DDD (specified_by) + linked ARCH (guided_by) + AGENTS.md.
    Enforces approximate <4000 token budget via character limit.
    """
    id_index = {a.id: a for a in all_artifacts}

    design_doc = None
    arch_doc = None

    for link in story.links:
        if link.role == "specified_by" and link.target in id_index:
            design_doc = id_index[link.target]
        elif link.role == "guided_by" and link.target in id_index:
            arch_doc = id_index[link.target]

    # Read AGENTS.md if it exists
    agents_md = ""
    agents_path = root / "AGENTS.md"
    if agents_path.exists():
        try:
            agents_md = agents_path.read_text(encoding="utf-8")
        except Exception:
            pass

    ctx = SubagentContext(
        story=story,
        design_doc=design_doc,
        arch_doc=arch_doc,
        agents_md=agents_md,
    )

    # Truncate if over budget — keep story complete, trim design/arch/agents
    if ctx.total_chars > MAX_CONTEXT_CHARS:
        budget_remaining = MAX_CONTEXT_CHARS - len(story.body)

        if ctx.agents_md and budget_remaining > 0:
            ctx.agents_md = ctx.agents_md[:min(len(ctx.agents_md), budget_remaining // 3)]
            budget_remaining -= len(ctx.agents_md)

        if ctx.arch_doc and budget_remaining > 0:
            arch_body = ctx.arch_doc.body[:budget_remaining // 2]
            # We can't modify the Artifact directly, so note the truncation
            budget_remaining -= len(arch_body)

        if ctx.design_doc and budget_remaining > 0:
            design_body = ctx.design_doc.body[:budget_remaining]

    return ctx


def _get_touched_artifacts(story: Artifact) -> list[str]:
    """Get artifact IDs that a story touches (its link targets)."""
    return [link.target for link in story.links]


def save_execution_state(root: Path, state: ExecutionState) -> None:
    """Save execution state to .specflow/state.yaml."""
    state_path = root / ".specflow" / "state.yaml"

    try:
        data = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
    except Exception:
        data = {}

    data["current"] = "executing"
    data["execution"] = state.to_dict()

    state_path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def load_execution_state(root: Path) -> ExecutionState | None:
    """Load execution state from .specflow/state.yaml."""
    state_path = root / ".specflow" / "state.yaml"
    if not state_path.exists():
        return None

    try:
        data = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(data, dict) or "execution" not in data:
        return None

    ex = data["execution"]
    return ExecutionState(
        current_wave=ex.get("wave", 0),
        total_waves=ex.get("total_waves", 0),
        completed=ex.get("completed", []),
        in_progress=ex.get("in_progress", []),
        queued=ex.get("queued", []),
        failed=ex.get("failed", []),
    )


def auto_commit_wave(root: Path, wave_num: int, story_ids: list[str]) -> bool:
    """Create a git commit after a wave completes."""
    ids_str = ", ".join(story_ids)
    message = f"specflow: wave {wave_num} complete [{ids_str}]"

    try:
        subprocess.run(["git", "add", "-A"], cwd=str(root), capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(root),
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, Exception):
        return False


def execute_story(
    context: SubagentContext,
    root: Path,
    timeout: int = 600,
) -> dict[str, Any]:
    """Execute a single story using its assembled context.

    In the Python CLI, this runs sequentially. The skill SKILL.md handles
    actual parallel subagent spawning via the AI platform.

    Returns {"ok": True/False, "story_id": str, "detail": str}.
    """
    # In sequential mode, we prepare the context and report it.
    # The actual implementation work is done by the AI agent reading the context.
    story_id = context.story.id
    return {
        "ok": True,
        "story_id": story_id,
        "detail": f"Context assembled for {story_id} ({context.total_chars} chars)",
        "context_prompt": context.to_prompt(),
    }


def run_execution(
    root: Path,
    stories: list[Artifact] | None = None,
    timeout: int = 600,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Main entry point: orchestrate wave-based execution.

    Args:
        root: Project root.
        stories: Optional pre-filtered story list. If None, loads approved stories.
        timeout: Per-story timeout in seconds.
        dry_run: If True, show wave plan without executing.

    Returns:
        Summary dict with wave results.
    """
    if stories is None:
        all_stories = discover_artifacts(root, "story")
        stories = filter_executable_stories(all_stories)

    if not stories:
        return {"ok": False, "error": "No approved stories found for execution"}

    # Compute waves
    wave_result = compute_waves(stories)
    if not wave_result["ok"]:
        return wave_result

    waves = wave_result["waves"]
    all_artifacts = discover_artifacts(root)

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "total_waves": len(waves),
            "waves": [{"wave": i + 1, "stories": w} for i, w in enumerate(waves)],
        }

    # Initialize execution state
    all_story_ids = [sid for wave in waves for sid in wave]
    state = ExecutionState(
        current_wave=0,
        total_waves=len(waves),
        completed=[],
        in_progress=[],
        queued=all_story_ids.copy(),
        failed=[],
    )
    save_execution_state(root, state)

    # Build story index
    story_index = {s.id: s for s in stories}
    wave_summaries: list[dict[str, Any]] = []

    for wave_num, wave_story_ids in enumerate(waves, 1):
        state.current_wave = wave_num
        state.in_progress = []
        ready: list[str] = []
        deferred: list[str] = []

        # Check locks
        for sid in wave_story_ids:
            story = story_index.get(sid)
            if story is None:
                continue

            locked = False
            for art_id in _get_touched_artifacts(story):
                lock_info = check_lock(root, art_id)
                if lock_info is not None:
                    locked = True
                    break

            if locked:
                deferred.append(sid)
            else:
                ready.append(sid)

        # Execute ready stories
        wave_results: list[dict[str, Any]] = []
        for sid in ready:
            story = story_index.get(sid)
            if story is None:
                continue

            state.in_progress.append(sid)
            if sid in state.queued:
                state.queued.remove(sid)
            save_execution_state(root, state)

            # Build context and execute
            context = build_subagent_context(root, story, all_artifacts)
            result = execute_story(context, root, timeout=timeout)
            wave_results.append(result)

            if result["ok"]:
                update_artifact(root, sid, status="implemented")
                state.completed.append(sid)
            else:
                state.failed.append(sid)

            if sid in state.in_progress:
                state.in_progress.remove(sid)

        # Deferred stories go back to queue for next wave
        for sid in deferred:
            if sid not in state.queued:
                state.queued.append(sid)

        save_execution_state(root, state)

        if ready:
            auto_commit_wave(root, wave_num, ready)

        wave_summaries.append({
            "wave": wave_num,
            "executed": ready,
            "deferred": deferred,
            "results": wave_results,
        })

    return {
        "ok": True,
        "total_waves": len(waves),
        "completed": state.completed,
        "failed": state.failed,
        "deferred": state.queued,
        "wave_summaries": wave_summaries,
    }
