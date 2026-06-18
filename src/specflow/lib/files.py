"""Source-file scanning + output_files expansion.

Two concerns live here:

1. **What counts as a source file.** `EXCLUDE_DIRS`, `EXCLUDE_PATTERNS`,
   `SOURCE_EXTENSIONS`, `_is_source_file`, and `scan_source_files` define the
   set of files SpecFlow considers "code" for coverage/orphan purposes. These
   used to live in `orphans.py`; they're broader than orphan detection (the
   adoption completeness views, source-drift, and reconcile all need the same
   definition), so they were promoted here. `orphans.py` is now a consumer.

2. **Resolving `output_files`.** Entries may be literal relative paths
   ("src/auth/login.py") or glob patterns
   ("src/main/java/com/acme/payments/**/*.java"). Historically each consumer
   (orphan detection, reconcile, source-drift lint) re-implemented literal-only
   resolution and silently *skipped* globs — making glob coverage invisible.
   `expand_output_files` is the single source of truth so globs are honored
   uniformly everywhere.

Filter rule of thumb: the same files we'd *scan* as source are the same files
we'll *credit* as referenced — no divergence between the denominator and
numerator of coverage.
"""

from __future__ import annotations

from pathlib import Path


# Directories and patterns to exclude from source scanning.
EXCLUDE_DIRS: set[str] = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    "node_modules", ".next", "dist", "build", ".specflow",
    "_specflow", ".claude", ".cursor", ".windsurf", ".codex",
    ".opencode", ".agents", ".roo", ".qwen", ".kiro", ".kilocode",
    ".trae", ".github", ".husky", ".clinerules", ".cline",
    ".gemini", ".junie",
}

EXCLUDE_PATTERNS: list[str] = [
    "*.pyc", "*.pyo", "*.so", "*.o", "*.a", "*.dylib", "*.dll",
    "*.class", "*.jar", "*.war", "*.egg", "*.whl",
    "*.min.js", "*.min.css", "*.map",
    "package-lock.json", "yarn.lock", "uv.lock", "poetry.lock",
    "*.log", "*.tmp", "*.swp", "*.swo", "*~",
]

SOURCE_EXTENSIONS: set[str] = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
    ".c", ".cpp", ".h", ".hpp", ".rb", ".php", ".swift", ".kt",
    ".scala", ".r", ".R", ".sql", ".sh", ".bash", ".zsh",
    ".yaml", ".yml", ".toml", ".json", ".xml", ".md", ".mdc",
    ".css", ".scss", ".less", ".html", ".vue", ".svelte",
    ".tf", ".dockerfile", ".proto", ".graphql",
}

GLOB_CHARS = set("*?[")

SOURCE_FP_FILE = ".specflow/source-fingerprints.yaml"


def _path_is_under_excluded_dir(rel: Path) -> bool:
    """True if any parent of `rel` (below root) is an excluded directory."""
    return any(part in EXCLUDE_DIRS for part in rel.parts[:-1])


def _normalize_extensions(extra: list[str] | None) -> set[str]:
    """Normalize a config `extensions` list to lowercased, dot-prefixed suffixes."""
    out: set[str] = set()
    for e in extra or []:
        if not isinstance(e, str) or not e.strip():
            continue
        e = e.strip().lower()
        out.add(e if e.startswith(".") else "." + e)
    return out


def is_source_file(filepath: Path, extra_extensions: list[str] | None = None) -> bool:
    """Check if a file is a trackable source file (not generated, not config).

    `extra_extensions` (from `source_scope.extensions` config) additively extends
    the built-in `SOURCE_EXTENSIONS` so a project can declare uncommon code types
    without an explicit include allowlist.
    """
    exts = SOURCE_EXTENSIONS | _normalize_extensions(extra_extensions)
    suffix = filepath.suffix.lower()
    if suffix not in exts:
        return False
    for pattern in EXCLUDE_PATTERNS:
        if filepath.match(pattern):
            return False
    name = filepath.name.lower()
    if name in ("dockerfile", "makefile", "docker-compose.yml", ".gitignore",
                ".dockerignore", ".editorconfig", ".prettierrc", ".eslintrc"):
        return False
    return True


