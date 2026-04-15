"""Assumption Surfacing thinking technique."""

from __future__ import annotations

from typing import Any

from specflow.lib.artifacts import Artifact
from specflow.lib.ci import LLMConfig, call_llm
from specflow.lib.techniques import parse_json_response

_SYSTEM_PROMPT = (
    "You are an Assumption Surfacing reviewer for a SpecFlow spec-driven-development repository. "
    "Enumerate implicit assumptions the artifact rests on. For each, attack it: what if it is false? "
    "What if it changes mid-project? Highlight unstated requirements or hidden dependencies. "
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
