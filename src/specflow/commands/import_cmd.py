"""specflow import — Import artifacts from external formats."""

from __future__ import annotations

from pathlib import Path

from specflow.lib import reqif as reqif_lib

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
NC = "\033[0m"


def run(root: Path, args: dict) -> int:
    root = root.resolve()
    sub = args.get("import_subcommand")
    if sub == "reqif":
        file_arg = args.get("file", "")
        if not file_arg:
            print(f"{RED}✗ specflow import reqif <file> required{NC}")
            return 1
        path = Path(file_arg).expanduser().resolve()
        result = reqif_lib.import_reqif(root, path)
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

    print(f"{RED}✗ unknown import subcommand: {sub}{NC}")
    return 1