# Back-compat alias: `orphans._is_source_file` was the internal name. Keep the
# underscore form working for any stray import without proliferating two APIs.
_is_source_file = is_source_file


def _git_candidate_files(root: Path) -> list[Path] | None:
    """Files git considers part of the project: tracked ∪ untracked-not-ignored.

    Returns None when `root` is not a git work tree or git fails, signalling the
    caller to fall back to a plain filesystem walk. When it returns a list, the
    result inherently respects `.gitignore` (ignored paths never appear), so a
    gitignored `data/raw/` tree drops out of the source scope for free while
    brand-new uncommitted code still counts.
    """
    from specflow.lib import git_utils

    if not git_utils.is_git_repo(root):
        return None
    tracked = git_utils._run_git(root, ["ls-files", "-z"])
    if tracked.returncode != 0:
        return None
    others = git_utils._run_git(root, ["ls-files", "--others", "--exclude-standard", "-z"])

    rels: set[str] = set()
    for proc in (tracked, others):
        if proc.returncode != 0:
            continue
        for part in proc.stdout.split("\0"):
            if part:
                rels.add(part)

    files: list[Path] = []
    for rel in rels:
        p = root / rel
        if p.is_file():
            files.append(p)
    return files


def _pattern_variants(pat: str) -> list[str]:
    """Expand a user scope pattern into glob variants that reliably match files.

    `Path.glob`'s `**` matches directories only, so a natural `data/**` (or the
    gitignore-style `data/`) matches no files on its own. We add a recursive
    files variant so the common "everything under this dir" intent works, while
    leaving precise patterns like `src/**/*.py` untouched.
    """
    pat = pat.strip()
    if pat.endswith("/"):
        base = pat.rstrip("/")
        return [base + "/**/*"] if base else []
    if pat.endswith("/**"):
        return [pat, pat + "/*"]
    return [pat]


def _scope_glob_set(root: Path, patterns: list[str] | None) -> set[Path]:
    """Resolve a list of globs (config `include`/`exclude`) to a set of files.

    Built on the same `Path.glob` engine as `expand_output_files` so precise
    patterns like `src/**/*.py` behave identically here and in `output_files`
    resolution; `_pattern_variants` additionally rescues directory-style
    patterns (`data/**`, `data/`).
    """
    out: set[Path] = set()
    root = Path(root).resolve()
    for pat in patterns or []:
        if not isinstance(pat, str) or not pat.strip():
            continue
        for variant in _pattern_variants(pat):
            for match in root.glob(variant):
                if match.is_file():
                    out.add(match.resolve())
    return out


def scan_source_files(root: Path) -> list[Path]:
    """Scan project root for the files SpecFlow treats as source ("code").

    The candidate set respects `.gitignore` automatically when `root` is a git
    work tree (via `git ls-files`), falling back to an `rglob` + `EXCLUDE_DIRS`
    walk otherwise. An optional `source_scope` block in `.specflow/config.yaml`
    refines the set:

      - `include`: glob allowlist. If present, only matching files count, and
        matching files BYPASS the extension heuristic (an explicit declaration
        is authoritative — honors uncommon/invented code types).
      - `extensions`: additive suffixes applied to the extension heuristic when
        no `include` allowlist is set.
      - `exclude`: glob denylist, always subtracted last (covers committed
        non-code that `.gitignore` doesn't hide, e.g. a tracked `data/` tree).

    With no config and no git, behavior is identical to the historical walk.
    """
    from specflow.lib.config import read_config

    root = Path(root)
    scope = (read_config(root).get("source_scope") or {})
    include = scope.get("include") or []
    exclude = scope.get("exclude") or []
    extra_exts = scope.get("extensions") or []

    candidates = _git_candidate_files(root)
    if candidates is None:
        # rglob traverses ALL directories; we prune by parent-name check below.
        candidates = [e for e in root.rglob("*") if e.is_file()]

    include_set = _scope_glob_set(root, include) if include else None
    exclude_set = _scope_glob_set(root, exclude)

    source_files: list[Path] = []
    for entry in candidates:
        try:
            rel = entry.relative_to(root)
        except ValueError:
            continue
        # EXCLUDE_DIRS backstop applies even to git-listed files (e.g. a
        # committed node_modules/).
        if _path_is_under_excluded_dir(rel):
            continue
        resolved = entry.resolve()
        if include_set is not None:
            if resolved not in include_set:
                continue
            # allowlist match: authoritative, skip extension heuristic
        elif not is_source_file(entry, extra_exts):
            continue
        if resolved in exclude_set:
            continue
        source_files.append(entry)
    return source_files


