"""Red Team / Blue Team thinking technique."""

from __future__ import annotations

from typing import Any

from specflow.lib.artifacts import Artifact
from specflow.lib.ci import LLMConfig, call_llm
from specflow.lib.techniques import parse_json_response

_SYSTEM_PROMPT = (
    "You are conducting a Red Team / Blue Team exercise for a SpecFlow spec-driven-development repository. "
    "Act as both the attacker (Red Team) finding exploits and the defender (Blue Team) evaluating defenses. "
    "Focus on security-adjacent requirements and trust boundaries. "
    "Do NOT duplicate findings already covered in the provided CHECKLIST CONTEXT. "
    "Output a JSON array: "
    '[{"title": "<short finding title>", "rationale": "<explanation>", "severity": "warn|error"}]. '
    "No prose outside JSON."
)

def run(artifact: Artifact, context: str, cfg: LLMConfig) -> list[dict[str, str]]:
    user_prompt = f"""
Artifact ID: {artifact.id}
Title: {artifact.title}
Body:
{artifact.body}

CHECKLIST CONTEXT (do not duplicate these findings):
{context}
"""
    result = call_llm(cfg, _SYSTEM_PROMPT, user_prompt)
    if not result.get("ok"):
        raise Exception(result.get("error", "Unknown LLM error"))
        
    return parse_json_response(result.get("content", ""))
