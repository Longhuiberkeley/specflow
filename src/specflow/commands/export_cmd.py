"""specflow export — Export artifacts to external formats.

Primary interface: specflow export --adapter <name> --output <file>
Legacy alias:   specflow export <format> --output <file>  (deprecated)
"""

from __future__ import annotations

from pathlib import Path

from specflow.lib.adapters import get_adapter
from specflow.lib.display import RED, GREEN, NC


def run(root: Path, args: dict) -> int:
    root = root.resolve()
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
