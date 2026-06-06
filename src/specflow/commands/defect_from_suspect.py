"""CLI handler for 'specflow defect-from-suspect'.

Materializes the suspect → DEF pipeline: when a human decides a suspect-flagged
artifact genuinely no longer satisfies its upstream requirement, this creates a
DEF with full traceability (`fails_to_meet` → REQ, `exposed_by` → suspect).
"""

from pathlib import Path
from typing import Any

from specflow.lib import defects as defects_lib
from specflow.lib.display import RED, GREEN, CYAN, NC


def run(root: Path, args: dict[str, Any]) -> int:
    suspect_id = args.get("suspect_id")
    req_id = args.get("req")

    if not suspect_id or not req_id:
        print(f"{RED}✗ both <SUSPECT_ID> and --req <REQ_ID> are required{NC}")
        return 1

    result = defects_lib.create_defect_from_suspect(
        root,
        suspect_artifact_id=suspect_id,
        upstream_req_id=req_id,
        impact_event_path=args.get("impact_event"),
        severity=args.get("severity", "medium"),
        title=args.get("title"),
    )

    if not result.get("ok"):
        print(f"{RED}✗ {result.get('error', 'Unknown error')}{NC}")
        return 1

    print(f"{GREEN}✓ Created {result['id']}{NC} — {result['path']}")
    print(
        f"  Links: {CYAN}fails_to_meet{NC} → {req_id}, "
        f"{CYAN}exposed_by{NC} → {suspect_id}"
    )
    print(f"  Next: resolve the suspect flag once addressed — "
          f"specflow change-impact --resolve {suspect_id}")
    return 0
