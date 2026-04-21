"""specflow import — Import artifacts from external formats.

Primary interface: specflow import --adapter <name> <file>
Legacy alias:   specflow import <format> <file>  (deprecated)
"""

from __future__ import annotations

from pathlib import Path

from specflow.lib.adapters import get_adapter
from specflow.lib.display import RED, GREEN, YELLOW, NC


def run(root: Path, args: dict) -> int:
    root = root.resolve()
    adapter_name = args.get("adapter")
    file_arg = args.get("file")

    # Legacy subcommand path: import_subcommand == "reqif"
    if not adapter_name:
        legacy_sub = args.get("import_subcommand")
        if legacy_sub == "reqif":
            adapter_name = "reqif"
            file_arg = args.get("file")
        if not adapter_name:
            print(f"{RED}✗ specflow import --adapter <name> <file> required{NC}")
            return 1

    if not file_arg:
        print(f"{RED}✗ file argument required{NC}")
        return 1

    try:
        adapter = get_adapter(adapter_name)
    except ValueError as exc:
        print(f"{RED}✗ {exc}{NC}")
        return 1

    if "import_artifacts" not in adapter.supported_operations:
        print(
            f"{RED}✗ Adapter '{adapter_name}' does not support 'import_artifacts'{NC}"
        )
        return 1

    path = Path(file_arg).expanduser().resolve()
    result = adapter.import_artifacts(path)

    if not result.get("ok"):
        print(f"{RED}✗ {result.get('error')}{NC}")
        return 1

    created = result.get("created") or []
    skipped = result.get("skipped") or []
    print(f"{GREEN}✓ Imported {len(created)} requirement(s) from {path.name}{NC}")
    for art_id in created:
        print(f"  • {art_id}")
    for entry in skipped:
        print(f"{YELLOW}  ⚠ Skipped {entry.get('id', '?')}: {entry.get('reason', '')}{NC}")
    return 0
