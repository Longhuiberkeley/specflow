"""specflow ci — CI adapter commands.

Subcommands:
  specflow ci generate [--force] [--dry-run]
      — Read adapters.yaml, write the provider's CI workflow files. Existing
        files that differ are preserved with a warning unless --force (which
        backs them up first); --dry-run only reports.
"""

from __future__ import annotations

import difflib
from pathlib import Path

from specflow.commands.hook import backup_file
from specflow.lib.adapters import load_adapters_config, get_adapter
from specflow.lib.display import RED, GREEN, YELLOW, NC


def _generate(root: Path, *, force: bool = False, dry_run: bool = False) -> int:
    """Write the provider's workflow files.

    An existing file that differs from the generated content is preserved with
    a warning (hand edits are the user's); ``--force`` overwrites it after a
    backup under ``.specflow/cache/backups/<timestamp>/ci/``; ``--dry-run``
    reports new / unchanged / differs without writing and prints a unified
    diff (existing -> generated) for a file that differs.
    """
    root = root.resolve()
    config = load_adapters_config(root)

    ci_cfg = config.get("ci") or {}
    provider = ci_cfg.get("provider")
    if not provider:
        print(f"{RED}✗ No CI provider configured in .specflow/adapters.yaml{NC}")
        return 1

    try:
        adapter = get_adapter(provider)
    except ValueError as exc:
        print(f"{RED}✗ {exc}{NC}")
        return 1

    ops = ci_cfg.get("operations", []) or []
    if not ops:
        print(f"{RED}✗ No CI operations listed in .specflow/adapters.yaml{NC}")
        return 1

    if "generate_ci_workflow" not in adapter.supported_operations:
        print(
            f"{RED}✗ Adapter '{provider}' does not support 'generate_ci_workflow'{NC}"
        )
        return 1

    files = adapter.generate_ci_workflow(ops)
    written = unchanged = skipped = 0
    for rel_path, content in files.items():
        out_path = root / rel_path
        if out_path.exists():
            existing = out_path.read_text(encoding="utf-8", errors="ignore")
            if existing == content:
                print(f"{GREEN}= {rel_path} unchanged{NC}")
                unchanged += 1
                continue
            if dry_run:
                print(f"{YELLOW}~ {rel_path} exists and differs (would be overwritten with --force){NC}")
                for line in _bounded_diff(existing, content, rel_path):
                    print(f"  {line}")
                skipped += 1
                continue
            if not force:
                print(f"{YELLOW}! {rel_path} exists and differs -- left as-is{NC}")
                print("  Overwrite it (a backup is taken first): specflow ci generate --force")
                print("  Preview the difference without writing: specflow ci generate --dry-run")
                skipped += 1
                continue
            backup = backup_file(root, out_path, "ci")
            print(f"{YELLOW}! Backed up {rel_path} to {backup.relative_to(root)}{NC}")
        elif dry_run:
            print(f"{GREEN}+ {rel_path} would be written (new){NC}")
            written += 1
            continue
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        print(f"{GREEN}✓ Wrote {rel_path}{NC}")
        written += 1

    verb = "Would generate" if dry_run else "Generated"
    summary = f"{verb} {written} CI workflow file(s) using '{provider}' adapter"
    if unchanged:
        summary += f", {unchanged} unchanged"
    if skipped:
        summary += f", {skipped} preserved (differs)"
    print(f"\n{GREEN}✓ {summary}{NC}")
    return 0


_DIFF_LINE_LIMIT = 60


def _bounded_diff(existing: str, generated: str, rel_path: str) -> list[str]:
    """Unified diff of the existing file against the generated content, capped."""
    lines = list(difflib.unified_diff(
        existing.splitlines(), generated.splitlines(),
        fromfile=f"{rel_path} (existing)", tofile=f"{rel_path} (generated)",
        lineterm="", n=2,
    ))
    if len(lines) > _DIFF_LINE_LIMIT:
        omitted = len(lines) - _DIFF_LINE_LIMIT
        lines = lines[:_DIFF_LINE_LIMIT] + [f"... ({omitted} more diff lines)"]
    return lines


def run(root: Path, args: dict) -> int:
    root = root.resolve()
    sub = args.get("ci_subcommand")
    if sub == "generate":
        return _generate(
            root,
            force=bool(args.get("force")),
            dry_run=bool(args.get("dry_run")),
        )

    print(f"{RED}✗ unknown ci subcommand: {sub}{NC}")
    return 1
