"""CLI handler for 'specflow defect-from-monitor'.

Materializes the ops outcome → DEF pipeline: when a human decides a breached
MONITOR (ops pack) genuinely indicates a requirement is no longer satisfied,
this freezes the MONITOR's ephemeral evidence into a DEF with full
traceability (`fails_to_meet` → REQ, `exposed_by` → MON). The DEF then flows
through the existing on_closure → PREV path on close.

Accounting, not policing: if the source MONITOR was healthy at capture the
command warns and still creates the DEF, and it never mutates the MONITOR.
"""

from pathlib import Path
from typing import Any

from specflow.lib import defects as defects_lib
from specflow.lib.display import RED, GREEN, YELLOW, CYAN, NC


def run(root: Path, args: dict[str, Any]) -> int:
    monitor_id = args.get("monitor_id")
    req_id = args.get("req")

    if not monitor_id or not req_id:
        print(f"{RED}✗ both <MON-NNN> and --req <REQ_ID> are required{NC}")
        return 1

    result = defects_lib.create_defect_from_monitor(
        root,
        monitor_id=monitor_id,
        upstream_req_id=req_id,
        severity=args.get("severity", "medium"),
        title=args.get("title"),
    )

    if not result.get("ok"):
        print(f"{RED}✗ {result.get('error', 'Unknown error')}{NC}")
        return 1

    # WARN-AND-PROCEED: the lib never refuses on a healthy MONITOR; it surfaces a
    # warning for us to print. The DEF is created either way.
    if result.get("warning"):
        print(f"{YELLOW}⚠ {result['warning']}{NC}")

    print(f"{GREEN}✓ Created {result['id']}{NC} — {result['path']}")
    print(
        f"  Links: {CYAN}fails_to_meet{NC} → {req_id}, "
        f"{CYAN}exposed_by{NC} → {monitor_id}"
    )
    print(
        f"  Next: close the DEF once addressed — "
        f"`specflow update {result['id']} --status verified` then `--status closed` "
        f"(fires prevention-pattern capture)."
    )
    return 0
