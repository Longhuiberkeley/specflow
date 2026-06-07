"""Devil's Advocate thinking technique — prompt generator."""

from __future__ import annotations

from specflow.lib.artifacts import Artifact
from specflow.lib.techniques import LENS_CATALOG, TechniquePrompt

_SYSTEM_PROMPT = LENS_CATALOG["devils_advocate"]


def build_prompt(artifact: Artifact, context: str) -> TechniquePrompt:
    """Build a devil's advocate prompt for the host agent to apply."""
    user_prompt = f"""
Artifact ID: {artifact.id}
Title: {artifact.title}
Body:
{artifact.body}

CHECKLIST CONTEXT (do not duplicate these findings):
{context}
"""
    return TechniquePrompt(
        technique="devils_advocate",
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        diversity_hint=(
            "Run as a separate subagent for maximum creative diversity. "
            "Devil's advocate benefits from an independent perspective that "
            "isn't influenced by findings from other techniques."
        ),
        artifact_id=artifact.id,
    )
