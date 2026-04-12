"""Directory and file scaffolding for SpecFlow init."""

import shutil
from pathlib import Path
from typing import Any

import yaml

# Spec directories under _specflow/
SPEC_DIRS = [
    "specs/requirements",
    "specs/architecture",
    "specs/detailed-design",
    "specs/unit-tests",
    "specs/integration-tests",
    "specs/qualification-tests",
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


def create_internal_dirs(root: Path, template_dir: Path) -> None:
    """Create .specflow/ internal directories and copy schemas."""
    specflow = root / ".specflow"
    for d in INTERNAL_DIRS:
        (specflow / d).mkdir(parents=True, exist_ok=True)

    # Copy schema files
    schema_dst = specflow / "schema"
    schema_src = template_dir / "schemas"
    if schema_src.exists():
        if schema_dst.exists():
            shutil.rmtree(str(schema_dst))
        shutil.copytree(str(schema_src), str(schema_dst))


def copy_checklists(root: Path, template_dir: Path) -> None:
    """Copy checklist templates from package to project instance.

    Copies from src/specflow/templates/checklists/ to .specflow/checklists/.
    Only copies if the destination file doesn't already exist (preserves user edits).
    """
    checklists_src = template_dir / "checklists"
    checklists_dst = root / ".specflow" / "checklists"

    if not checklists_src.exists():
        return

    for category in ("phase-gates", "in-process", "readiness"):
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

    return {
        "ok": True,
        "pack": pack_name,
        "types_added": types_added,
        "standards_added": standards_added,
    }
