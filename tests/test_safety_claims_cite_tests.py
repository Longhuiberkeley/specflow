"""Safety claims in code must cite the test that backs them (STORY-696 AC7).

SPIKE-003 was triggered by two false claims: locks.py called the stale-break
race "nanosecond-scale" and renumber_drafts.py said "re-running is safe".
Any docstring or comment in src/ that makes such a claim must name a
``tests/`` path in the same docstring or comment block, so the claim is
checkable. The allowlist is shrink-only.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"

CLAIM = re.compile(
    r"safe to re-?run|re-?running is safe|race-free|crash-safe|nanosecond"
    r"|every artifact mutation goes through|atomic with respect to",
    re.IGNORECASE,
)
CITE = re.compile(r"\btests/[\w./-]+")

# Shrink-only: "<path relative to src> <first line of the block>" entries for
# claims that legitimately cannot cite a test. Keep empty if possible.
ALLOWLIST: set[str] = set()


def _blocks(source: str) -> list[tuple[int, str]]:
    """(line, text) of every docstring and every run of adjacent comments."""
    out: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc:
                line = node.body[0].lineno if node.body else 1
                out.append((line, doc))
    run: list[str] = []
    start = 0
    last = -2
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type != tokenize.COMMENT:
            continue
        line = tok.start[0]
        if line != last + 1 and run:
            out.append((start, "\n".join(run)))
            run = []
        if not run:
            start = line
        run.append(tok.string)
        last = line
    if run:
        out.append((start, "\n".join(run)))
    return out


def uncited_claims(src: Path = SRC) -> list[str]:
    found = []
    for path in sorted(src.rglob("*.py")):
        rel = path.relative_to(src).as_posix()
        for line, text in _blocks(path.read_text(encoding="utf-8")):
            m = CLAIM.search(text)
            if m and not CITE.search(text):
                key = f"{rel} {text.strip().splitlines()[0][:60]}"
                if key not in ALLOWLIST:
                    found.append(f"{rel}:{line}: '{m.group(0)}' without a tests/ citation")
    return found


def test_safety_claims_cite_a_test():
    found = uncited_claims()
    assert not found, (
        "safety claims must cite the test that proves them (or be removed):\n  "
        + "\n  ".join(found)
    )


def test_seeded_claims_are_caught(tmp_path: Path):
    pkg = tmp_path / "src"
    pkg.mkdir()
    (pkg / "m.py").write_text(
        '"""Re-running is safe."""\n'
        "# the window is nanosecond-scale\n"
        "def f():\n"
        '    """Crash-safe: tests/formal/test_index_store_crash.py proves it."""\n'
        "# race-free (see\n"
        "# tests/test_create_locking.py)\n",
        encoding="utf-8",
    )
    found = uncited_claims(pkg)
    assert [f.split(": ")[1] for f in found] == [
        "'Re-running is safe' without a tests/ citation",
        "'nanosecond' without a tests/ citation",
    ], found
