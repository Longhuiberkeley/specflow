"""specflow standards gaps — List uncovered standard clauses."""

from __future__ import annotations

from pathlib import Path

from specflow.lib import standards as std_lib

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
CYAN = "\033[0;36m"
NC = "\033[0m"


def run(root: Path, args: dict) -> int:
    """Execute specflow standards gaps."""
    root = root.resolve()

    standard_name = args.get("standard")

    result = std_lib.check_compliance(root, standard_name)
    if not result["ok"]:
        print(f"{RED}✗ {result.get('error', 'Failed to check compliance.')}{NC}")
        return 1

    standard = result.get("standard", "unknown")
    uncovered = result.get("uncovered", [])

    if not uncovered:
        print(f"{GREEN}✓ No uncovered clauses found in standard '{standard}'.{NC}")
        return 0

    stds = std_lib.load_standards(root, standard)
    clause_desc: dict[str, str] = {}
    for std in stds:
        for clause in std.get("clauses", []):
            if isinstance(clause, dict) and clause.get("id"):
                clause_desc[clause["id"]] = clause.get("description", "")

    print(f"{YELLOW}⚠ Found {len(uncovered)} uncovered clause(s) in standard '{standard}':{NC}\n")

    for clause in uncovered:
        clause_id = clause.get("clause_id", "")
        clause_title = clause.get("clause_title", "")
        desc = clause_desc.get(clause_id, "")
        line = f"  {CYAN}{clause_id}{NC}: {clause_title}"
        if desc:
            line += f"\n       {desc}"
        print(line)

    return 0
