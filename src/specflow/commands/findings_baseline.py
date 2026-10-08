"""specflow findings-baseline — the only writer of the findings baseline.

REQ-053 AC7/AC8, DEC-099. ``update`` records the escalating lint
warnings a project accepts as known debt in ``.specflow/findings-baseline.yaml``:

- absent file: seed every current escalating-warning key;
- present file: always drop keys no longer produced (the ratchet only
  tightens); keys not yet recorded are added only with ``--accept-new``
  (approval-gated). Without it, new keys make ``update`` write nothing,
  list them and exit 1 — all or nothing.

``diff`` is read-only. Both use ``artifact_lint.collect`` — the exact path a
full lint run takes — so the baseline equals what CI sees.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from specflow.core import findings_baseline as fb
from specflow.core import policy
from specflow.lib import locks
from specflow.lib.display import CYAN, GREEN, NC, RED, YELLOW


def _as_of(args: dict[str, Any]) -> date | None:
    raw = args.get("as_of")
    if not raw:
        return datetime.now(timezone.utc).date()
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        print(f"{RED}✗ --as-of must be YYYY-MM-DD, got {raw!r}{NC}")
        return None


def _current_keys(root: Path, as_of: date) -> set[fb.Key]:
    from specflow.commands import artifact_lint

    _, findings = artifact_lint.collect(root, artifact_lint.CHECK_NAMES, as_of=as_of)
    return {f.key for f in policy.escalating_warnings(findings)}


def _fmt(key: fb.Key) -> str:
    rule, subjects = key
    return f"[{rule}] {' '.join(subjects)}"


def write_baseline(root: Path, keys: set[fb.Key] | frozenset[fb.Key]) -> None:
    """THE baseline write (AC8) — under the repo-wide mutation lock."""
    with locks.mutation_lock(root):
        locks.atomic_write(fb.baseline_path(root), fb.dumps(frozenset(keys)))


def _update(root: Path, args: dict[str, Any]) -> int:
    as_of = _as_of(args)
    if as_of is None:
        return 1
    existing, error = fb.load(root)
    if error is not None:
        print(f"{RED}✗{NC} {error.text.strip()} — fix or delete it, then re-run")
        return 1
    current = _current_keys(root, as_of)

    if existing is None:
        write_baseline(root, current)
        print(
            f"{GREEN}✓ Seeded {fb.BASELINE_FILE} with {len(current)} known "
            f"escalating warning(s) (as-of {as_of.isoformat()}).{NC} Commit it."
        )
        return 0

    resolved = existing - current
    new = current - existing
    if new and not args.get("accept_new"):
        print(f"{RED}✗ {len(new)} escalating warning(s) not in the baseline — nothing written:{NC}")
        for key in sorted(new):
            print(f"  {_fmt(key)}")
        print(
            "  Fix them, or record them as known debt with "
            "`specflow findings-baseline update --accept-new` (approval-gated)."
        )
        return 1

    target = (existing - resolved) | new
    if target == existing:
        print(f"{GREEN}✓ {fb.BASELINE_FILE} up to date ({len(existing)} known).{NC}")
        return 0
    write_baseline(root, target)
    if resolved:
        print(f"{GREEN}✓ Ratcheted down: removed {len(resolved)} resolved entr(ies).{NC}")
    if new:
        print(f"{YELLOW}⚠ Accepted {len(new)} new entr(ies) as known debt:{NC}")
        for key in sorted(new):
            print(f"  + {_fmt(key)}")
    print(f"  {fb.BASELINE_FILE}: {len(target)} known. Commit it.")
    return 0


def _diff(root: Path, args: dict[str, Any]) -> int:
    as_of = _as_of(args)
    if as_of is None:
        return 1
    existing, error = fb.load(root)
    if error is not None:
        print(f"{RED}✗{NC} {error.text.strip()}")
        return 1
    if existing is None:
        print(f"{CYAN}ℹ No {fb.BASELINE_FILE} — ratchet off. Seed it: specflow findings-baseline update{NC}")
        return 0
    current = _current_keys(root, as_of)
    new, resolved = sorted(current - existing), sorted(existing - current)
    print(f"Findings baseline: {len(existing & current)} known, {len(new)} new, {len(resolved)} resolved")
    for key in new:
        print(f"  {RED}+ new{NC}      {_fmt(key)}")
    for key in resolved:
        print(f"  {GREEN}- resolved{NC} {_fmt(key)}")
    return 1 if new else 0


def run(root: Path, args: dict[str, Any]) -> int:
    sub = args.get("findings_baseline_subcommand")
    if sub == "update":
        return _update(root, args)
    if sub == "diff":
        return _diff(root, args)
    print("Usage: specflow findings-baseline {update [--accept-new] | diff} [--as-of YYYY-MM-DD]")
    return 1
