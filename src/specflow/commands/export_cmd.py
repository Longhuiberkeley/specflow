"""specflow export — Export artifacts to external formats."""

from __future__ import annotations

from pathlib import Path

from specflow.lib import reqif as reqif_lib

RED = "\033[0;31m"
GREEN = "\033[0;32m"
NC = "\033[0m"


def run(root: Path, args: dict) -> int:
    root = root.resolve()
    sub = args.get("export_subcommand")
    if sub == "reqif":
        output = args.get("output", "")
        if not output:
            print(f"{RED}✗ specflow export reqif --output <file> required{NC}")
            return 1
        path = Path(output).expanduser().resolve()
        result = reqif_lib.export_reqif(root, path)
        if not result.get("ok"):
            print(f"{RED}✗ {result.get('error')}{NC}")
            return 1
        print(
            f"{GREEN}✓ Exported {result.get('written', 0)} requirement(s) to "
            f"{result.get('path')}{NC}"
        )
        return 0

    print(f"{RED}✗ unknown export subcommand: {sub}{NC}")
    return 1
