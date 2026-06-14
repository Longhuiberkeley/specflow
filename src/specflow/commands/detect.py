"""CLI handler for 'specflow detect' — project hygiene scans.

Three informational subcommands that never block:
- `specflow detect dead-code` — declared-but-unreferenced top-level symbols.
- `specflow detect similarity` — near-duplicate function bodies.
- `specflow detect orphan-code` — source files not referenced by any
  STORY/REQ/ARCH/DDD. Use `--retro-link <ID>` to retroactively link all orphan
  files to an artifact (any of STORY/ARCH/DDD/REQ).

All return exit code 0 regardless of findings (informational only).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from specflow.lib.analysis import (
    DeadSymbol,
    SimilarPair,
    find_dead_code,
    find_similar_functions,
)
from specflow.lib.orphans import find_orphan_code, retro_link

from specflow.lib.display import YELLOW_DIM, GREEN, CYAN, NC, RED, YELLOW

BOLD = "\033[1m"


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _biggest_orphan_cluster(root: Path, orphans: list[Path]) -> tuple[str | None, int]:
    """Group orphan files by top-level directory; return (top-dir, count) or (None, 0).

    The top-level directory is the adoption boundary signal: "the biggest
    un-adopted chunk of the repo is X". Files at the repo root bucket as "(root)".
    """
    if not orphans:
        return None, 0
    buckets: Counter[str] = Counter()
    for f in orphans:
        try:
            rel = f.relative_to(root)
        except ValueError:
            rel = Path(f.name)
        top = rel.parts[0] if len(rel.parts) > 1 else "(root)"
        buckets[top] += 1
    top_dir, count = buckets.most_common(1)[0]
    return top_dir, count


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


def _run_orphan_code(root: Path, args: dict[str, Any]) -> int:
    result = find_orphan_code(root)
    orphans = result["orphan_files"]
    total = result["total_count"]
    ref_count = result["referenced_count"]

    coverage_pct = (100.0 * ref_count / total) if total else 100.0

    print(f"{BOLD}SpecFlow Detect — Orphan Code{NC}")
    print(f"  Source files scanned: {total}")
    print(f"  Referenced by an artifact: {ref_count}  ({coverage_pct:.1f}% coverage)")
    print(f"  Orphan files: {len(orphans)}")

    if not orphans:
        print(f"  {GREEN}✓{NC} All source files trace to an artifact (STORY/REQ/ARCH/DDD)")
        return 0

    top_dir, cluster_count = _biggest_orphan_cluster(root, orphans)
    if top_dir is not None:
        print(f"  {YELLOW}Biggest un-adopted cluster:{NC} {top_dir}/ ({cluster_count} files)")

    print(f"  {YELLOW_DIM}Unreferenced source files:{NC}")
    for f in sorted(orphans):
        print(f"    {_rel(root, f)}")

    retro_target = args.get("retro_link_target") or args.get("retro_link_story")
    if retro_target:
        print(f"\n  {CYAN}Retro-linking all orphan files to {retro_target}...{NC}")
        linked = 0
        for f in orphans:
            if retro_link(root, str(_rel(root, f)), retro_target):
                linked += 1
        print(f"  {GREEN}✓{NC} Linked {linked}/{len(orphans)} orphan files to {retro_target}")
        if linked < len(orphans):
            print(f"  {YELLOW_DIM}{len(orphans) - linked} files could not be linked (target not found or file error){NC}")
        return 0 if linked == len(orphans) else 1
    else:
        print(f"\n  {CYAN}Tip:{NC} Use --retro-link <ID> to retroactively link all orphan files to an existing artifact (STORY/ARCH/DDD/REQ).")
        print(f"  {YELLOW_DIM}Orphan code breaks SpecFlow traceability. Run with --retro-link to fix, or review manually.{NC}")

    return 1


def run(root: Path, args: dict[str, Any]) -> int:
    subcommand = args.get("detect_subcommand")
    if subcommand == "dead-code":
        return _run_dead_code(root, args)
    if subcommand == "similarity":
        return _run_similarity(root, args)
    if subcommand == "orphan-code":
        return _run_orphan_code(root, args)

    print("Usage: specflow detect {dead-code|similarity|orphan-code}")
    return 1
