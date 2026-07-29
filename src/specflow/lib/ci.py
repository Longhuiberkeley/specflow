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
    """Return active/approved BPs matching by tag or ``applies_to`` link."""
    bp_dir = root / "_specflow" / "specs" / "best-practices"
    if not bp_dir.exists():
        return []

    artifact_tags = set(artifact.tags)
    relevant_bps: list[art_lib.Artifact] = []
    for bp_file in sorted(bp_dir.glob("*.md")):
        bp = art_lib.parse_artifact(bp_file)
        if not bp or bp.status not in ("active", "approved"):
            continue
        applies_to_ids = {link.target for link in bp.links if link.role == "applies_to"}
        if artifact.id in applies_to_ids or artifact_tags & set(bp.tags):
            relevant_bps.append(bp)
    return relevant_bps


def load_active_bp_context(root: Path, artifact: art_lib.Artifact) -> str:
    """Format matching best-practice artifacts as review-prompt context."""
    relevant_bps = [
        f"[{bp.id}] {bp.title}:\n{bp.body[:500]}"
        for bp in load_active_best_practices(root, artifact)
    ]
    if not relevant_bps:
        return ""
    return "Applicable best practices:\n" + "\n---\n".join(relevant_bps)
