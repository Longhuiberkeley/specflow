#!/usr/bin/env python3
"""SpecFlow privacy denylist gate (DDD-029) — single source of truth.

Scope, pattern, and exception policy are frozen in
_specflow/specs/detailed-design/DDD-029.md (REQ-038). This script is consumed
by CI (.github/workflows/specflow.yml) and by tests/test_denylist_gate.py —
never duplicate the pattern elsewhere.

Sanctioned exceptions are ENUMERATED, not pattern-based (ARCH-029):
  - REQ-038.md, DDD-029.md            the requirement/design quote the denylist
  - domain-research-checklists.md     sanctioned model-family vocabulary (Kalman)
  - scripts/denylist_gate.py          this gate carries the pattern itself
  - tests/test_denylist_gate.py       the gate's test carries sample tokens

Exit 0 = clean; exit 1 = violations printed as file:line:match.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Single source of truth: the pattern lives in the shipped package
# (specflow.lib.privacy). Bootstrap src/ onto sys.path so this script runs
# standalone in a bare CI checkout (no uv sync needed by the privacy job).
_SRC = REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from specflow.lib.privacy import PATTERN  # noqa: E402

SCOPE_DIRS = ("src", "tests", "docs", "scripts", "_specflow")
SCOPE_FILES = ("CHANGELOG.md", "README.md", "ROADMAP.md")

ALLOWLIST_PATHS = (
    "src/specflow/packs/autoresearch/skills/specflow-autoresearch/references/"
    "domain-research-checklists.md",
    "src/specflow/lib/privacy.py",
    "scripts/denylist_gate.py",
    "tests/test_denylist_gate.py",
    "tests/test_privacy_redaction.py",
)

_REQUIREMENT_SPEC = "_specflow/specs/requirements/REQ-038.md"
_DESIGN_SPEC = "_specflow/specs/detailed-design/DDD-029.md"


def _allowlisted(rel: str) -> bool:
    """Exact-path matching on the scan-root-relative path — ARCH-029:
    'enumerated, not pattern-based'. A suffix trick
    (docs/domain-research-checklists.md, other/REQ-038.md) must NOT bypass."""
    return (
        rel == _REQUIREMENT_SPEC
        or rel == _DESIGN_SPEC
        or rel in ALLOWLIST_PATHS
    )


def scan_files(files: list[Path], root: Path) -> list[tuple[Path, int, str]]:
    """Core scan over an explicit file list (also the test surface)."""
    skip_suffixes = {".pyc", ".pyo", ".so"}
    violations: list[tuple[Path, int, str]] = []
    for path in sorted(files):
        rel = path.relative_to(root).as_posix()
        if _allowlisted(rel):
            continue
        if path.suffix in skip_suffixes or "__pycache__" in path.parts:
            continue  # build artifacts embed absolute paths; never tracked
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if PATTERN.search(line):
                violations.append((path.relative_to(root), lineno, line.strip()[:120]))
    return violations


def scan(root: Path = REPO_ROOT) -> list[tuple[Path, int, str]]:
    """Scan the frozen DDD-029 scope under `root` (dirs + top-level files)."""
    files: list[Path] = []
    for d in SCOPE_DIRS:
        p = root / d
        if p.is_dir():
            files.extend(q for q in p.rglob("*") if q.is_file())
    for f in SCOPE_FILES:
        p = root / f
        if p.is_file():
            files.append(p)
    return scan_files(files, root)


def main() -> int:
    violations = scan()
    if not violations:
        print("privacy gate: CLEAN (0 denylist hits in scope)")
        return 0
    print(f"privacy gate: {len(violations)} denylist hit(s) in scope:")
    for rel, lineno, line in violations:
        print(f"  {rel}:{lineno}: {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
