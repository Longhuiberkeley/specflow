"""Directory and file scaffolding for SpecFlow init."""

import shutil
from pathlib import Path
from typing import Any

import yaml

from specflow.lib import platform

# Spec directories under _specflow/
SPEC_DIRS = [
    "specs/requirements",
    "specs/architecture",
    "specs/detailed-design",
    "specs/unit-tests",
    "specs/integration-tests",
    "specs/qualification-tests",
    "specs/reviews",
    "work/stories",
    "work/spikes",
    "work/decisions",
    "work/defects",
]

# Internal directories under .specflow/
INTERNAL_DIRS = [
    "schema",
    "impact-log",
    "checklist-log",
    "baselines",
    "locks",
    "standards",
    "checklists/phase-gates",
    "checklists/in-process",
    "checklists/readiness",
    "checklists/review",
    "checklists/shared",
    "checklists/learned",
    "checklists/domain",
]

_INDEX_STUB = {"artifacts": {}, "next_id": 1}


def create_spec_dirs(root: Path) -> None:
    """Create _specflow/ directory structure with _index.yaml stubs."""
    for rel in SPEC_DIRS:
        d = root / "_specflow" / rel
        d.mkdir(parents=True, exist_ok=True)
        index = d / "_index.yaml"
        if not index.exists():
            index.write_text(yaml.dump(_INDEX_STUB, default_flow_style=False))


def create_internal_dirs(root: Path, template_dir: Path, *, overwrite_schemas: bool = False) -> None:
    """Create .specflow/ internal directories and copy schemas.

    Args:
        root: Project root path.
        template_dir: Package templates directory.
        overwrite_schemas: If True, overwrite existing schemas with fresh copies
            from the package. Used by ``--force`` re-init.
    """
    specflow = root / ".specflow"
    for d in INTERNAL_DIRS:
        (specflow / d).mkdir(parents=True, exist_ok=True)

    schema_dst = specflow / "schema"
    schema_src = template_dir / "schemas"
    if schema_src.exists():
        schema_dst.mkdir(parents=True, exist_ok=True)
        for schema_file in schema_src.glob("*.yaml"):
            dst_file = schema_dst / schema_file.name
            if overwrite_schemas or not dst_file.exists():
                shutil.copy2(str(schema_file), str(dst_file))


def copy_adapters_config(root: Path, template_dir: Path) -> None:
    """Copy the default adapters.yaml template into .specflow/.

    Only copies if the destination doesn't already exist (preserves user edits).
    """
    src = template_dir / "adapters.yaml"
    dst = root / ".specflow" / "adapters.yaml"
    if not src.exists():
        return
    if dst.exists():
        return
    shutil.copy2(str(src), str(dst))


def copy_checklists(root: Path, template_dir: Path) -> None:
    """Copy checklist templates from package to project instance.

    Copies from src/specflow/templates/checklists/ to .specflow/checklists/.
    Only copies if the destination file doesn't already exist (preserves user edits).
    """
    checklists_src = template_dir / "checklists"
    checklists_dst = root / ".specflow" / "checklists"

    if not checklists_src.exists():
        return

    for category in ("phase-gates", "in-process", "readiness", "review", "shared", "domain"):
        src_cat = checklists_src / category
        dst_cat = checklists_dst / category
        if not src_cat.exists():
            continue

        dst_cat.mkdir(parents=True, exist_ok=True)
        for yaml_file in src_cat.glob("*.yaml"):
            dst_file = dst_cat / yaml_file.name
            if not dst_file.exists():
                shutil.copy2(str(yaml_file), str(dst_file))


