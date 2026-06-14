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


def is_source_file(filepath: Path) -> bool:
    """Check if a file is a trackable source file (not generated, not config)."""
    suffix = filepath.suffix.lower()
    if suffix not in SOURCE_EXTENSIONS:
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


def scan_source_files(root: Path) -> list[Path]:
    """Scan project root for all source files, excluding known non-source dirs.

    Note: `rglob` traverses ALL directories (including excluded ones); we prune
    by parent-name check. Acceptable for typical SpecFlow project sizes. For
    very large projects with deep node_modules trees, switching to os.walk with
    selective pruning would help.
    """
    root = Path(root)
    source_files: list[Path] = []
    for entry in root.rglob("*"):
        if not entry.is_file():
            continue
        try:
            rel = entry.relative_to(root)
        except ValueError:
            continue
        if _path_is_under_excluded_dir(rel):
            continue
        if is_source_file(entry):
            source_files.append(entry)
    return source_files


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
