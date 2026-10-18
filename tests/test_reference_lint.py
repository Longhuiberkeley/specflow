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


# --- STORY-742: skill-catalog backstop pins (REQ-042 R2/R4) ----------------
# Shipped skills install side by side (`<skills-dir>/<skill>/`), core and pack
# alike, so cross-skill citations (`../specflow-references/...`) and routes
# (`/specflow-<name>`) resolve against the union of both trees.

CORE_SKILLS_DIR = SRC / "templates" / "skills" / "shared"
DESCRIPTION_MAX = 160
_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_REF_CITE = re.compile(r"(?<![\w./-])((?:\.\./)*(?:specflow-[\w-]+/)?references/[^\s`'\")\]]+)")
_ROUTE = re.compile(r"(?<![\w/.-])/specflow-([a-z][\w-]*)")
_PLACEHOLDER = set("<>{}*")


def _skill_dirs() -> dict[str, Path]:
    """Installed skill name -> source dir (core + pack, including the
    references-only `specflow-references` dir that holds shared references)."""
    dirs = {p.name: p for p in sorted(CORE_SKILLS_DIR.iterdir()) if p.is_dir()}
    for p in sorted((SRC / "packs").glob("*/skills/*")):
        if p.is_dir():
            dirs[p.name] = p
    return dirs


def _skill_text_files(skill_dirs: dict[str, Path]) -> list[tuple[Path, Path]]:
    """(file, its skill dir) for every SKILL.md and references/**/*.md."""
    out = []
    for skill_dir in skill_dirs.values():
        for path in sorted(skill_dir.glob("SKILL.md")) + sorted(skill_dir.glob("references/**/*.md")):
            out.append((path, skill_dir))
    return out


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def check_descriptions(skill_md_files) -> list[str]:
    """Frontmatter `description` is one line, <= DESCRIPTION_MAX characters
    (unquoted), and carries no "NOT for" negation."""
    failures = []
    for path in skill_md_files:
        m = _FRONTMATTER.match(path.read_text(encoding="utf-8"))
        lines = m.group(1).splitlines() if m else []
        idx = next((i for i, ln in enumerate(lines) if ln.startswith("description:")), None)
        if idx is None:
            failures.append(f"{_rel(path)}: no frontmatter description")
            continue
        value = lines[idx][len("description:"):].strip()
        continued = idx + 1 < len(lines) and lines[idx + 1][:1] in (" ", "\t")
        if value[:1] in (">", "|") or continued or not value:
            failures.append(f"{_rel(path)}: description is not a single line")
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if len(value) > DESCRIPTION_MAX:
            failures.append(f"{_rel(path)}: description is {len(value)} chars > {DESCRIPTION_MAX}")
        if re.search(r"\bnot for\b", value, re.IGNORECASE):
            failures.append(f"{_rel(path)}: description carries a 'NOT for' negation")
    return failures


def _resolves(cite: str, path: Path, skill_dir: Path, skill_dirs: dict[str, Path]) -> bool:
    # File-relative (`../../specflow-execute/...` from inside references/).
    if (path.parent / cite).is_file():
        return True
    # Skill-root-relative: bare `references/x.md` from anywhere in the skill,
    # and `../<skill>/...` resolved through the installed (flattened) layout.
    parts = Path(cite).parts
    if parts and parts[0] == "references":
        return (skill_dir / cite).is_file()
    if len(parts) > 2 and parts[0] == ".." and parts[1] in skill_dirs:
        return (skill_dirs[parts[1]].joinpath(*parts[2:])).is_file()
    # `../../<skill>/...` from a references file, via the installed layout.
    if path.parent.name == "references" and len(parts) > 3 and parts[:2] == ("..", "..") and parts[2] in skill_dirs:
        return (skill_dirs[parts[2]].joinpath(*parts[3:])).is_file()
    return False


def check_reference_paths(files, skill_dirs: dict[str, Path]) -> list[str]:
    """Every cited `references/...` path resolves to an existing file."""
    failures = []
    for path, skill_dir in files:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for m in _REF_CITE.finditer(_URL.sub("", line)):
                cite = m.group(1).rstrip(".,;:")
                if _PLACEHOLDER & set(cite) or not cite.endswith(".md"):
                    continue
                if not _resolves(cite, path, skill_dir, skill_dirs):
                    failures.append(f"{_rel(path)}:{lineno}: unresolved reference {cite!r}")
    return failures


