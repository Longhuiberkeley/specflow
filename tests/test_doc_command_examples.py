"""Regression guard: documented `specflow create` commands must actually parse.

Two recent bugs shipped docs printing `specflow create` invocations that crash
argparse: (1) flags that don't exist, and (2) `--set links=...` colliding with
the dedicated `create_artifact(links=...)` keyword (see test_create_set_fields.py
for the runtime side of that fix). This test scans the shipped skill docs for
fenced-code-block `specflow create` / `uv run specflow create` invocations and
verifies each one parses cleanly against the real CLI argparse parser — it does
not execute anything, only validates argument parsing.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import pytest

from specflow.cli import build_parser

REPO_ROOT = Path(__file__).resolve().parents[1]

_SCAN_ROOTS = [
    REPO_ROOT / "src" / "specflow",
    REPO_ROOT / ".claude" / "skills",
]

_FENCE_RE = re.compile(r"^```")
_PLACEHOLDER_RE = re.compile(r"<[^>]+>")
_ANNOTATED_CMD_PREFIXES = ("specflow create", "uv run specflow create")


def _iter_markdown_files():
    for scan_root in _SCAN_ROOTS:
        if not scan_root.exists():
            continue
        yield from sorted(scan_root.rglob("*.md"))


def _iter_fenced_blocks(text: str):
    """Yield (start_line_number, list_of_lines) for each fenced code block.

    start_line_number is 1-based and points at the first line *inside* the
    fence (the line after the opening ``` marker).
    """
    lines = text.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        if _FENCE_RE.match(lines[i].strip()):
            block_start = i + 2  # 1-based line number of first line inside the fence
            i += 1
            block_lines = []
            while i < n and not _FENCE_RE.match(lines[i].strip()):
                block_lines.append(lines[i])
                i += 1
            yield block_start, block_lines
            # i now points at the closing fence (or EOF); advance past it.
            i += 1
        else:
            i += 1


def _extract_commands(block_lines: list[str], block_start_line: int):
    """Yield (line_number, logical_command_string) for each specflow-create
    invocation (joining backslash line continuations) found in a code block.
    """
    i = 0
    n = len(block_lines)
    while i < n:
        raw = block_lines[i]
        stripped = raw.strip()
        if stripped.startswith(_ANNOTATED_CMD_PREFIXES):
            start_line = block_start_line + i
            parts = []
            cur = raw.rstrip()
            while cur.endswith("\\"):
                parts.append(cur[:-1].strip())
                i += 1
                if i >= n:
                    cur = ""
                    break
                cur = block_lines[i].rstrip()
            parts.append(cur.strip())
            i += 1
            logical_cmd = " ".join(p for p in parts if p)
            yield start_line, logical_cmd
        else:
            i += 1


def _collect_all_commands():
    """Return (list_of_(file, line, command), list_of_skipped_(file, line, command, reason))."""
    commands = []
    skipped = []
    for md_file in _iter_markdown_files():
        text = md_file.read_text(encoding="utf-8")
        for block_start, block_lines in _iter_fenced_blocks(text):
            for line_no, cmd in _extract_commands(block_lines, block_start):
                if "$(" in cmd:
                    skipped.append((md_file, line_no, cmd, "shell substitution — not statically parseable"))
                    continue
                commands.append((md_file, line_no, cmd))
    return commands, skipped


@pytest.fixture(scope="module")
def all_doc_commands():
    return _collect_all_commands()


def test_doc_command_scan_finds_commands(all_doc_commands):
    """Sanity check: the scan must actually find documented create commands,
    otherwise this test would silently pass on zero coverage."""
    commands, _skipped = all_doc_commands
    assert len(commands) >= 10, (
        f"Expected to find at least 10 documented `specflow create` commands, "
        f"found {len(commands)}. The scanner may be broken."
    )


def test_documented_create_commands_parse(all_doc_commands):
    parser = build_parser()
    commands, _skipped = all_doc_commands
    failures = []
    for md_file, line_no, cmd in commands:
        placeholder_free = _PLACEHOLDER_RE.sub("X", cmd)
        try:
            argv = shlex.split(placeholder_free)
        except ValueError as exc:
            failures.append(f"{md_file}:{line_no}: could not tokenize command: {cmd!r} ({exc})")
            continue

        # Strip the leading `uv run specflow` / `specflow` prefix so argv
        # starts at the subcommand ("create ...").
        if argv[:3] == ["uv", "run", "specflow"]:
            argv = argv[3:]
        elif argv[:1] == ["specflow"]:
            argv = argv[1:]

        try:
            parser.parse_args(argv)
        except SystemExit:
            failures.append(f"{md_file}:{line_no}: `{cmd}` failed to parse (argv={argv!r})")

    assert not failures, "Documented commands failed to parse:\n" + "\n".join(failures)
