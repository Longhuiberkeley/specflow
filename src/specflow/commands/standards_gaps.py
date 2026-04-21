"""specflow standards gaps — List uncovered standard clauses."""

from __future__ import annotations

import json
from pathlib import Path

from specflow.lib import standards as std_lib
from specflow.lib.display import RED, GREEN, YELLOW_DIM, CYAN, NC, BOLD, DIM

_SEVERITY_LABEL = {"high": "HIGH", "medium": "MED ", "low": "LOW "}


def run(root: Path, args: dict) -> int:
    """Execute specflow standards gaps."""
    root = root.resolve()

    standard_name = args.get("standard")
    use_json = args.get("json", False)

    result = std_lib.check_compliance(root, standard_name)
    if not result["ok"]:
        print(f"{RED}✗ {result.get('error', 'Failed to check compliance.')}{NC}")
        return 1

    if use_json:
        return _print_json(result)

    return _print_dashboard(result, root, standard_name)


def _print_json(result: dict) -> int:
    uncovered = result.get("uncovered", [])
    covered = result.get("covered", [])
    score = result.get("score", 0.0)

    output = {
        "standard": result.get("standard", ""),
        "title": result.get("title", ""),
        "version": result.get("version", ""),
        "total_clauses": result.get("total_clauses", 0),
        "covered": len(covered),
        "uncovered": len(uncovered),
        "score": score,
        "gaps": [
            {
                "id": g.get("clause_id", ""),
                "title": g.get("clause_title", ""),
                "severity": g.get("severity", "medium"),
                "category": g.get("category", "functional"),
                "remediation": g.get("remediation", ""),
            }
            for g in uncovered
        ],
    }

    print(json.dumps(output, indent=2))
    return 0


def _print_dashboard(result: dict, root: Path, standard_name: str | None) -> int:
    standard = result.get("standard", "unknown")
    uncovered = result.get("uncovered", [])
    covered = result.get("covered", [])
    score = result.get("score", 0.0)
    total = result.get("total_clauses", 0)

    if not uncovered:
        print(f"{GREEN}✓ No uncovered clauses found in standard '{standard}'.{NC}")
        print(f"  Coverage: {score}% ({len(covered)}/{total} clauses)")
        return 0

    print(f"\n{BOLD}Standard: {result.get('title', standard)}{NC}")
    print(f"  Total: {total} clauses | Covered: {len(covered)} ({score}%) | Uncovered: {len(uncovered)}")
    print()

    print(f"  {YELLOW_DIM}Uncovered (sorted by severity):{NC}")
    for clause in uncovered:
        clause_id = clause.get("clause_id", "")
        clause_title = clause.get("clause_title", "")
        severity = clause.get("severity", "medium")
        remediation = clause.get("remediation", "")

        sev_label = _SEVERITY_LABEL.get(severity, "MED ")
        print(f"    [{CYAN}{sev_label}{NC}]  {clause_id} — {clause_title}")
        if remediation:
            print(f"           {DIM}→ {remediation}{NC}")

    print()
    return 0
