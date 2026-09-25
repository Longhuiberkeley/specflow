"""Deprecated CLI alias for ``specflow practices seed``."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def run(root: Path, args: dict[str, Any]) -> int:
    """Delegate the legacy command to the practice-seed implementation."""
    print(
        "Deprecated: `specflow handbook generate` is retained as an alias; "
        "use `specflow practices seed`.",
        file=sys.stderr,
    )
    from specflow.commands.practices import run as practices_run

    return practices_run(root, {**args, "practices_subcommand": "seed"})
