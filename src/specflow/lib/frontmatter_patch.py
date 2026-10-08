"""Patch one top-level frontmatter key without re-serialising the rest.

Writers that only *record* something on an artifact (``checklists_applied``
from ``checklist-run``, ``output_files`` from retro-link) must not reformat
the fields they do not own: a YAML round-trip turns flow lists into block
lists, re-quotes strings, drops comments and reorders keys, so a
``checklist-run --all`` used to rewrite every artifact in the store.

:func:`split_frontmatter` finds the fences by line (a ``---`` inside a value
or the body is not a fence) and keeps any leading blank lines, which
``parse_artifact`` also tolerates. :func:`patch_block` splices the YAML for
one key over the old block for that key, or appends it. Every other byte of
the file is reproduced as-is. Comment lines inside the replaced block belong
to the record and are dropped with it; comments after it are kept.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

_FENCE = re.compile(r"^---[ \t]*$", re.MULTILINE)


def split_frontmatter(text: str) -> tuple[str, str, str] | None:
    """Split ``text`` into ``(prefix, frontmatter_yaml, rest)`` or None.

    ``prefix`` is everything up to and including the opening fence line
    (leading blank lines plus ``---\\n``), ``rest`` starts at the closing
    fence, so ``prefix + frontmatter_yaml + rest == text``.
    """
    start = len(text) - len(text.lstrip())
    first = _FENCE.match(text, start)
    if first is None or first.start() != start:
        return None
    fm_start = first.end() + 1  # past the newline of the opening fence
    if fm_start > len(text):
        return None
    close = _FENCE.search(text, fm_start)
    if close is None:
        return None
    return text[:fm_start], text[fm_start:close.start()], text[close.start():]


def _block_re(key: str) -> re.Pattern[str]:
    # The key line, then every continuation line: indented, a list item, or a
    # comment. Comments are consumed so a record interrupted by one is still
    # replaced as a whole (a stray tail would re-attach to the new block).
    return re.compile(
        rf"^{re.escape(key)}:[^\n]*\n(?:(?:[ \t-]|#)[^\n]*\n)*", re.MULTILINE
    )


def patch_block(fm_text: str, key: str, value: Any) -> str:
    """Return ``fm_text`` with the block for ``key`` replaced by ``value``.

    Only the lines of that key are touched; when the key is absent the block
    is appended. Comment lines that trail the old block (and so belong to the
    next key) are left in place.
    """
    block = yaml.dump({key: value}, default_flow_style=False, sort_keys=False,
                      allow_unicode=True)
    m = _block_re(key).search(fm_text)
    if m is None:
        if fm_text and not fm_text.endswith("\n"):
            fm_text += "\n"
        return fm_text + block
    end = m.end()
    # Give back trailing comment lines: they precede the next key, not ours.
    while True:
        prev = fm_text.rfind("\n", m.start(), end - 1)
        line = fm_text[prev + 1:end]
        if prev == -1 or not line.startswith("#"):
            break
        end = prev + 1
    return fm_text[: m.start()] + block + fm_text[end:]