def apply_pack(root: Path, pack_name: str, packs_dir: Path) -> dict[str, Any]:
    """Apply a standards pack from packs_dir/<pack_name>/ to the project.

    Copies schemas, checklists, and standards into the project's .specflow/
    internals, and creates any new _specflow/ artifact directories declared in
    the pack manifest. Existing destination files are preserved (not overwritten).

    Returns {"ok": True, "pack": ..., "types_added": [...], "standards_added": [...]}
    or {"ok": False, "error": str} on failure.
    """
    pack_root = packs_dir / pack_name
    manifest_path = pack_root / "pack.yaml"
    if not manifest_path.exists():
        return {
            "ok": False,
            "error": f"Pack '{pack_name}' not found at {pack_root}",
        }

    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "error": f"Failed to parse {manifest_path}: {e}"}
    if not isinstance(manifest, dict):
        return {"ok": False, "error": f"Invalid manifest at {manifest_path}"}

    specflow_internal = root / ".specflow"
    types_added: list[str] = []
    standards_added: list[str] = []

    # 1. Copy schemas → .specflow/schema/ (no overwrite)
    src_schemas = pack_root / "schemas"
    if src_schemas.exists():
        dst_schemas = specflow_internal / "schema"
        dst_schemas.mkdir(parents=True, exist_ok=True)
        for yaml_file in src_schemas.glob("*.yaml"):
            dst_file = dst_schemas / yaml_file.name
            if not dst_file.exists():
                shutil.copy2(str(yaml_file), str(dst_file))

    # 2. Create _specflow/ directories declared in the manifest
    for rel in manifest.get("adds_directories", []) or []:
        d = root / "_specflow" / rel
        d.mkdir(parents=True, exist_ok=True)
        index = d / "_index.yaml"
        if not index.exists():
            index.write_text(yaml.dump(_INDEX_STUB, default_flow_style=False))

    # 3. Copy checklists (any subdirectory structure) → .specflow/checklists/
    src_checklists = pack_root / "checklists"
    if src_checklists.exists():
        dst_checklists_root = specflow_internal / "checklists"
        for src_file in src_checklists.rglob("*.yaml"):
            rel_path = src_file.relative_to(src_checklists)
            dst_file = dst_checklists_root / rel_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            if not dst_file.exists():
                shutil.copy2(str(src_file), str(dst_file))

    # 4. Copy standards → .specflow/standards/ (no overwrite)
    src_standards = pack_root / "standards"
    if src_standards.exists():
        dst_standards = specflow_internal / "standards"
        dst_standards.mkdir(parents=True, exist_ok=True)
        for yaml_file in src_standards.glob("*.yaml"):
            dst_file = dst_standards / yaml_file.name
            if not dst_file.exists():
                shutil.copy2(str(yaml_file), str(dst_file))
                standards_added.append(yaml_file.stem)

    types_added = list(manifest.get("adds_artifact_types", []) or [])

    # 5. Install pack skills → platform skills dir (no overwrite)
    skills_added: list[str] = []
    declared_skills = manifest.get("adds_skills", []) or []
    if declared_skills:
        platform_code, _ = platform.detect_platform(root)
        if platform_code is None:
            print(f"  ⚠ Pack '{pack_name}' declares skills but no AI platform detected; install manually")
        else:
            skills_dir = platform.get_skills_dir(root, platform_code)
            for skill_name in declared_skills:
                src = pack_root / "skills" / skill_name
                if not src.is_dir():
                    return {
                        "ok": False,
                        "error": f"Pack declares skill '{skill_name}' but directory not found: {src}",
                    }
                dst = skills_dir / skill_name
                if not dst.exists():
                    shutil.copytree(str(src), str(dst))
                    skills_added.append(skill_name)

    return {
        "ok": True,
        "pack": pack_name,
        "types_added": types_added,
        "standards_added": standards_added,
        "skills_added": skills_added,
        "context_snippet": manifest.get("context_snippet", ""),
    }


_SENTINEL_START = "<!-- pack:{pack_name} context (auto-generated, do not edit manually) -->"
_SENTINEL_END = "<!-- end pack:{pack_name} context -->"


def inject_pack_context(root: Path, pack_name: str, context_snippet: str) -> bool:
    """Inject a pack's context snippet into the platform instruction file.

    Uses sentinel markers for idempotent updates. Returns True if the file
    was modified (new injection or updated snippet).
    """
    if not context_snippet:
        return False

    platform_code, _ = platform.detect_platform(root)
    if platform_code is None:
        return False

    cfg = platform.get_platform(platform_code)
    if not cfg:
        return False

    instruction_file = cfg.get("instruction_file")
    if not instruction_file:
        return False

    target = root / instruction_file

    if not target.exists():
        if instruction_file == "AGENTS.md":
            if platform_code == "claude-code" and (root / "CLAUDE.md").exists():
                target = root / "CLAUDE.md"
            elif platform_code == "gemini" and (root / "GEMINI.md").exists():
                target = root / "GEMINI.md"

    sentinel_start = _SENTINEL_START.format(pack_name=pack_name)
    sentinel_end = _SENTINEL_END.format(pack_name=pack_name)

    block = f"\n{sentinel_start}\n{context_snippet.strip()}\n{sentinel_end}\n"

    if target.exists():
        content = target.read_text(encoding="utf-8")
        if sentinel_start in content:
            start_idx = content.index(sentinel_start)
            end_idx = content.index(sentinel_end) + len(sentinel_end)
            existing_block = content[start_idx:end_idx]
            new_block = block.strip()
            if existing_block == new_block:
                return False
            content = content[:start_idx] + new_block + content[end_idx:]
            target.write_text(content, encoding="utf-8")
            return True
        content = content.rstrip() + "\n" + block
        target.write_text(content, encoding="utf-8")
        return True
    else:
        target.write_text(block, encoding="utf-8")
        return True
