"""Status is written only through artifacts.update_artifact (STORY-697 AC5, DEC-093).

A grep ban over src/specflow: no module other than lib/artifacts.py may
write an artifact's ``status`` field directly (frontmatter subscript
assignment, ``_update_frontmatter_field(..., "status", ...)``, or a text
substitution of a ``status:`` line), and the pre-DEC-093 ``merged_into``
pseudo-status appears nowhere. Building an ``updates`` dict that is handed to
update_artifact is the sanctioned path and is not matched.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "specflow"

# The one module allowed to write status: update_artifact and its helpers.
ALLOWLIST = {"lib/artifacts.py"}

BANNED = [
    ("frontmatter subscript write",
     re.compile(r"\b(fm|frontmatter|front_matter|meta|header)\[\s*[\"']status[\"']\s*\]\s*=(?!=)")),
    ("frontmatter field helper",
     re.compile(r"_(update|set|write)_frontmatter_field\([^)]*[\"']status[\"']")),
    ("status line substitution",
     re.compile(r"(\.replace|re\.sub)\([^)\n]*[\"'][\^]?status:")),
    ("frontmatter update/setdefault",
     re.compile(r"\b(fm|frontmatter|front_matter|meta|header)\.(update|setdefault)\("
                r"[^)]*([\"']status[\"']|\bstatus=)")),
    ("merged_into pseudo-status", re.compile(r"merged_into")),
]


def scan(text: str) -> list[str]:
    hits = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for label, pattern in BANNED:
            if pattern.search(line):
                hits.append(f"{lineno}: {label}: {line.strip()}")
    return hits


def test_no_status_write_outside_update_artifact():
    offenders = {}
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC).as_posix()
        if rel in ALLOWLIST:
            continue
        hits = scan(path.read_text(encoding="utf-8"))
        if hits:
            offenders[rel] = hits
    assert offenders == {}, offenders


@pytest.mark.parametrize("line", [
    'fm["status"] = "merged_into"',
    "frontmatter['status'] = new",
    '_update_frontmatter_field(path, "status", "superseded")',
    'text = text.replace("status: approved", "status: verified")',
    "new = re.sub(r'^status: .*$', 'status: x', text)",
    'reason = "merged_into"',
    'fm.update({"status": "verified"})',
    'frontmatter.update(status="verified")',
    "fm.setdefault('status', 'approved')",
])
def test_seeded_violation_is_caught(line):
    assert scan(line), line


@pytest.mark.parametrize("line", [
    'updates["status"] = "running"',
    'record["status"] = entry.get("status")',
    'if fm["status"] == "draft":',
    'art_lib.update_artifact(root, tid, status=to_st)',
])
def test_sanctioned_forms_are_not_matched(line):
    assert scan(line) == [], line
