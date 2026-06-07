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


def load_active_bp_context(root: Path, artifact: art_lib.Artifact) -> str:
    """Load active best-practice artifacts as review context.

    Reads BP artifacts from _specflow/specs/best-practices/ and formats
    them as a context prefix for review prompts. Filters to active BPs
    whose tags overlap with the artifact's tags or whose applies_to links
    reference the artifact.
    """
    bp_dir = root / "_specflow" / "specs" / "best-practices"
    if not bp_dir.exists():
        return ""
    artifact_tags = set(artifact.tags)
    artifact_id = artifact.id
    relevant_bps: list[str] = []
    for bp_file in sorted(bp_dir.glob("*.md")):
        bp = art_lib.parse_artifact(bp_file)
        if not bp or bp.status not in ("active", "approved"):
            continue
        # Match by applies_to link or tag overlap
        applies_to_ids = {lnk.target for lnk in bp.links if lnk.role == "applies_to"}
        if artifact_id in applies_to_ids:
            relevant_bps.append(f"[{bp.id}] {bp.title}:\n{bp.body[:500]}")
            continue
        if artifact_tags & set(bp.tags):
            relevant_bps.append(f"[{bp.id}] {bp.title}:\n{bp.body[:500]}")
    if not relevant_bps:
        return ""
    return "Applicable best practices:\n" + "\n---\n".join(relevant_bps)
