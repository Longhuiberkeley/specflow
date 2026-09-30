"""Read and serialise the committed findings baseline (REQ-053 AC7/AC8).

``.specflow/findings-baseline.yaml`` holds the escalating-warning keys a
project has accepted as known debt. This module never writes: the only
writer is ``specflow findings-baseline update``
(``specflow.commands.findings_baseline``). The format is one entry per key,
sorted, with no counts or timestamps, so re-running is byte-idempotent and
worktrees merge cleanly.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.core.findings import Finding, make

BASELINE_FILE = ".specflow/findings-baseline.yaml"
FORMAT = 1
_HEADER = (
    "# Managed by `specflow findings-baseline update` — do not hand-edit\n"
    "# (REQ-053 AC7/AC8). Escalating lint warnings accepted as known debt.\n"
)

Key = tuple[str, tuple[str, ...]]


def baseline_path(root: Path) -> Path:
    return root / BASELINE_FILE


def load(root: Path) -> tuple[frozenset[Key] | None, Finding | None]:
    """Return ``(keys, error)``: ``keys`` is None when the file is absent;
    a malformed file yields ``(None, blocking schema-error finding)``."""
    path = baseline_path(root)
    if not path.exists():
        return None, None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data is None:
            data = {"format": FORMAT, "entries": []}
        if not isinstance(data, dict) or data.get("format") != FORMAT:
            raise ValueError(f"expected a mapping with format: {FORMAT}")
        keys: set[Key] = set()
        for entry in data.get("entries") or []:
            rule = entry.get("rule") if isinstance(entry, dict) else None
            subjects = entry.get("subjects") if isinstance(entry, dict) else None
            if not isinstance(rule, str) or not isinstance(subjects, list):
                raise ValueError(f"bad entry {entry!r}")
            keys.add((rule, tuple(str(s) for s in subjects)))
        return frozenset(keys), None
    except (yaml.YAMLError, ValueError, AttributeError) as exc:
        return None, make(
            "findings-baseline/schema-error", (BASELINE_FILE,), "blocking",
            text=f"  ✗ schema-error: malformed {BASELINE_FILE} ({exc})",
        )


def dumps(keys: frozenset[Key] | set[Key]) -> str:
    entries = [
        {"rule": rule, "subjects": list(subjects)} for rule, subjects in sorted(keys)
    ]
    body = yaml.safe_dump(
        {"format": FORMAT, "entries": entries},
        sort_keys=False, allow_unicode=True, default_flow_style=None, width=1000,
    )
    return _HEADER + body
