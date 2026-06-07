"""Assumption Surfacing thinking technique — prompt generator."""

from __future__ import annotations

from specflow.lib.artifacts import Artifact
from specflow.lib.techniques import LENS_CATALOG, TechniquePrompt

_SYSTEM_PROMPT = LENS_CATALOG["assumption_surfacing"]


def build_prompt(artifact: Artifact, context: str) -> TechniquePrompt:
    """Build an assumption surfacing prompt for the host agent to apply."""
    user_prompt = f"""
Artifact ID: {artifact.id}
Title: {artifact.title}
Body:
{artifact.body}

CHECKLIST CONTEXT (do not duplicate these findings):
{context}
"""
    return TechniquePrompt(
        technique="assumption_surfacing",
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        diversity_hint=(
            "Run as a separate subagent for maximum creative diversity. "
            "Assumption surfacing benefits from a fresh perspective that "
            "isn't anchored by other techniques' findings."
        ),
        artifact_id=artifact.id,
    )
