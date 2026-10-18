"""REQ-071 AC1 / STORY-751: the 19 ARCH/DDD bodies rewritten against the engine
as built (SPIKE-008) no longer carry the stale names the review recorded.

The rewrite line (``> Rewritten 2026-10-18 …``) may name what the earlier text
said, so it is excluded from the scan. Every other line of the body must be
free of the tokens below, each of which names a module, flag, library or count
that no longer exists in ``src/specflow``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SPECS = REPO / "_specflow" / "specs"

REWRITTEN = [
    "architecture/ARCH-001.md",
    "architecture/ARCH-003.md",
    "architecture/ARCH-004.md",
    "architecture/ARCH-005.md",
    "architecture/ARCH-007.md",
    "architecture/ARCH-009.md",
    "architecture/ARCH-010.md",
    "architecture/ARCH-011.md",
    "architecture/ARCH-014.md",
    "architecture/ARCH-015.md",
    "architecture/ARCH-016.md",
    "architecture/ARCH-017.md",
    "architecture/ARCH-018.md",
    "architecture/ARCH-019.md",
    "architecture/ARCH-020.md",
    "architecture/ARCH-025.md",
    "architecture/ARCH-027.md",
    "architecture/ARCH-031.md",
    "architecture/ARCH-035.md",
    "detailed-design/DDD-020.md",
]

# SPIKE-008 rows R1-027..036 and R1-101..111: names that left the engine.
STALE_TOKENS = [
    "best_practices.py",
    "copy_generic_fallback",
    "templates/best-practices/",
    "uuid5(",
    ".reqifz",
    "--direction",
    "read_version(",
    "merge_schemas(",
    "Click group",
    "Click command",
    "10 Tier-1",
    "14 registered",
    "src/specflow/platforms.yaml",
    "tests/test_lint.py",
    "standards-gaps",
    "checklists/conventions/",
    "validate_output_files",
    "parse_output_files",
]


def _body_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    body = parts[2] if len(parts) == 3 else text
    return [ln for ln in body.splitlines() if not ln.lstrip().startswith("> Rewritten")]


@pytest.mark.parametrize("rel", REWRITTEN)
def test_rewritten_body_has_no_stale_names(rel: str) -> None:
    path = SPECS / rel
    assert path.exists(), rel
    lines = _body_lines(path)
    hits = [
        (i + 1, tok)
        for i, ln in enumerate(lines)
        for tok in STALE_TOKENS
        if tok in ln
    ]
    assert not hits, f"{rel} still names removed engine surface: {hits}"


@pytest.mark.parametrize("rel", REWRITTEN)
def test_rewritten_body_carries_one_rewrite_line(rel: str) -> None:
    text = (SPECS / rel).read_text(encoding="utf-8")
    rewrite_lines = [ln for ln in text.splitlines() if ln.lstrip().startswith("> Rewritten 2026-10-18")]
    assert len(rewrite_lines) == 1, f"{rel}: expected exactly one rewrite line, found {len(rewrite_lines)}"
    assert "SPIKE-008" in rewrite_lines[0]
    assert "Amended 2026-10-18" not in text, f"{rel}: the v1.17.7 amendment note should be folded into the rewrite line"


def test_scanner_would_catch_a_stale_name(tmp_path: Path) -> None:
    sample = tmp_path / "ARCH-999.md"
    sample.write_text("---\nid: ARCH-999\n---\n\n> Rewritten 2026-10-18 (SPIKE-008)\n\nUses uuid5( ids.\n", encoding="utf-8")
    lines = _body_lines(sample)
    assert any("uuid5(" in ln for ln in lines)
