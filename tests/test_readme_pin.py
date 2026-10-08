"""README guards (STORY-712 AC2): the install pin tracks the released version.

The README's ``uv tool install git+…@v<ver>`` example drifted four minor
versions behind the engine once, because nothing checked it. These tests pin
the README to ``specflow.__version__`` and keep the other release-prose
hygiene rules that drifted with it: no ``(new)`` badges that never get
retired, no hard-coded subcommand count, and a Docs list that links every
file under ``docs/``.
"""

from __future__ import annotations

import re
from pathlib import Path

import specflow

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
DOCS_DIR = REPO_ROOT / "docs"

_PIN_RE = re.compile(r"github\.com/Longhuiberkeley/specflow@v(\d+\.\d+\.\d+)")


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def test_readme_pin_matches_package_version():
    pins = _PIN_RE.findall(_readme())
    assert pins, "README must show a pinned install example (`…specflow@vX.Y.Z`)"
    stale = sorted({p for p in pins if p != specflow.__version__})
    assert not stale, (
        f"README pins {stale} but specflow.__version__ is {specflow.__version__}; "
        "update the `uv tool install …@v<ver>` example (AGENTS.md release step)"
    )


def test_readme_has_no_new_badges():
    text = _readme()
    badges = [ln for ln in text.splitlines() if "*(new)*" in ln or re.search(r"\(new in v\d", ln)]
    assert not badges, "README '(new)' badges are never retired; describe the feature without one:\n" + "\n".join(badges)


def test_readme_has_no_hardcoded_subcommand_count():
    hits = re.findall(r"\b\d+ subcommands\b", _readme())
    assert not hits, f"README hard-codes a subcommand count {hits}; the CLI reference is the catalog"


def test_readme_links_every_doc():
    text = _readme()
    linked = set(re.findall(r"\]\(docs/([\w-]+\.md)\)", text))
    on_disk = {p.name for p in DOCS_DIR.glob("*.md")}
    missing = sorted(on_disk - linked)
    assert not missing, f"docs/ files not linked from the README Docs list: {missing}"
    dangling = sorted(linked - on_disk)
    assert not dangling, f"README links docs that do not exist: {dangling}"
