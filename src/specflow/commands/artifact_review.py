"""specflow artifact-review — Compose lint + checklist into a single review entry point."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

from specflow.commands import artifact_lint, checklist_run
from specflow.lib import artifacts as art_lib
from specflow.lib import checklists
from specflow.lib import ci
from specflow.lib.analysis import find_dead_code, find_similar_functions
from specflow.lib.display import YELLOW_DIM, CYAN, NC
from specflow.lib.techniques import run_subagents, TechniqueFinding

BOLD = "\033[1m"


def _bootstrap_challenge_schema(root: Path) -> None:
    schema_dir = root / ".specflow" / "schema"
    if not schema_dir.exists():
        return
    dst = schema_dir / "challenge.yaml"
    if not dst.exists():
        src = root / "src" / "specflow" / "templates" / "schemas" / "challenge.yaml"
        if src.exists():
            shutil.copy(str(src), str(dst))


def _run_hygiene_silently(root: Path) -> list[TechniqueFinding]:
    findings = []
    # Dead code
    symbols = find_dead_code(root, src_dir="src")
    if symbols:
        findings.append(TechniqueFinding(
            title=f"Dead Code Detected ({len(symbols)} symbols)",
            rationale=f"Found {len(symbols)} unreferenced top-level symbols. Informational only.",
            severity="info",
            technique="detect:dead-code"
        ))
        
    # Similarity
    pairs = find_similar_functions(root, src_dir="src", min_statements=10, threshold=0.9)
    if pairs:
        findings.append(TechniqueFinding(
            title=f"Code Similarity Detected ({len(pairs)} pairs)",
            rationale=f"Found {len(pairs)} near-duplicate functions. Informational only.",
            severity="info",
            technique="detect:similarity"
        ))
    return findings


def _format_prompt(artifact: art_lib.Artifact, items: list[checklists.ChecklistItem]) -> str:
    lines = [
        f"Artifact ID: {artifact.id}",
        f"Artifact type: {artifact.type}",
        f"Title: {artifact.title}",
        f"Tags: {', '.join(artifact.tags) if artifact.tags else '(none)'}",
        "---BODY---",
        artifact.body[:2000],
        "---END---",
        "",
        "Checks to judge:",
    ]
    for idx, item in enumerate(items, 1):
        lines.append(f"{idx}. [{item.id}] {item.check} (severity: {item.severity})")
        if item.llm_prompt:
            lines.append(f"   guidance: {item.llm_prompt}")
    return "\n".join(lines)


def _run_llm_checklist(
    root: Path, target_artifacts: list[art_lib.Artifact], cfg: ci.LLMConfig
) -> list[TechniqueFinding]:
    findings = []
    for art in target_artifacts:
        assembled = checklists.assemble_checklist(root, art)
        llm_items = [i for i in assembled.items if not i.automated]
        if not llm_items:
            continue
        
        prompt = _format_prompt(art, llm_items)
        result = ci.call_llm(cfg, ci.SYSTEM_PROMPT, prompt)
        if not result.get("ok"):
            print(f"  {YELLOW_DIM}⚠ LLM call failed for {art.id}: {result.get('error')}{NC}")
            continue
            
        dict_items = [{"id": i.id, "check": i.check, "severity": i.severity, "llm_prompt": i.llm_prompt} for i in llm_items]
        parsed = ci.parse_batch_response(result.get("content", ""), dict_items)
        for p, item in zip(parsed, llm_items):
            if p.get("verdict") == "FAIL":
                findings.append(TechniqueFinding(
                    title=item.check,
                    rationale=p.get("reason", "Failed checklist item"),
                    severity=item.severity,
                    technique="checklist-run",
                    target_id=art.id,
                ))
    return findings


def _get_target_artifacts(root: Path, args: dict[str, Any]) -> list[art_lib.Artifact]:
    all_arts = art_lib.discover_artifacts(root)
    art_id = args.get("artifact_id")
    if art_id:
        targets = [a for a in all_arts if a.id == art_id]
    else:
        targets = all_arts
    return targets


def _create_chl_artifacts(root: Path, target_id: str, findings: list[TechniqueFinding]) -> int:
    count = 0
    for f in findings:
        if f.severity == "info":
            continue  # We only create CHL for warn/error
            
        try:
            art = art_lib.create_artifact(
                root,
                artifact_type="challenge",
                title=f.title[:100],
                status="open",
                rationale=f.rationale,
                links=[{"target": target_id, "role": "challenges"}],
                body=""
            )
            if not art.get("ok"):
                print(f"  {YELLOW_DIM}⚠ Failed to create CHL: {art.get('error', 'Unknown error')}{NC}")
                continue

            art_lib.update_artifact(
                root,
                art["id"],
                severity=f.severity,
                technique=f.technique
            )
            count += 1
            print(f"  Created {art['id']} [{f.severity}] from {f.technique}")
        except Exception as e:
            print(f"  {YELLOW_DIM}⚠ Failed to create CHL: {e}{NC}")
    return count


def _prompt_for_techniques(target_arts: list[art_lib.Artifact]) -> list[str]:
    techniques = ["devils_advocate", "premortem", "assumption_surfacing", "red_blue_team"]
    est_tokens = len(target_arts) * 3000 * len(techniques)
    print(f"\n{BOLD}Deep Review Subagents{NC}")
    print(f"Target artifacts: {len(target_arts)}")
    print(f"Available techniques: {', '.join(techniques)}")
    print(f"Estimated token spend: ~{est_tokens} tokens")
    
    if not sys.stdout.isatty():
        return techniques
        
    ans = input("Run all 4 subagents? [Y/n]: ").strip().lower()
    if ans in ("n", "no"):
        return []
    return techniques


def run(root: Path, args: dict[str, Any]) -> int:
    _bootstrap_challenge_schema(root)
    depth = args.get("depth") or "quick"

    # 1. Silent detect pre-step
    hygiene_findings = _run_hygiene_silently(root)
    
    # 2. Deterministic lint + checklist
    lint_rc = artifact_lint.run(root, {})
    
    check_args = {
        "artifact_id": args.get("artifact_id"),
        "all": args.get("all", False),
        "gate": args.get("gate"),
        "proactive": args.get("proactive", False),
        "dedup": False,
    }
    if not check_args["artifact_id"] and not check_args["all"]:
        check_args["all"] = True

    check_rc = checklist_run.run(root, check_args)
    if lint_rc not in (0, 1) or check_rc not in (0, 1):
        return 3
        
    if depth == "quick":
        return 2 if (lint_rc == 1 or check_rc == 1) else 0
        
    # 3. Target collection & Config
    targets = _get_target_artifacts(root, args)
    if not targets:
        return 2 if (lint_rc == 1 or check_rc == 1) else 0
        
    cfg = ci.load_llm_config(root)
    if not cfg.api_key:
        print(f"{YELLOW_DIM}⚠ Cannot run LLM depth: missing {ci.DEFAULT_KEY_ENV} in environment.{NC}")
        return 2 if (lint_rc == 1 or check_rc == 1) else 0

    print(f"\n{CYAN}SpecFlow Artifact Review — Depth: {depth}{NC}")
    
    # 4. Normal depth: LLM checklist
    print("Running LLM checklist judgment...")
    findings = _run_llm_checklist(root, targets, cfg)
    
    # 5. Deep depth: Techniques
    if depth == "deep":
        techs_str = args.get("techniques")
        if techs_str:
            techniques = [t.strip() for t in techs_str.split(",") if t.strip()]
        else:
            techniques = _prompt_for_techniques(targets)
            
        if techniques:
            print(f"Fanning out {len(techniques)} subagent(s)...")
            for art in targets:
                # get deduplication context
                assembled = checklists.assemble_checklist(root, art)
                ctx = "\n".join([f"- {i.check}" for i in assembled.items])
                tech_findings = run_subagents(techniques, [art], ctx, cfg)
                findings.extend(tech_findings)
                
    # 6. Hygiene findings (these do not have target_id naturally, but we can assign to root or skip CHL)
    findings.extend(hygiene_findings)
    
    # 7. Create CHL artifacts
    created = 0
    if any(f.severity != "info" for f in findings):
        print("\nCreating CHL artifacts for findings...")
        for art in targets:
            art_findings = [f for f in findings if f.target_id == art.id]
            created += _create_chl_artifacts(root, art.id, art_findings)
            
        # For findings without a target_id (hygiene), we just skip CHL creation for now
        # since their severity is 'info'.
        
    if created > 0 or lint_rc == 1 or check_rc == 1:
        return 2
        
    return 0
