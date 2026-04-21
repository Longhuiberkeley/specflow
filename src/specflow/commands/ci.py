"""specflow ci — CI adapter commands.

Subcommands:
  specflow ci generate    — Read adapters.yaml, generate CI workflow files
"""

from __future__ import annotations

from pathlib import Path

from specflow.lib.adapters import load_adapters_config, get_adapter
from specflow.lib.display import RED, GREEN, NC


def _generate(root: Path) -> int:
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
    written = 0
    for rel_path, content in files.items():
        out_path = root / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        print(f"{GREEN}✓ Wrote {rel_path}{NC}")
        written += 1

    print(f"\n{GREEN}✓ Generated {written} CI workflow file(s) using '{provider}' adapter{NC}")
    return 0


def run(root: Path, args: dict) -> int:
    root = root.resolve()
    sub = args.get("ci_subcommand")
    if sub == "generate":
        return _generate(root)

    print(f"{RED}✗ unknown ci subcommand: {sub}{NC}")
    return 1
