"""specflow export — Export artifacts to external formats or skills to platform formats.

Primary interface:
  specflow export --adapter <name> --output <file>     (artifact export)
  specflow export --skills --format <fmt> --output <dir>  (skill export)
Legacy alias:
  specflow export <format> --output <file>             (deprecated)
"""

from __future__ import annotations

from pathlib import Path

from specflow.lib.adapters import get_adapter
from specflow.lib.display import RED, GREEN, NC


def run(root: Path, args: dict) -> int:
    root = root.resolve()

    # Skill export path
    if args.get("export_skills"):
        from specflow.lib.skill_export import export_skills, FORMAT_HANDLERS

        fmt = args.get("export_format")
        if not fmt:
            print(f"{RED}✗ --format required with --skills. "
                  f"Available: {', '.join(FORMAT_HANDLERS)}{NC}")
            return 1

        output = args.get("output")
        if not output:
            output = "."
        out_dir = Path(output).expanduser().resolve()

        result = export_skills(out_dir, fmt)
        if not result.get("ok"):
            print(f"{RED}✗ {result.get('error')}{NC}")
            return 1

        print(f"{GREEN}✓ Exported {result['count']} skill(s) in {fmt} format to {result['output_dir']}{NC}")
        return 0

    # Artifact export path (existing)
    adapter_name = args.get("adapter")
    output = args.get("output")

    # Legacy subcommand path: export_subcommand == "reqif"
    if not adapter_name:
        legacy_sub = args.get("export_subcommand")
        if legacy_sub == "reqif":
            adapter_name = "reqif"
            output = args.get("output")
        if not adapter_name:
            print(f"{RED}✗ specflow export --adapter <name> --output <file> required{NC}")
            print(f"   Or: specflow export --skills --format <fmt> --output <dir>{NC}")
            return 1

    if not output:
        print(f"{RED}✗ --output argument required{NC}")
        return 1

    try:
        adapter = get_adapter(adapter_name)
    except ValueError as exc:
        print(f"{RED}✗ {exc}{NC}")
        return 1

    if "export_artifacts" not in adapter.supported_operations:
        print(
            f"{RED}✗ Adapter '{adapter_name}' does not support 'export_artifacts'{NC}"
        )
        return 1

    path = Path(output).expanduser().resolve()
    result = adapter.export_artifacts(path)

    if not result.get("ok"):
        print(f"{RED}✗ {result.get('error')}{NC}")
        return 1

    print(
        f"{GREEN}✓ Exported {result.get('written', 0)} requirement(s) to "
        f"{result.get('path')}{NC}"
    )
    return 0
