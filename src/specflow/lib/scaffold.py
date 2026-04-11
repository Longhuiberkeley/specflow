"""Directory and file scaffolding for SpecFlow init."""

import shutil
from pathlib import Path

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
