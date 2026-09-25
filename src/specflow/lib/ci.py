"""CI support: artifact context loading for deterministic review.

SpecFlow is self-contained — all audit, health-check, and review logic is
fully deterministic with zero external API calls. The host agent (Claude,
Codex, OpenCode, etc.) provides the intelligence; SpecFlow provides the
artifact graph, checklists, and structure.

This module loads local best-practice artifacts as review context so that
programmatic checks and agent-driven skills have domain-specific guidance
available.
"""

from __future__ import annotations

from pathlib import Path

from specflow.lib import artifacts as art_lib


def load_active_best_practices(
    root: Path,
    artifact: art_lib.Artifact,
) -> list[art_lib.Artifact]:
    """Return approved BPs matched applicability-first, then by legacy tags."""
    from specflow.lib.practices import load_active_best_practices as load

    return load(root, artifact)


def load_active_bp_context(root: Path, artifact: art_lib.Artifact) -> str:
    """Format matching best-practice artifacts as review-prompt context."""
    relevant_bps = [
        f"[{bp.id}] {bp.title}:\n{bp.body[:500]}"
        for bp in load_active_best_practices(root, artifact)
    ]
    if not relevant_bps:
        return ""
    return "Applicable best practices:\n" + "\n---\n".join(relevant_bps)
