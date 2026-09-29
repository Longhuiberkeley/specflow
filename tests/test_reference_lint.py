"""STORY-688 AC2: shipped templates and packs carry no repository-internal
references, and every shipped SKILL.md stays inside its line budget.

Shipped text is copied into a consuming project, where this repository's
source tree, its docs/ files and its dogfood .claude/skills mirror do not
exist. A pointer to any of them is a dead link for the user. Legacy
`D-NN` decision ids were retired for artifact ids (DEC-NNN) and must not
reappear.

What is NOT a repository-internal reference (and stays allowed):
- a project's own `docs/` tree (`roots: ["docs/"]`, `docs/adr/...`): the docs
  surface and adoption pack read the user's docs;
- the `.claude/` and `.claude/skills` platform directories (install targets
  and platform markers);
- GitHub URLs (`https://github.com/.../blob/main/docs/...`).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src" / "specflow"
SHIPPED_ROOTS = [SRC / "templates", SRC / "packs"]
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".sh", ".toml", ".json", ".txt", ".py"}

# SpecFlow's own documentation files: `docs/<one of these>` is a pointer into
# this repository, never into the user's project.
_REPO_DOCS = sorted(p.name for p in (REPO_ROOT / "docs").glob("*.md"))
_URL = re.compile(r"https?://\S+")

RULES: list[tuple[str, re.Pattern[str]]] = [
    ("source-tree path", re.compile(r"src/specflow/")),
    ("SpecFlow docs/ file", re.compile(r"(?<![\w.-])docs/(?:" + "|".join(map(re.escape, _REPO_DOCS)) + r")\b")),
    ("dogfood .claude/skills mirror path", re.compile(r"\.claude/skills/specflow-[\w-]+")),
    ("legacy D-NN decision id", re.compile(r"(?<![\w-])D-\d+\b")),
]

# Per-skill line budgets: core skills are lean routers, pack skills carry a
# protocol. A named exception records a current offender at its present size
# (a ceiling, so it cannot grow); trim it and delete the entry.
CORE_BUDGET = 120
PACK_BUDGET = 300
BUDGET_EXCEPTIONS: dict[str, int] = {
    "src/specflow/templates/skills/shared/specflow-adapter/SKILL.md": 176,
    "src/specflow/templates/skills/shared/specflow-init/SKILL.md": 157,
    "src/specflow/templates/skills/shared/specflow-pack-author/SKILL.md": 187,
    "src/specflow/packs/autoresearch/skills/specflow-autoresearch/SKILL.md": 383,
}


def _shipped_files():
    for root in SHIPPED_ROOTS:
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix in TEXT_SUFFIXES and "__pycache__" not in path.parts:
                yield path


def lint_text(text: str) -> list[tuple[int, str, str]]:
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        scrubbed = _URL.sub("", line)
        for label, rule in RULES:
            for m in rule.finditer(scrubbed):
                hits.append((lineno, label, m.group(0)))
    return hits


def test_repo_docs_known():
    assert "authoring-a-pack.md" in _REPO_DOCS and "decisions.md" in _REPO_DOCS


def test_shipped_text_has_no_repository_internal_references():
    failures = []
    scanned = 0
    for path in _shipped_files():
        scanned += 1
        for lineno, label, match in lint_text(path.read_text(encoding="utf-8")):
            failures.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {label}: {match!r}")
    assert scanned > 50
    assert not failures, "\n".join(failures)


def test_seeded_references_fail():
    seeded = "\n".join([
        "See src/specflow/lib/lint.py for details.",
        "Read docs/authoring-a-pack.md first.",
        "Mirrors .claude/skills/specflow-plan/SKILL.md.",
        "Per D-19 we adopt incrementally.",
        # Allowed: the user's docs tree, platform dirs, GitHub URLs, DEC ids.
        'roots: ["docs/"] and docs/adr/0003.md; OpenCode reads `.claude/skills`.',
        "https://github.com/Longhuiberkeley/specflow/blob/main/docs/lifecycle.md",
        "Superseded by DEC-019 and CKL-D-12 style keys.",
    ])
    labels = [label for _, label, _ in lint_text(seeded)]
    assert labels == [
        "source-tree path",
        "SpecFlow docs/ file",
        "dogfood .claude/skills mirror path",
        "legacy D-NN decision id",
    ], lint_text(seeded)


def _skill_files():
    core = sorted((SRC / "templates" / "skills" / "shared").glob("*/SKILL.md"))
    packs = sorted((SRC / "packs").glob("*/skills/*/SKILL.md"))
    return [(p, CORE_BUDGET) for p in core] + [(p, PACK_BUDGET) for p in packs]


def check_budgets(files, exceptions) -> list[str]:
    failures = []
    for path, budget in files:
        rel = str(path.relative_to(REPO_ROOT))
        n = len(path.read_text(encoding="utf-8").splitlines())
        limit = exceptions.get(rel, budget)
        if n > limit:
            kind = "exception ceiling" if rel in exceptions else "budget"
            failures.append(f"{rel}: {n} lines > {kind} {limit}")
    return failures


def test_skill_line_budgets():
    files = _skill_files()
    assert len(files) >= 12
    failures = check_budgets(files, BUDGET_EXCEPTIONS)
    assert not failures, "\n".join(failures)


def test_budget_exceptions_are_live():
    """An exception must name an existing skill that still exceeds its
    default budget; a trimmed skill loses its exception."""
    budgets = {str(p.relative_to(REPO_ROOT)): b for p, b in _skill_files()}
    for rel in BUDGET_EXCEPTIONS:
        assert rel in budgets, f"stale exception: {rel}"
        n = len((REPO_ROOT / rel).read_text(encoding="utf-8").splitlines())
        assert n > budgets[rel], f"{rel} is within budget ({n} lines); drop its exception"


def test_seeded_budget_violation_fails():
    start = SRC / "templates" / "skills" / "shared" / "specflow-start" / "SKILL.md"
    failures = check_budgets([(start, 10)], {})
    assert failures and "> budget 10" in failures[0]
    # A named exception lifts the ceiling for that file only.
    assert check_budgets([(start, 10)], {str(start.relative_to(REPO_ROOT)): 10_000}) == []
