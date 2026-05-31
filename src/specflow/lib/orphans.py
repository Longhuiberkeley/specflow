"""Orphan code detection — find source files not referenced by any SpecFlow artifact.

Provides:
  find_orphan_code() — scan project for unreferenced source files
  retro_link()      — create a STORY to retroactively cover orphan files
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from specflow.lib.artifacts import discover_artifacts


# Directories and patterns to exclude from orphan scanning
EXCLUDE_DIRS: set[str] = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    "node_modules", ".next", "dist", "build", ".specflow",
    "_specflow", ".claude", ".cursor", ".windsurf", ".codex",
    ".opencode", ".agents", ".roo", ".qwen", ".kiro", ".kilocode",
    ".trae", ".github", ".husky", ".clinerules",
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


def _is_source_file(filepath: Path) -> bool:
    """Check if a file is a trackable source file (not generated, not config)."""
    suffix = filepath.suffix.lower()
    if suffix not in SOURCE_EXTENSIONS:
        return False
    for pattern in EXCLUDE_PATTERNS:
        if filepath.match(pattern):
            return False
    # Skip common generated/config file names
    name = filepath.name.lower()
    if name in ("dockerfile", "makefile", "docker-compose.yml", ".gitignore",
                 ".dockerignore", ".editorconfig", ".prettierrc", ".eslintrc"):
        return False
    return True


def _scan_source_files(root: Path) -> list[Path]:
    """Scan project root for all source files, excluding known non-source dirs."""
    source_files: list[Path] = []
    for entry in root.rglob("*"):
        if not entry.is_file():
            # Prune excluded directories
            if entry.is_dir() and entry.name in EXCLUDE_DIRS:
                # Don't descend into excluded dirs
                pass  # rglob still descends; we filter below
            continue
        # Check if any parent is an excluded directory
        parts = set(p.name for p in entry.parents if p != root)
        if parts & EXCLUDE_DIRS:
            continue
        if _is_source_file(entry):
            source_files.append(entry)
    return source_files


def _collect_referenced_files(artifacts, root: Path) -> set[Path]:
    """Collect all output_files and body-referenced files from artifacts."""
    referenced: set[Path] = set()
    for art in artifacts:
        if art.type not in ("story", "requirement"):
            continue
        # Check output_files frontmatter field
        output_files = art.frontmatter.get("output_files")
        if output_files and isinstance(output_files, list):
            for f in output_files:
                if isinstance(f, str):
                    resolved = (root / f).resolve()
                    if resolved.exists():
                        referenced.add(resolved)
        # Check for file paths mentioned in the body
        body = art.body or ""
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("`") and "`" in line[1:]:
                # Backtick-quoted file path
                fname = line.split("`")[1]
                candidate = (root / fname).resolve()
                if candidate.exists() and candidate.is_file():
                    referenced.add(candidate)
    return referenced


def find_orphan_code(root: Path) -> dict:
    """Find source code files not referenced by any STORY or REQ artifact.

    Returns:
        dict with keys:
          orphan_files: list of Path objects (unreferenced source files)
          referenced_files: count of referenced source files
          total_source_files: total source files scanned
    """
    root = Path(root).resolve()
    artifacts = discover_artifacts(root)
    source_files = _scan_source_files(root)
    referenced = _collect_referenced_files(artifacts, root)

    orphans = [f for f in source_files if f.resolve() not in referenced]

    return {
        "orphan_files": orphans,
        "referenced_count": len(referenced),
        "total_count": len(source_files),
    }


def retro_link(root: Path, filepath: str, story_id: str) -> bool:
    """Retroactively link an orphan file to an existing STORY's output_files.

    Args:
        root: Project root
        filepath: Path to the orphan source file (relative or absolute)
        story_id: STORY artifact ID (e.g., "STORY-042")

    Returns:
        True if successful, False if STORY not found or file doesn't exist
    """
    root = root.resolve()
    story_path = root / "_specflow" / "work" / "stories" / f"{story_id}.md"
    if not story_path.exists():
        return False

    file_path = Path(filepath)
    if file_path.is_absolute():
        rel_path = file_path.relative_to(root)
    else:
        rel_path = file_path
        file_path = (root / filepath).resolve()

    if not file_path.exists():
        return False

    # Read existing STORY frontmatter
    text = story_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return False
    end = text.find("---", 3)
    if end == -1:
        return False

    fm = yaml.safe_load(text[3:end]) or {}
    output_files = fm.get("output_files") or []
    if not isinstance(output_files, list):
        output_files = []

    rel_str = str(rel_path).replace("\\", "/")
    if rel_str not in output_files:
        output_files.append(rel_str)
        fm["output_files"] = output_files

    # Rewrite frontmatter
    import io
    new_fm = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    new_text = f"---\n{new_fm}---{text[end+3:]}"
    story_path.write_text(new_text, encoding="utf-8")

    return True
