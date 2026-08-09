"""specflow artifact-review — Compose lint + checklist into a single review entry point."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

from specflow.commands import artifact_lint, checklist_run
from specflow.lib import artifacts as art_lib
from specflow.lib import checklists
from specflow.lib import challenges as chl_lib
from specflow.lib import learning as learn_lib
from specflow.lib.analysis import find_dead_code, find_similar_functions
from specflow.lib.display import YELLOW_DIM, CYAN, NC, BOLD
from specflow.lib.techniques import generate_technique_prompts, TechniqueFinding, ARTIFACT_LEVEL_DEFAULT_LENSES


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


def _format_prompt(
    artifact: art_lib.Artifact,
    items: list[checklists.ChecklistItem],
    root: Path | None = None,
) -> str:
    lines: list[str] = []

    bp_items_present = any(item.source_checklist.startswith("best-practices/") for item in items)
    if root is not None and not bp_items_present:
        from specflow.lib import ci as ci_mod

        prefix = ci_mod.load_active_bp_context(root, artifact)
        if prefix:
            lines.append(prefix.rstrip())
            lines.append("")

    lines.extend([
        f"Artifact ID: {artifact.id}",
        f"Artifact type: {artifact.type}",
        f"Title: {artifact.title}",
        f"Tags: {', '.join(artifact.tags) if artifact.tags else '(none)'}",
        "---BODY---",
        artifact.body[:2000],
        "---END---",
        "",
        "Checks to judge:",
    ])
    for idx, item in enumerate(items, 1):
        lines.append(f"{idx}. [{item.id}] {item.check} (severity: {item.severity})")
        if item.llm_prompt:
            lines.append(f"   guidance: {item.llm_prompt}")
    return "\n".join(lines)


def _get_target_artifacts(root: Path, args: dict[str, Any]) -> list[art_lib.Artifact]:
    all_arts = art_lib.discover_artifacts(root)
    art_id = args.get("artifact_id")
    if art_id:
        targets = [a for a in all_arts if a.id == art_id]
    else:
        targets = all_arts
    return targets


def _create_chl_artifacts(
    root: Path,
    target_id: str,
    findings: list[TechniqueFinding],
    review_id: str | None = None,
) -> list[dict[str, str]]:
    """Create CHL artifacts for non-info findings.

    Returns a list of dicts: [{"id", "severity", "technique", "title"}, ...].
    Delegates to :func:`specflow.lib.challenges.create_chl_artifacts`.
    """
    return chl_lib.create_chl_artifacts(
        root,
        findings,
        target_id,
        link_role="challenges",
        review_id=review_id,
        dedup=False,
    )


def _bootstrap_review_schema(root: Path) -> None:
    """Ensure review.yaml is present in .specflow/schema/ for repos that
    pre-date the REVIEW artifact type."""
    schema_dir = root / ".specflow" / "schema"
    if not schema_dir.exists():
        return
    dst = schema_dir / "review.yaml"
    if dst.exists():
        return
    pkg_template = Path(__file__).parent.parent / "templates" / "schemas" / "review.yaml"
    if pkg_template.exists():
        shutil.copy(str(pkg_template), str(dst))
        review_dir = root / "_specflow" / "specs" / "reviews"
        review_dir.mkdir(parents=True, exist_ok=True)
        index = review_dir / "_index.yaml"
        if not index.exists():
            index.write_text("artifacts: {}\nnext_id: 1\n", encoding="utf-8")


def emit_review_pass(
    root: Path,
    target: art_lib.Artifact,
    findings: list[TechniqueFinding],
    depth: str,
) -> dict[str, object]:
    """Emit a single REVIEW artifact summarizing this review pass for one target.

    Creates the REVIEW first (so spawned CHLs can link back via refers_to),
    then creates CHLs, then updates the REVIEW with the finding summary.
    Returns {"ok": bool, "review_id": str, "chl_ids": [...], "error": str?}.

    REVIEW emission is skipped when there are no actionable findings — there
    is nothing to summarize that the existing artifact-review CLI output
    didn't already say.
    """
    actionable = [f for f in findings if f.severity != "info"]
    if not actionable:
        return {"ok": False, "review_id": "", "chl_ids": [], "error": "no actionable findings"}

    summary = f"Review of {target.id}"
    rationale = (
        f"{depth.capitalize()} review pass over {target.id} "
        f"({target.type}) yielded {len(actionable)} finding(s)."
    )

    review = art_lib.create_artifact(
        root,
        artifact_type="review",
        title=summary[:100],
        status="open",
        rationale=rationale,
        links=[{"target": target.id, "role": "review_of"}],
        body="",
        artifact_ref=target.id,
        depth=depth,
        reviewers=[],
        consensus="pending",
        findings=[],
    )
    if not review.get("ok"):
        return {"ok": False, "review_id": "", "chl_ids": [],
                "error": review.get("error", "review creation failed")}

    review_id = review["id"]
    chls = _create_chl_artifacts(root, target.id, actionable, review_id=review_id)

    finding_summary = [
        {"chl_ref": c["id"], "severity": c["severity"], "summary": c["title"]}
        for c in chls
    ]
    art_lib.update_artifact(root, review_id, findings=finding_summary)
    print(f"  Created {review_id} (review_of {target.id}, {len(chls)} CHL(s))")

    return {
        "ok": True,
        "review_id": review_id,
        "chl_ids": [c["id"] for c in chls],
    }


def _create_learned_patterns(
    root: Path, targets: list[art_lib.Artifact], findings: list[TechniqueFinding]
) -> int:
    count = 0
    art_map = {a.id: a for a in targets}
    learnable_techs = learn_lib.learnable_techniques(root)
    for f in findings:
        if f.severity not in learn_lib.LEARNABLE_SEVERITIES:
            continue
        if not f.technique or f.technique not in learnable_techs:
            continue
        if count >= learn_lib.max_patterns_per_session(root):
            break
        if not f.target_id or f.target_id not in art_map:
            continue
        try:
            path = learn_lib.create_pattern_from_finding(
                root,
                art_map[f.target_id],
                check_text=f.title,
                reason=f.rationale,
                severity=f.severity,
            )
            if path:
                count += 1
                print(f"  Created prevention pattern {path.name} from {f.technique}")
        except Exception as e:
            print(f"  {YELLOW_DIM}⚠ Failed to create pattern: {e}{NC}")
    return count


def _prompt_for_techniques(target_arts: list[art_lib.Artifact]) -> list[str]:
    from specflow.lib.techniques import (
        ARTIFACT_LEVEL_DEFAULT_LENSES,
        LENS_CATEGORIES,
    )

    research_types = set(ARTIFACT_LEVEL_DEFAULT_LENSES.keys())
    types_present = {a.type for a in target_arts}
    research_types_present = types_present & research_types
    has_software = bool(types_present - research_types_present)
    has_research = bool(research_types_present)

    # Mixed review: fall back to "both" category lenses to avoid domain mismatch
    if has_research and has_software:
        techniques = [
            name for name, cat in LENS_CATEGORIES.items()
            if cat == "both"
        ]
        label = "Mixed review — both-domain lenses only"
    elif has_research and len(types_present) == 1:
        art_type = target_arts[0].type
        techniques = list(ARTIFACT_LEVEL_DEFAULT_LENSES.get(art_type, []))
        label = f"Research defaults for {art_type}"
    else:
        techniques = ["devils_advocate", "premortem", "assumption_surfacing", "red_blue_team"]
        label = "Software defaults"

    est_tokens = len(target_arts) * 3000 * len(techniques)
    print(f"\n{BOLD}Deep Review Subagents{NC}")
    print(f"Target artifacts: {len(target_arts)}")
    print(f"Techniques ({label}): {', '.join(techniques)}")
    print(f"Estimated token spend: ~{est_tokens} tokens")

    if not sys.stdout.isatty():
        return techniques

    ans = input("Run these subagents? [Y/n]: ").strip().lower()
    if ans in ("n", "no"):
        return []
    return techniques


def _record_techniques_on_artifacts(
    root: Path,
    targets: list[art_lib.Artifact],
    techniques: list[str],
) -> None:
    for art in targets:
        existing = art.thinking_techniques
        merged = list(dict.fromkeys(existing + techniques))
        if merged != existing:
            art_lib.update_artifact(
                root,
                art.id,
                thinking_techniques=merged,
            )


def run(root: Path, args: dict[str, Any]) -> int:
    _bootstrap_challenge_schema(root)
    _bootstrap_review_schema(root)
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
        
    # 3. Target collection
    targets = _get_target_artifacts(root, args)
    if not targets:
        return 2 if (lint_rc == 1 or check_rc == 1) else 0

    print(f"\n{CYAN}SpecFlow Artifact Review — Depth: {depth}{NC}")

    findings: list[TechniqueFinding] = []

    # 4. Normal depth: emit agent-judged checklist items as a self-contained prompt.
    #    SpecFlow makes no external API calls — the host agent (Claude, Codex,
    #    OpenCode, …) reads this prompt and produces the judgement itself.
    for art in targets:
        assembled = checklists.assemble_checklist(root, art)
        agent_items = [i for i in assembled.items if not i.automated]
        if agent_items:
            prompt = _format_prompt(art, agent_items, root=root)
            print(f"\n  {BOLD}Agent-judged checks for {art.id} ({len(agent_items)} items){NC} — host agent evaluates the prompt below:")
            print(prompt)

    # 5. Deep depth: thinking techniques as full prompts for the host agent.
    if depth == "deep":
        techs_str = args.get("techniques")
        if techs_str:
            techniques = [t.strip() for t in techs_str.split(",") if t.strip()]
        else:
            techniques = _prompt_for_techniques(targets)

        if techniques:
            print(f"\n  Generating {len(techniques)} technique prompt(s) for the host agent...")
            for art in targets:
                assembled = checklists.assemble_checklist(root, art)
                ctx = "\n".join([f"- {i.check}" for i in assembled.items])
                prompts = generate_technique_prompts(techniques, [art], ctx)
                for p in prompts:
                    print(f"\n  ┌─ {p.technique} → {p.artifact_id}")
                    print(f"  │ {p.diversity_hint}")
                    print(f"  ├─ SYSTEM:")
                    print(p.system_prompt)
                    print(f"  ├─ USER:")
                    print(p.user_prompt)
                    print(f"  └─ (host agent applies this technique with its own intelligence — no external API call)")

            _record_techniques_on_artifacts(root, targets, techniques)
                
    # 6. Hygiene findings (these do not have target_id naturally, but we can assign to root or skip CHL)
    findings.extend(hygiene_findings)
    
    # 7. Create REVIEW + CHL artifacts (one REVIEW per target, CHLs linked back)
    created = 0
    if any(f.severity != "info" for f in findings):
        print("\nCreating REVIEW + CHL artifacts for findings...")
        for art in targets:
            art_findings = [f for f in findings if f.target_id == art.id]
            if not any(f.severity != "info" for f in art_findings):
                continue
            outcome = emit_review_pass(root, art, art_findings, depth)
            if outcome.get("ok"):
                created += len(outcome.get("chl_ids", []))

        # For findings without a target_id (hygiene), we just skip CHL creation for now
        # since their severity is 'info'.

    # 8. Create learned patterns from significant findings
    learnable = [f for f in findings if f.severity in learn_lib.LEARNABLE_SEVERITIES]
    if learnable:
        print("\nCreating prevention patterns from findings...")
        _create_learned_patterns(root, targets, findings)
        
    if created > 0 or lint_rc == 1 or check_rc == 1:
        return 2
        
    return 0