def check_routes(files, known: set[str]) -> list[str]:
    """Every `/specflow-<name>` route names an invocable shipped skill."""
    failures = []
    for path in files:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for m in _ROUTE.finditer(_URL.sub("", line)):
                name = "specflow-" + m.group(1).rstrip("-")
                if name not in known:
                    failures.append(f"{_rel(path)}:{lineno}: unknown route '/{name}'")
    return failures


def _invocable(skill_dirs: dict[str, Path]) -> set[str]:
    return {name for name, d in skill_dirs.items() if (d / "SKILL.md").is_file()}


def test_skill_descriptions_are_single_short_lines():
    files = [p for p, _ in _skill_files()]
    assert len(files) >= 15
    failures = check_descriptions(files)
    assert not failures, "\n".join(failures)


def test_cited_reference_paths_resolve():
    skill_dirs = _skill_dirs()
    files = _skill_text_files(skill_dirs)
    assert len(files) > 50
    failures = check_reference_paths(files, skill_dirs)
    assert not failures, "\n".join(failures)


def test_skill_routes_resolve():
    skill_dirs = _skill_dirs()
    known = _invocable(skill_dirs)
    assert {"specflow-start", "specflow-adopt", "specflow-autoresearch"} <= known
    assert "specflow-references" not in known  # reference-only, not invocable
    failures = check_routes([p for p, _ in _skill_text_files(skill_dirs)], known)
    assert not failures, "\n".join(failures)


def test_core_skill_count_pinned():
    # A 14th core skill directory (or a 13th invocable core skill) is a
    # conscious catalog change: update this pin together with the always-on
    # catalog, the Tier-1 table (test_cli_reference_coverage.py) and the
    # "13 skill directories" lines in the getting-started/commands docs.
    dirs = sorted(p.name for p in CORE_SKILLS_DIR.iterdir() if p.is_dir())
    assert len(dirs) == 13, dirs
    with_skill_md = [d for d in dirs if (CORE_SKILLS_DIR / d / "SKILL.md").is_file()]
    assert len(with_skill_md) == 12, with_skill_md
    assert set(dirs) - set(with_skill_md) == {"specflow-references"}


def _write_skill(root: Path, name: str, frontmatter: str, body: str = "") -> Path:
    d = root / name
    d.mkdir(parents=True)
    p = d / "SKILL.md"
    p.write_text(f"---\nname: {name}\n{frontmatter}\n---\n\n{body}\n", encoding="utf-8")
    return p


def test_seeded_bad_descriptions_fail(tmp_path):
    long_desc = "x" * (DESCRIPTION_MAX + 1)
    multi = _write_skill(tmp_path, "specflow-multi", "description: >\n  Folded\n  text")
    over = _write_skill(tmp_path, "specflow-over", f'description: "{long_desc}"')
    neg = _write_skill(tmp_path, "specflow-neg", 'description: "Plan work. NOT for audits."')
    ok = _write_skill(tmp_path, "specflow-ok", 'description: "Plan work."',
                      body='description: "{body text is not frontmatter}"')
    failures = check_descriptions([multi, over, neg, ok])
    assert len(failures) == 3, failures
    assert "specflow-multi" in failures[0] and "single line" in failures[0]
    assert "specflow-over" in failures[1] and f"> {DESCRIPTION_MAX}" in failures[1]
    assert "specflow-neg" in failures[2] and "NOT for" in failures[2]


def test_seeded_dead_reference_fails(tmp_path):
    skill = _write_skill(tmp_path, "specflow-a", 'description: "A."',
                         body="See `references/nope.md` and `references/ok.md`, "
                              "`references/<type>.md`, https://x.io/references/gone.md.")
    (skill.parent / "references").mkdir()
    (skill.parent / "references" / "ok.md").write_text("ok\n", encoding="utf-8")
    failures = check_reference_paths([(skill, skill.parent)], {"specflow-a": skill.parent})
    assert len(failures) == 1, failures
    assert "specflow-a/SKILL.md" in failures[0] and "references/nope.md" in failures[0]


def test_seeded_unknown_route_fails(tmp_path):
    skill = _write_skill(tmp_path, "specflow-a", 'description: "A."',
                         body="Route to `/specflow-a` or /specflow-nonexistent; "
                              "path .claude/skills/specflow-ghost is not a route.")
    failures = check_routes([skill], {"specflow-a"})
    assert len(failures) == 1, failures
    assert "SKILL.md" in failures[0] and "/specflow-nonexistent" in failures[0]
