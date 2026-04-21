"""CLI handler for 'specflow detect' — project hygiene scans.

Two informational subcommands that never block:
- `specflow detect dead-code` — declared-but-unreferenced top-level symbols.
- `specflow detect similarity` — near-duplicate function bodies.

Both always return exit code 0 regardless of findings.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specflow.lib.analysis import (
    DeadSymbol,
    SimilarPair,
    find_dead_code,
    find_similar_functions,
)

from specflow.lib.display import YELLOW_DIM, GREEN, CYAN, NC

BOLD = "\033[1m"


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _run_dead_code(root: Path, args: dict[str, Any]) -> int:
    src_dir = args.get("src_dir") or "src"
    symbols: list[DeadSymbol] = find_dead_code(root, src_dir=src_dir)

    print(f"{BOLD}SpecFlow Detect — Dead Code{NC} (src: {src_dir})")
    if not symbols:
        print(f"  {GREEN}✓{NC} No dead code detected")
        return 0

    print(f"  {YELLOW_DIM}{len(symbols)} unreferenced top-level symbol(s):{NC}")
    for s in symbols:
        print(f"    {_rel(root, s.file)}:{s.line}  [{s.kind}] {s.name}")
    print(f"  {CYAN}Informational only — review manually before removing.{NC}")
    return 0


def _run_similarity(root: Path, args: dict[str, Any]) -> int:
    src_dir = args.get("src_dir") or "src"
    min_statements = args.get("min_statements") or 10
    threshold = args.get("threshold")
    threshold = 0.9 if threshold is None else float(threshold)

    pairs: list[SimilarPair] = find_similar_functions(
        root,
        src_dir=src_dir,
        min_statements=min_statements,
        threshold=threshold,
    )

    print(f"{BOLD}SpecFlow Detect — Similarity{NC} "
          f"(src: {src_dir}, min_statements: {min_statements}, threshold: {threshold})")
    if not pairs:
        print(f"  {GREEN}✓{NC} No near-duplicate functions found")
        return 0

    print(f"  {YELLOW_DIM}{len(pairs)} similar function pair(s):{NC}")
    for p in pairs:
        pct = p.similarity * 100
        print(
            f"    {pct:.1f}%  "
            f"{_rel(root, p.file_a)}:{p.lines_a[0]}-{p.lines_a[1]} {p.func_a}  <->  "
            f"{_rel(root, p.file_b)}:{p.lines_b[0]}-{p.lines_b[1]} {p.func_b}"
        )
    print(f"  {CYAN}Informational only — similar does not mean incorrect.{NC}")
    return 0


def run(root: Path, args: dict[str, Any]) -> int:
    subcommand = args.get("detect_subcommand")
    if subcommand == "dead-code":
        return _run_dead_code(root, args)
    if subcommand == "similarity":
        return _run_similarity(root, args)

    print("Usage: specflow detect {dead-code|similarity}")
    return 1
