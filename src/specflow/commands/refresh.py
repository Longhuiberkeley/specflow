"""specflow refresh — Update skills, agent-context, and templates without full re-init."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import yaml

from specflow.lib import config as config_lib
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
    skills_dst = plat_lib.get_skills_install_dir(root, platform_code)

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


def classify_schemas(root: Path, template_dir: Path | None = None) -> tuple[list[str], list[str], list[str]]:
    """Classify installed base schemas against package templates.

    Returns ``(new, identical, changed)`` as lists of schema type names (file
    stems):
      - new:       package schema with no installed counterpart in
                   ``.specflow/schema/``
      - identical: installed file exists and matches the package byte-for-byte
      - changed:   installed file exists but differs from the package (drift)

    Only base ``templates/schemas/*.yaml`` are considered; pack-added schemas
    that live only in ``.specflow/schema/`` are never classified, so pack-owned
    drift does not pollute the base-schema signal.
    """
    if template_dir is None:
        template_dir = _get_package_templates()
    schema_src = template_dir / "schemas"
    schema_dst = root / ".specflow" / "schema"
    new: list[str] = []
    identical: list[str] = []
    changed: list[str] = []
    if not schema_src.is_dir():
        return new, identical, changed
    for yaml_file in sorted(schema_src.glob("*.yaml")):
        dst_file = schema_dst / yaml_file.name
        if not dst_file.exists():
            new.append(yaml_file.stem)
        elif dst_file.read_bytes() == yaml_file.read_bytes():
            identical.append(yaml_file.stem)
        else:
            changed.append(yaml_file.stem)
    return new, identical, changed


def _update_schemas(root: Path, template_dir: Path, *, force: bool = False) -> tuple[int, list[str], list[str]]:
    """Write missing schemas always; drifted schemas only with ``force``.

    Safe schema-drift behavior: plain ``refresh --schemas`` installs new types
    but preserves a user's (or a prior tool's) edits to a shipped schema —
    overwriting silently would lose intentional drift. ``force`` explicitly
    replaces drifted schemas with the shipped defaults.

    Returns ``(written_count, preserved_changed, replaced_changed)``.
    """
    schema_src = template_dir / "schemas"
    schema_dst = root / ".specflow" / "schema"
    schema_dst.mkdir(parents=True, exist_ok=True)
    written = 0
    preserved: list[str] = []
    replaced: list[str] = []
    if not schema_src.is_dir():
        return 0, preserved, replaced
    for yaml_file in sorted(schema_src.glob("*.yaml")):
        dst_file = schema_dst / yaml_file.name
        if not dst_file.exists():
            shutil.copy2(str(yaml_file), str(dst_file))
            written += 1
        elif dst_file.read_bytes() != yaml_file.read_bytes():
            if force:
                shutil.copy2(str(yaml_file), str(dst_file))
                replaced.append(yaml_file.stem)
                written += 1
            else:
                preserved.append(yaml_file.stem)
    return written, preserved, replaced


def _schema_drift_summary(new_names: list[str], changed_names: list[str]) -> str:
    """Deterministic one-line schema summary for dry-run output."""
    parts: list[str] = []
    if new_names:
        parts.append(f"{len(new_names)} new: {', '.join(new_names)}")
    if changed_names:
        parts.append(f"{len(changed_names)} changed: {', '.join(changed_names)}")
    return "; ".join(parts) if parts else "up to date"


def _refresh_platform_specific(
    root: Path,
    platform_code: str,
    template_dir: Path,
    *,
    dry_run: bool,
    do_skills: bool,
    do_context: bool,
) -> list[tuple[str, str]]:
    """Run the per-platform refresh steps (skills + agent-context) for one platform.

    Returns a summary list of (label, detail) tuples.
    """
    summary: list[tuple[str, str]] = []

    # ── Skills ──────────────────────────────────────────────────
    if do_skills:
        skills_src = template_dir / "skills" / "shared"
        skills_dst = plat_lib.get_skills_install_dir(root, platform_code)
        remapped = plat_lib.get_skills_install_code(platform_code) != platform_code
        dest_note = " → .claude/skills (OpenCode reads this tree)" if remapped else ""
        leftovers = plat_lib.leftover_specflow_skills(root, platform_code)
        changed_count, changed_names = _count_skill_diffs(skills_src, skills_dst)
        if dry_run:
            if changed_count:
                summary.append((
                    "skills",
                    f"{changed_count} to update: {', '.join(changed_names)}{dest_note}",
                ))
            else:
                summary.append(("skills", f"up to date{dest_note}"))
        else:
            if changed_count:
                installed = _install_skills(root, platform_code, dry_run=False)
                summary.append((
                    "skills",
                    f"{installed} installed ({', '.join(changed_names)}){dest_note}",
                ))
            else:
                summary.append(("skills", f"up to date{dest_note}"))
        if leftovers:
            summary.append((
                "skills-leftover",
                f"{', '.join(leftovers)} in .opencode/skills would override "
                f".claude/skills — remove to avoid a silent fork",
            ))

    # ── Agent-context ───────────────────────────────────────────
    if do_context:
        # Pending CLAUDE.md actions must be visible even when the AGENTS.md
        # inject itself is idempotent (dry-run or "up to date").
        pending = scaffold_lib.pending_claude_md_migration(root, platform_code)
        if dry_run:
            # Check if content would change
            ctx_file = template_dir / "agent-context.md"
            if ctx_file.exists():
                summary.append(("context", "would re-inject (idempotent)"))
            else:
                summary.append(("context", "template not found"))
            for action in pending:
                summary.append(("context-claude-md", f"would {action}"))
        else:
            # Ensure the instruction file's parent dir exists (some platforms
            # nest it, e.g. .cursor/rules/specflow.md) before injecting.
            inst_cfg = plat_lib.get_platform(platform_code)
            inst_file = inst_cfg.get("instruction_file") if inst_cfg else None
            if inst_file:
                (root / inst_file).parent.mkdir(parents=True, exist_ok=True)
            changed = scaffold_lib.inject_base_context(root, template_dir, platform_code)
            if changed:
                summary.append(("context", "updated"))
            else:
                summary.append(("context", "up to date"))
            for action in pending:
                summary.append(("context-claude-md", action))

    return summary


def _refresh_shared(
    root: Path,
    template_dir: Path,
    *,
    dry_run: bool,
    do_schemas: bool,
    do_checklists: bool,
    force_schemas: bool,
) -> list[tuple[str, str]]:
    """Run the refresh steps that are not platform-scoped (schemas, checklists)."""
    summary: list[tuple[str, str]] = []

    # ── Schemas ─────────────────────────────────────────────────
    if do_schemas:
        new_names, _identical_names, changed_names = classify_schemas(root, template_dir)
        if dry_run:
            summary.append(("schemas", _schema_drift_summary(new_names, changed_names)))
        else:
            written, preserved, replaced = _update_schemas(root, template_dir, force=force_schemas)
            parts: list[str] = []
            if written:
                parts.append(f"{written} written")
            if preserved:
                parts.append(f"{len(preserved)} preserved (changed): {', '.join(preserved)}")
            if replaced:
                parts.append(f"{len(replaced)} replaced: {', '.join(replaced)}")
            detail = "; ".join(parts) if parts else "up to date"
            if preserved and not force_schemas:
                detail += (" — run `specflow refresh --schemas --force` to "
                           "replace with shipped defaults")
            summary.append(("schemas", detail))

    # ── Checklists ──────────────────────────────────────────────
    if do_checklists:
        if dry_run:
            summary.append(("checklists", "would copy new (idempotent)"))
        else:
            scaffold_lib.copy_checklists(root, template_dir)
            summary.append(("checklists", "copied (new only)"))

    return summary


def _refresh_active_packs(
    root: Path,
    platform_codes: list[str],
    *,
    dry_run: bool,
    force: bool,
) -> list[tuple[str, str]]:
    """Preview or refresh assets for packs listed in project config."""
    summary: list[tuple[str, str]] = []
    active_packs = (config_lib.read_config(root) or {}).get("active_packs", []) or []
    packs_dir = Path(__file__).parent.parent / "packs"
    for pack_name in active_packs:
        preview = scaffold_lib.inspect_pack_refresh(root, pack_name, packs_dir, platform_codes)
        if not preview.get("ok"):
            summary.append((f"pack:{pack_name}", preview.get("error", "not found")))
            continue
        changes = preview["changes"]
        if dry_run:
            detail = f"{len(changes)} managed file(s) differ" if changes else "up to date"
            summary.append((f"pack:{pack_name}", detail))
            continue
        result = scaffold_lib.refresh_pack(
            root, pack_name, packs_dir, platform_codes, force=force,
        )
        written = len(result.get("written", []))
        preserved = len(result.get("preserved", []))
        detail = f"{written} written"
        if preserved:
            detail += f", {preserved} preserved (use --force to replace)"
        summary.append((f"pack:{pack_name}", detail))
    if not active_packs:
        summary.append(("packs", "no active packs"))
    return summary


def _run_all_platforms(root: Path, detected: list[tuple[str, dict]], args: dict) -> int:
    """Refresh skills + agent-context for every detected platform, plus shared
    (non-platform-scoped) steps once.
    """
    dry_run = args.get("dry_run", False)
    do_skills = not args.get("no_skills", False)
    do_context = not args.get("no_context", False)
    do_schemas = args.get("schemas", False)
    do_checklists = args.get("checklists", False)
    force_schemas = args.get("force", False)

    template_dir = _get_package_templates()

    if dry_run:
        print(f"  [dry-run] Refresh preview for {len(detected)} platform(s):")
    else:
        print(f"  Refresh complete for {len(detected)} platform(s):")

    seen_skill_installs: set[str] = set()
    for platform_code, cfg in detected:
        install_code = plat_lib.get_skills_install_code(platform_code)
        do_skills_here = do_skills and install_code not in seen_skill_installs
        if do_skills_here:
            seen_skill_installs.add(install_code)
        platform_summary = _refresh_platform_specific(
            root, platform_code, template_dir,
            dry_run=dry_run, do_skills=do_skills_here, do_context=do_context,
        )
        if do_skills and not do_skills_here:
            platform_summary.insert(0, (
                "skills",
                f"shared with {install_code} (.claude/skills) — not copied again",
            ))
        leftovers = plat_lib.leftover_specflow_skills(root, platform_code)
        if leftovers and not any(label == "skills-leftover" for label, _ in platform_summary):
            platform_summary.append((
                "skills-leftover",
                f"{', '.join(leftovers)} in host skills dir would override "
                f".claude/skills — remove to avoid a silent fork",
            ))
        print(f"    [{platform_code}] {cfg.get('name', platform_code)}:")
        for label, detail in platform_summary:
            print(f"      {label}: {detail}")

    shared_summary = _refresh_shared(
        root, template_dir,
        dry_run=dry_run, do_schemas=do_schemas, do_checklists=do_checklists,
        force_schemas=force_schemas,
    )
    if args.get("packs", False):
        shared_summary.extend(_refresh_active_packs(
            root,
            [code for code, _ in detected],
            dry_run=dry_run,
            force=force_schemas,
        ))
    if shared_summary:
        print("    shared:")
        for label, detail in shared_summary:
            print(f"      {label}: {detail}")

    if dry_run:
        print("\n  Run without --dry-run to apply changes.")

    return 0


def run(root: Path, args: dict) -> int:
    """Refresh skills, agent-context, schemas, and checklists."""
    root = root.resolve()

    specflow_dir = root / ".specflow"
    if not specflow_dir.is_dir():
        print("  x No .specflow/ directory found. Run 'specflow init' first.")
        return 1

    # Detect platform(s)
    all_platforms = args.get("all_platforms", False)
    platform_code = args.get("platform")

    if all_platforms:
        if platform_code:
            print(f"  ! --all-platforms overrides --platform '{platform_code}'.")
        detected = plat_lib.detect_platforms(root)
        if not detected:
            print("  x No AI platform detected. Nothing to refresh for --all-platforms.")
            return 1
        return _run_all_platforms(root, detected, args)

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

    summary = _refresh_platform_specific(
        root, platform_code, template_dir,
        dry_run=dry_run, do_skills=do_skills, do_context=do_context,
    )

    # ── Cross-host leftovers ────────────────────────────────────
    # A remapped host (OpenCode) prefers its own skills tree over .claude/skills,
    # so a leftover specflow-* copy silently overrides the install. Default
    # refresh resolves to ONE platform, so scan the other detected hosts too —
    # otherwise leftovers only surface via init or --all-platforms.
    if do_skills:
        for code, _host_cfg in plat_lib.detect_platforms(root):
            if code == platform_code:
                continue  # already reported by _refresh_platform_specific
            others = plat_lib.leftover_specflow_skills(root, code)
            if others:
                host_cfg = plat_lib.get_platform(code) or {}
                summary.append((
                    "skills-leftover",
                    f"{', '.join(others)} in {host_cfg.get('skills_dir', '?')} "
                    f"would override .claude/skills on {host_cfg.get('name', code)} "
                    f"— remove to avoid a silent fork",
                ))

    summary.extend(_refresh_shared(
        root, template_dir,
        dry_run=dry_run, do_schemas=do_schemas, do_checklists=do_checklists,
        force_schemas=force_schemas,
    ))
    if args.get("packs", False):
        summary.extend(_refresh_active_packs(
            root,
            [platform_code],
            dry_run=dry_run,
            force=force_schemas,
        ))

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
