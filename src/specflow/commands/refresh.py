"""specflow refresh — Update skills, agent-context, and templates without full re-init."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import yaml

from specflow.lib import platform as plat_lib
from specflow.lib import scaffold as scaffold_lib


def _get_package_templates() -> Path:
    return Path(__file__).parent.parent / "templates"


def _hash_dir(path: Path) -> str:
    """Compute a stable hash of a directory's contents (sorted file hashes)."""
    if not path.is_dir():
        return ""
    parts = []
    for f in sorted(path.rglob("*")):
        if f.is_file():
            h = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
            parts.append(f"{f.relative_to(path)}:{h}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _count_skill_diffs(skills_src: Path, skills_dst: Path) -> tuple[int, list[str]]:
    """Compare source and destination skill directories.

    Returns (changed_count, list_of_changed_skill_names).
    """
    changed = []
    if not skills_src.is_dir():
        return 0, changed
    for skill_dir in sorted(skills_src.iterdir()):
        if not skill_dir.is_dir():
            continue
        dst = skills_dst / skill_dir.name
        src_hash = _hash_dir(skill_dir)
        dst_hash = _hash_dir(dst)
        if src_hash != dst_hash:
            changed.append(skill_dir.name)
    return len(changed), changed


def _install_skills(root: Path, platform_code: str, *, dry_run: bool = False) -> int:
    """Copy skills from package templates to platform skills directory.

    Returns the number of skills installed.
    """
    template_dir = _get_package_templates()
    skills_src = template_dir / "skills" / "shared"
    skills_dst = plat_lib.get_skills_dir(root, platform_code)

    skills_dst.mkdir(parents=True, exist_ok=True)

    cfg = plat_lib.get_platform(platform_code)
    legacy = cfg.get("legacy_dirs", []) if cfg else []
    if not dry_run:
        for legacy_dir in legacy:
            legacy_path = root / legacy_dir
            if legacy_path.exists():
                shutil.rmtree(str(legacy_path), ignore_errors=True)

    count = 0
    for skill_dir in skills_src.iterdir():
        if skill_dir.is_dir():
            dst = skills_dst / skill_dir.name
            if dst.exists():
                shutil.rmtree(str(dst))
            shutil.copytree(str(skill_dir), str(dst))
            count += 1
    return count


def _compare_schemas(root: Path, template_dir: Path) -> tuple[int, list[str]]:
    """Compare package schemas with installed schemas.

    Returns (new_count, list_of_new_schema_names).
    """
    schema_src = template_dir / "schemas"
    schema_dst = root / ".specflow" / "schema"
    new_schemas = []
    if not schema_src.is_dir():
        return 0, new_schemas
    for yaml_file in sorted(schema_src.glob("*.yaml")):
        dst_file = schema_dst / yaml_file.name
        if not dst_file.exists():
            new_schemas.append(yaml_file.stem)
    return len(new_schemas), new_schemas


def _update_schemas(root: Path, template_dir: Path, *, force: bool = False) -> int:
    """Copy new (or all, if force) schemas from package to project.

    Returns count of schemas written.
    """
    schema_src = template_dir / "schemas"
    schema_dst = root / ".specflow" / "schema"
    schema_dst.mkdir(parents=True, exist_ok=True)
    count = 0
    if not schema_src.is_dir():
        return 0
    for yaml_file in sorted(schema_src.glob("*.yaml")):
        dst_file = schema_dst / yaml_file.name
        if force or not dst_file.exists():
            shutil.copy2(str(yaml_file), str(dst_file))
            count += 1
    return count


def run(root: Path, args: dict) -> int:
    """Refresh skills, agent-context, schemas, and checklists."""
    root = root.resolve()

    specflow_dir = root / ".specflow"
    if not specflow_dir.is_dir():
        print("  x No .specflow/ directory found. Run 'specflow init' first.")
        return 1

    # Detect platform
    platform_code = args.get("platform")
    if platform_code:
        cfg = plat_lib.get_platform(platform_code)
        if cfg is None:
            print(f"  x Unknown platform '{platform_code}'.")
            print(f"    Available: {', '.join(plat_lib.get_all_platforms().keys())}")
            return 1
        platform_name = cfg["name"]
    else:
        platform_code, cfg = plat_lib.detect_platform(root)
        if platform_code is None:
            platform_code = "claude-code"
            platform_name = "Claude Code"
        else:
            platform_name = cfg["name"]

    dry_run = args.get("dry_run", False)
    do_skills = not args.get("no_skills", False)
    do_context = not args.get("no_context", False)
    do_schemas = args.get("schemas", False)
    do_checklists = args.get("checklists", False)
    force_schemas = args.get("force", False)

    template_dir = _get_package_templates()
    summary: list[tuple[str, str]] = []

    # ── Skills ──────────────────────────────────────────────────
    if do_skills:
        skills_src = template_dir / "skills" / "shared"
        skills_dst = plat_lib.get_skills_dir(root, platform_code)
        changed_count, changed_names = _count_skill_diffs(skills_src, skills_dst)
        if dry_run:
            if changed_count:
                summary.append(("skills", f"{changed_count} to update: {', '.join(changed_names)}"))
            else:
                summary.append(("skills", "up to date"))
        else:
            if changed_count:
                installed = _install_skills(root, platform_code, dry_run=False)
                summary.append(("skills", f"{installed} installed ({', '.join(changed_names)})"))
            else:
                summary.append(("skills", "up to date"))

    # ── Agent-context ───────────────────────────────────────────
    if do_context:
        if dry_run:
            # Check if content would change
            ctx_file = template_dir / "agent-context.md"
            if ctx_file.exists():
                summary.append(("context", "would re-inject (idempotent)"))
            else:
                summary.append(("context", "template not found"))
        else:
            changed = scaffold_lib.inject_base_context(root, template_dir, platform_code)
            if changed:
                summary.append(("context", "updated"))
            else:
                summary.append(("context", "up to date"))

    # ── Schemas ─────────────────────────────────────────────────
    if do_schemas:
        new_count, new_names = _compare_schemas(root, template_dir)
        if dry_run:
            if new_count:
                summary.append(("schemas", f"{new_count} new: {', '.join(new_names)}"))
            else:
                summary.append(("schemas", "up to date"))
        else:
            written = _update_schemas(root, template_dir, force=force_schemas)
            if written:
                summary.append(("schemas", f"{written} written"))
            else:
                summary.append(("schemas", "up to date"))

    # ── Checklists ──────────────────────────────────────────────
    if do_checklists:
        if dry_run:
            summary.append(("checklists", "would copy new (idempotent)"))
        else:
            scaffold_lib.copy_checklists(root, template_dir)
            summary.append(("checklists", "copied (new only)"))

    # ── Summary ─────────────────────────────────────────────────
    if dry_run:
        print("  [dry-run] Refresh preview:")
    else:
        print("  Refresh complete:")

    for label, detail in summary:
        print(f"    {label}: {detail}")

    if dry_run:
        print("\n  Run without --dry-run to apply changes.")

    return 0
