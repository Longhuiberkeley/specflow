"""Devil's Advocate thinking technique."""

from __future__ import annotations

from specflow.lib.artifacts import Artifact
from specflow.lib.ci import LLMConfig, call_llm
from specflow.lib.techniques import LENS_CATALOG, parse_json_response

_SYSTEM_PROMPT = LENS_CATALOG["devils_advocate"]

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
