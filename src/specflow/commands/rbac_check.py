"""specflow rbac check — surface resolved roles and (optionally) test an authorization.

`lib/rbac.py` has always had the primitives (`resolve_author_roles`,
`authorize_status_transition`, `current_git_author_email`), but no user-facing
command exposed them — agents were told to "inspect config.yaml" manually. This
is a thin, read-only wrapper: nested under `rbac` (`specflow rbac check`) so a
future `rbac doctor` has a natural home alongside it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specflow.lib import rbac as rbac_lib
from specflow.lib.display import RED, GREEN, YELLOW, CYAN, BOLD, DIM, NC


def run(root: Path, args: dict[str, Any]) -> int:
    root = root.resolve()

    team = rbac_lib._team_section(root)  # noqa: SLF001 (same-package reuse, see phase_status.py precedent)
    if not rbac_lib._has_configured_roles(team):  # noqa: SLF001
        print(f"{YELLOW}No team configuration in .specflow/ — RBAC is not active (single-user mode).{NC}")
        return 0

    email = (args.get("email") or "").strip()
    if not email:
        email = rbac_lib.current_git_author_email(root)

    if not email:
        print(f"{RED}✗ No email resolved — pass --email or configure git user.email.{NC}")
        return 1

    roles = rbac_lib.resolve_author_roles(root, email)

    print(f"\n{CYAN}SpecFlow RBAC{NC}")
    print(f"  Author: {BOLD}{email}{NC}")
    if roles:
        print(f"  Roles:  {GREEN}{', '.join(roles)}{NC}")
    else:
        print(f"  Roles:  {DIM}(none assigned){NC}")

    art_type = (args.get("type") or "").strip()
    to_status = (args.get("to_status") or "").strip()

    if art_type and to_status:
        # `authorize_status_transition` only uses the id in its message text —
        # a bare type/prefix is a fine stand-in when no specific ID is given.
        artifact_id = art_type if "-" in art_type else f"{art_type}-000"
        ok, reason = rbac_lib.authorize_status_transition(root, artifact_id, to_status, email)
        print()
        if ok:
            print(f"  {GREEN}✓ Allowed{NC}: '{email}' may transition {art_type} -> '{to_status}'.")
            print()
            return 0
        print(f"  {RED}✗ Denied{NC}: {reason}")
        print()
        return 1

    if art_type or to_status:
        print(f"\n  {YELLOW}Note: both --type and --to-status are required to run an authorization check.{NC}")

    print()
    return 0
