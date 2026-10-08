"""Terminal colour constants.

Colour is on only when it can be seen: ``FORCE_COLOR`` (non-empty, not
``0``) always enables it, ``NO_COLOR`` (non-empty, https://no-color.org)
always disables it, otherwise it follows whether stdout is a TTY. Agents
piping ``specflow`` output through ``cat``/``grep``/a tool harness therefore
get plain text and never have to strip escape sequences (F-023, v1.17.2).
The decision is taken once at import so every importer sees one value.
"""

from __future__ import annotations

import os
import sys


def colour_enabled() -> bool:
    force = os.environ.get("FORCE_COLOR", "")
    if force not in ("", "0"):
        return True
    if os.environ.get("NO_COLOR", ""):
        return False
    try:
        return bool(sys.stdout.isatty())
    except (AttributeError, ValueError):
        return False


_ON = colour_enabled()

RED = "\033[0;31m" if _ON else ""
GREEN = "\033[0;32m" if _ON else ""
YELLOW = "\033[1;33m" if _ON else ""
YELLOW_DIM = "\033[0;33m" if _ON else ""
CYAN = "\033[0;36m" if _ON else ""
BOLD = "\033[1m" if _ON else ""
DIM = "\033[2m" if _ON else ""
NC = "\033[0m" if _ON else ""
