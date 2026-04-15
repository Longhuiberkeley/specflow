"""Thinking technique subagent framework."""

from __future__ import annotations

import concurrent.futures
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from specflow.lib.artifacts import Artifact
from specflow.lib.ci import LLMConfig, call_llm


@dataclass
class TechniqueFinding:
    title: str
    rationale: str
    severity: str  # info | warn | error
    technique: str
    target_id: str | None = None


def parse_json_response(text: str) -> list[dict[str, str]]:
    """Parse a JSON array response from the model."""
    stripped = text.strip()
    fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", stripped, re.DOTALL)
    if fence:
        stripped = fence.group(1)
    else:
        start = stripped.find("[")
        end = stripped.rfind("]")
        if start != -1 and end != -1 and end > start:
            stripped = stripped[start : end + 1]

    try:
        parsed = json.loads(stripped)
    except Exception:
        parsed = []
        
    findings = []
    if isinstance(parsed, list):
        for entry in parsed:
            if not isinstance(entry, dict):
                continue
            findings.append({
                "title": str(entry.get("title", "")).strip(),
                "rationale": str(entry.get("rationale", "")).strip(),
                "severity": str(entry.get("severity", "")).strip().lower(),
            })
    return findings


def execute_technique(
    technique_name: str,
    artifact: Artifact,
    context: str,
    cfg: LLMConfig,
) -> list[TechniqueFinding]:
    """Execute a single thinking technique against an artifact."""
    import importlib
    
    try:
        mod = importlib.import_module(f"specflow.lib.techniques.{technique_name}")
    except ImportError:
        return [TechniqueFinding(
            title=f"Failed to load technique {technique_name}",
            rationale="Module not found.",
            severity="error",
            technique="framework"
        )]
        
    try:
        results = mod.run(artifact, context, cfg)
        findings = []
        for r in results:
            findings.append(TechniqueFinding(
                title=r.get("title", "Untitled finding"),
                rationale=r.get("rationale", ""),
                severity=r.get("severity", "info"),
                technique=technique_name,
                target_id=artifact.id,
            ))
        return findings
    except Exception as e:
        return [TechniqueFinding(
            title=f"Error executing {technique_name}",
            rationale=str(e),
            severity="error",
            technique="framework",
            target_id=artifact.id,
        )]


def run_subagents(
    techniques: list[str],
    artifacts: list[Artifact],
    context: str,
    cfg: LLMConfig,
) -> list[TechniqueFinding]:
    """Run all specified techniques against all target artifacts in parallel."""
    all_findings = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(techniques) * len(artifacts)) as executor:
        futures = []
        for tech in techniques:
            for art in artifacts:
                futures.append(executor.submit(execute_technique, tech, art, context, cfg))
        
        for future in concurrent.futures.as_completed(futures):
            all_findings.extend(future.result())
            
    return all_findings
