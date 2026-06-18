"""Orphan code detection — find source files not referenced by any SpecFlow artifact.

Provides:
  find_orphan_code() — scan project for unreferenced source files
  retro_link()       — retroactively link an orphan file to an artifact's output_files

Code-linking model (D-20): `output_files` may live on STORY (forward action),
ARCH (component / adoption custody), DDD (detailed-design), or REQ. The orphan
meter credits all four. Glob patterns in `output_files` are expanded via
`lib.files.expand_output_files` so a single ARCH can cover a whole package.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import files as files_lib


# Artifact types whose `output_files` count as "referencing" code. STORY covers
# forward action; ARCH/DDD cover adoption custody of existing components; REQ
# is kept for backward compatibility (its schema doesn't bless output_files,
# but some projects set it and we don't want to orphan their code on upgrade).
REFERENCING_TYPES: set[str] = {"story", "requirement", "architecture", "detailed-design"}


def find_orphan_code(root: Path) -> dict:
    """Find source code files not referenced by any STORY/REQ/ARCH/DDD artifact.

    A file is "referenced" if it appears in any referencing artifact's
    `output_files` (literal path OR glob match) or is cited via a backtick-quoted
    path at the start of a body line (best-effort heuristic).

    Returns:
        dict with keys:
          orphan_files: list of Path objects (unreferenced source files)
          referenced_count: count of referenced source files
          total_count: total source files scanned
    """
    root = Path(root).resolve()
    artifacts = art_lib.discover_artifacts(root)
    source_files = files_lib.scan_source_files(root)
    source_set = {f.resolve() for f in source_files}
    referenced = _collect_referenced_files(artifacts, root)

    orphans = [f for f in source_files if f.resolve() not in referenced]

    # Keep numerator on the same scope as the denominator: a declared output_file
    # outside the scanned scope must not push coverage past 100%.
    referenced_in_scope = referenced & source_set

    return {
        "orphan_files": orphans,
        "referenced_count": len(referenced_in_scope),
        "total_count": len(source_files),
    }


def _collect_referenced_files(artifacts, root: Path) -> set[Path]:
    """Collect all output_files (frontmatter) and body-referenced files from artifacts.

    Globs in `output_files` are expanded via `expand_output_files`. Only the
    four referencing types contribute (see REFERENCING_TYPES).
    """
    referenced: set[Path] = set()
    for art in artifacts:
        if art.type not in REFERENCING_TYPES:
            continue
        expanded = files_lib.expand_output_files(root, art.frontmatter.get("output_files"))
        referenced.update(expanded)
        # Body heuristic: backtick-quoted paths at line start. Best-effort; the
        # primary mechanism is the frontmatter output_files field above.
        body = art.body or ""
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("`") and "`" in line[1:]:
                fname = line.split("`")[1]
                candidate = (root / fname).resolve()
                if candidate.exists() and candidate.is_file():
                    referenced.add(candidate)
    return referenced


def retro_link(root: Path, filepath: str, target_id: str) -> bool:
    """Retroactively link an orphan file to an artifact's output_files.

    Args:
        root: Project root
        filepath: Path to the orphan source file (relative or absolute)
        target_id: Artifact ID (e.g. "ARCH-003", "STORY-042", "DDD-007").
            The artifact's directory is resolved from its prefix, so any
            artifact type that owns output_files can be a target.

    Returns:
        True if successful, False if target not found or file doesn't exist
    """
    root = Path(root).resolve()

    # Resolve the target artifact's path from its ID prefix.
    target_path = art_lib.resolve_link_target(root, target_id)
    if target_path is None or not Path(target_path).exists():
        # Fall back to the legacy STORY-only path for any caller that passed a
        # bare STORY id we couldn't resolve through the link graph.
        legacy = root / "_specflow" / "work" / "stories" / f"{target_id}.md"
        if legacy.exists():
            target_path = legacy
        else:
            return False
    target_path = Path(target_path)

    file_path = Path(filepath)
    if file_path.is_absolute():
        try:
            rel_path = file_path.relative_to(root)
        except ValueError:
            return False
    else:
        rel_path = file_path
        file_path = (root / filepath).resolve()

    if not file_path.exists():
        return False

    text = target_path.read_text(encoding="utf-8")
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

    new_fm = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    new_text = f"---\n{new_fm}---{text[end+3:]}"
    target_path.write_text(new_text, encoding="utf-8")

    return True