def describe_source_scope(root: Path) -> dict:
    """Summarize the active source scope for display (see `adopt status`).

    Returns {include, exclude, extensions, gitignore_respected}.
    """
    from specflow.lib import git_utils
    from specflow.lib.config import read_config

    scope = (read_config(root).get("source_scope") or {})
    return {
        "include": scope.get("include") or [],
        "exclude": scope.get("exclude") or [],
        "extensions": scope.get("extensions") or [],
        "gitignore_respected": git_utils.is_git_repo(root),
    }


def expand_output_files(root: Path, entries: list[str] | None) -> set[Path]:
    """Expand an artifact's `output_files` entries into concrete existing files.

    Args:
        root: Project root that relative paths/globs resolve against.
        entries: The `output_files` frontmatter value. Tolerates None / non-list
            gracefully (returns an empty set).

    Returns:
        Set of resolved, existing file Paths (absolute). Globs are expanded via
        `Path.glob(recursive=True)` (so `**` works). Literal entries that don't
        exist resolve to nothing. Expanded glob results are filtered through the
        same exclude rules as source scanning so generated/config files inside
        a globbed package aren't credited.

    Literal entries are credited even if they'd fail the source-file filter:
    a user who explicitly named a config/doc file as an output_file meant it.
    Globs are filtered; literals are honored.
    """
    root = Path(root).resolve()
    resolved: set[Path] = set()
    if not entries or not isinstance(entries, list):
        return resolved

    for entry in entries:
        if not isinstance(entry, str) or not entry.strip():
            continue
        is_glob = any(c in entry for c in GLOB_CHARS)
        if is_glob:
            for match in root.glob(entry):
                if not match.is_file():
                    continue
                try:
                    rel = match.relative_to(root)
                except ValueError:
                    continue
                if _path_is_under_excluded_dir(rel):
                    continue
                if not is_source_file(rel):
                    continue
                resolved.add(match.resolve())
        else:
            candidate = (root / entry).resolve()
            if candidate.is_file():
                resolved.add(candidate)
    return resolved


def literal_missing(root: Path, entries: list[str] | None) -> list[str]:
    """Return the literal (non-glob) entries that don't exist on disk.

    Globs never appear here — a glob with zero matches is ambiguous (could mean
    "package deleted" or "pattern typo") and is surfaced separately by callers
    that care. Only hard, named-file misses are reported, since those are
    unambiguous drift signals (a declared output file is gone).
    """
    root = Path(root).resolve()
    missing: list[str] = []
    if not entries or not isinstance(entries, list):
        return missing
    for entry in entries:
        if not isinstance(entry, str) or not entry.strip():
            continue
        if any(c in entry for c in GLOB_CHARS):
            continue
        if not (root / entry).resolve().exists():
            missing.append(entry)
    return missing


def glob_entries(entries: list[str] | None) -> list[str]:
    """Return just the glob entries from an output_files list (for reporting)."""
    if not entries or not isinstance(entries, list):
        return []
    return [e for e in entries if isinstance(e, str) and any(c in e for c in GLOB_CHARS)]
