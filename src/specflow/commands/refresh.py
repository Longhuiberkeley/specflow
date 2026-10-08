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


def _install_skills(root: Path, platform_code: str) -> int:
    """Copy skills from package templates to platform skills directory.

    Always writes — the caller decides on dry-run before calling. Returns
    the number of skill directories copied (every shipped skill is
    re-copied; the caller reports only the ones that actually changed).
    Legacy-dir cleanup is the caller's job (``_refresh_platform_specific``)
    so it also runs when the skills are already current.
    """
    template_dir = _get_package_templates()
    skills_src = template_dir / "skills" / "shared"
    skills_dst = plat_lib.get_skills_install_dir(root, platform_code)

    skills_dst.mkdir(parents=True, exist_ok=True)

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

    Base ``templates/schemas/*.yaml`` are always considered. Optional types
    (``templates/schemas/optional/*.yaml``, installed via
    ``init --with-types``) are considered ONLY when already installed — an
    uninstalled optional type is never reported as ``new``, so opting out
    stays silent while an installed copy still gets a drift signal.
    Pack-added schemas that live only in ``.specflow/schema/`` are never
    classified, and an optional core name that an ACTIVE pack owns (its
    manifest adds the type, or it ships ``schemas/<name>.yaml``) is skipped
    too, so pack-owned drift does not pollute the base-schema signal.
    """
    if template_dir is None:
        template_dir = _get_package_templates()
    schema_dst = root / ".specflow" / "schema"
    new: list[str] = []
    identical: list[str] = []
    changed: list[str] = []
    for yaml_file, installed_only in _shipped_schema_files(template_dir, root):
        dst_file = schema_dst / yaml_file.name
        if not dst_file.exists():
            if not installed_only:
                new.append(yaml_file.stem)
        elif dst_file.read_bytes() == yaml_file.read_bytes():
            identical.append(yaml_file.stem)
        else:
            changed.append(yaml_file.stem)
    return new, identical, changed


def _shipped_schema_files(template_dir: Path, root: Path) -> list[tuple[Path, bool]]:
    """``(template, installed_only)`` for base schemas then optional types.

    An optional type that an active pack owns is left out entirely: the
    installed ``.specflow/schema/<name>.yaml`` is the PACK's file (synced by
    ``refresh --packs``), not a drifted copy of the core optional schema.
    """
    schema_src = template_dir / "schemas"
    files: list[tuple[Path, bool]] = []
    if schema_src.is_dir():
        files.extend((f, False) for f in sorted(schema_src.glob("*.yaml")))
    optional_src = schema_src / "optional"
    if optional_src.is_dir():
        active_packs = (config_lib.read_config(root) or {}).get("active_packs", []) or []
        pack_owned = scaffold_lib.pack_owned_schema_names(root, active_packs)
        files.extend(
            (f, True) for f in sorted(optional_src.glob("*.yaml")) if f.stem not in pack_owned
        )
    return files


def _update_schemas(root: Path, template_dir: Path, *, force: bool = False) -> tuple[int, list[str], list[str]]:
    """Write missing schemas always; drifted schemas only with ``force``.

    Safe schema-drift behavior: plain ``refresh --schemas`` installs new types
    but preserves a user's (or a prior tool's) edits to a shipped schema —
    overwriting silently would lose intentional drift. ``force`` explicitly
    replaces drifted schemas with the shipped defaults.

    Installed optional types (``schemas/optional/``) follow the same rule;
    an optional type that is not installed, or that an active pack owns, is
    never written here (even with ``force``).

    Returns ``(written_count, preserved_changed, replaced_changed)``.
    """
    schema_dst = root / ".specflow" / "schema"
    schema_dst.mkdir(parents=True, exist_ok=True)
    written = 0
    preserved: list[str] = []
    replaced: list[str] = []
    for yaml_file, installed_only in _shipped_schema_files(template_dir, root):
        dst_file = schema_dst / yaml_file.name
        if not dst_file.exists():
            if installed_only:
                continue
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
        install_code = plat_lib.get_skills_install_code(platform_code)
        dest_note = ""
        if install_code != platform_code:
            dest_rel = skills_dst.relative_to(root).as_posix()
            dest_note = f" → {dest_rel} (shared with {install_code})"
        leftovers = plat_lib.leftover_specflow_skills(root, platform_code)
        # STORY-685: legacy cleanup runs before any copy or context injection,
        # and (F-130) runs even when the skills are already current — a
        # leftover `.claude/commands/specflow-*` is stale either way.
        legacy_removed = plat_lib.cleanup_legacy_dirs(root, platform_code, dry_run=dry_run)
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
                _install_skills(root, platform_code)
                summary.append((
                    "skills",
                    f"{len(changed_names)} installed ({', '.join(changed_names)}){dest_note}",
                ))
            else:
                summary.append(("skills", f"up to date{dest_note}"))
        if legacy_removed:
            verb = "would remove" if dry_run else "removed"
            summary.append(("skills-legacy", f"{verb} {', '.join(legacy_removed)}"))
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
    backup_stamp: str | None = None,
) -> list[tuple[str, str]]:
    """Run the refresh steps that are not platform-scoped (schemas, checklists)."""
    summary: list[tuple[str, str]] = []

    # ── Format version (STORY-678) ──────────────────────────────
    stamped = config_lib.stamp_format_version(root, dry_run=dry_run)
    if stamped:
        verb = "would stamp" if dry_run else "stamped"
        summary.append(("config", f"{verb} format_version: {config_lib.FORMAT_VERSION}"))
    legacy_version = config_lib.strip_legacy_version(root, dry_run=dry_run)
    if legacy_version is not None:
        verb = "would remove" if dry_run else "removed"
        summary.append(("config", f"{verb} stale version: {legacy_version} (format_version is the stamp)"))

    # ── Findings ratchet migration (DEC-099) ──────────
    from specflow.commands.artifact_lint import LEGACY_HISTORY_FILE
    from specflow.core.findings_baseline import BASELINE_FILE

    legacy_history = root / LEGACY_HISTORY_FILE
    if legacy_history.exists():
        if dry_run:
            summary.append(("lint-history", f"would remove {LEGACY_HISTORY_FILE} (run counters retired)"))
        else:
            from specflow.lib import locks

            with locks.mutation_lock(root):
                legacy_history.unlink()
            summary.append(("lint-history", f"removed {LEGACY_HISTORY_FILE} (run counters retired)"))
        if not (root / BASELINE_FILE).exists():
            summary.append((
                "findings",
                "no findings baseline — run `specflow findings-baseline update` once and commit "
                f"{BASELINE_FILE} to turn the ratchet on",
            ))

    # ── Source-drift store (REQ-053 AC2: lint no longer seeds it) ─
    from specflow.lib import source_drift

    if not source_drift.store_path(root).exists() and (root / "_specflow").is_dir():
        if dry_run:
            summary.append(("source-drift", "would seed source fingerprints (store absent)"))
        else:
            seeded = source_drift.seed(root)
            if seeded:
                summary.append(("source-drift", f"seeded source fingerprints for {len(seeded)} artifact(s)"))

    # ── CI workflow pin (STORY-705) ─────────────────────────────
    from specflow.lib.adapters.github_actions import WORKFLOW_PATH, bump_workflow_pin

    pin = bump_workflow_pin(root, dry_run=dry_run)
    if pin["count"]:
        verb = "would bump" if dry_run else "bumped"
        summary.append(("ci", f"{verb} {WORKFLOW_PATH} pin {', '.join(pin['old'])} → {pin['new']} ({pin['count']})"))
    if pin["skipped"]:
        summary.append(("ci", f"left non-release pin(s) as-is: {', '.join(pin['skipped'])}"))

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


    # Practice migration owns the legacy status-map collapse, independently of
    # whether the caller requested general schema refresh (which preserves drift).
    from specflow.lib.practices import migrate_practices

    migration = migrate_practices(root, dry_run=dry_run)
    if dry_run:
        detail_parts = []
        if migration.get("would_repair_status_map"):
            detail_parts.append("best-practice status map would be repaired")
        if migration.get("would_stamp"):
            detail_parts.append(
                f"{len(migration['would_stamp'])} BP provenance value(s) to stamp"
            )
    else:
        detail_parts = []
        if migration.get("status_map_repaired"):
            detail_parts.append("best-practice status map repaired")
        changed = len(migration.get("stamped", []))
        if changed:
            detail_parts.append(f"{changed} BP provenance value(s) stamped")
    warnings = len(migration.get("warnings", []))
    errors = len(migration.get("errors", []))
    if warnings:
        detail_parts.append(f"{warnings} warning(s)")
    if errors:
        detail_parts.append(f"{errors} error(s)")
    summary.append(("practices", "; ".join(detail_parts) or "up to date"))

    # ── Checklists ──────────────────────────────────────────────
    if do_checklists:
        summary.append(("checklists", _refresh_checklists(
            root, template_dir, dry_run=dry_run, force=force_schemas,
            backup_stamp=backup_stamp,
        )))

    return summary


_LIST_CAP = 8


def _list_paths(paths: list[str], cap: int = _LIST_CAP) -> str:
    """``a, b, c (+N more)`` — enough to see what moved without a wall of paths."""
    shown = ", ".join(paths[:cap])
    more = len(paths) - cap
    return f"{shown} (+{more} more)" if more > 0 else shown


def _refresh_checklists(
    root: Path,
    template_dir: Path,
    *,
    dry_run: bool,
    force: bool,
    backup_stamp: str | None = None,
) -> str:
    """Write missing checklists, repair unparseable ones, and replace drifted
    ones only with ``--force`` (STORY-687: fixed templates must reach
    projects initialised before the fix)."""
    if dry_run:
        status = scaffold_lib.classify_checklists(root, template_dir)
        parts = []
        if status["missing"]:
            parts.append(f"would write {len(status['missing'])} new")
        if status["broken"]:
            parts.append(f"would replace {len(status['broken'])} unparseable: {', '.join(status['broken'])}")
        if status["drifted"]:
            verb = "would replace" if force else "would preserve"
            parts.append(f"{verb} {len(status['drifted'])} changed: {', '.join(status['drifted'])}")
        return "; ".join(parts) or "up to date"
    result = scaffold_lib.copy_checklists(root, template_dir, force=force, backup_stamp=backup_stamp)
    parts = []
    if result["missing"]:
        parts.append(f"{len(result['missing'])} written")
    if result["broken"]:
        parts.append(f"{len(result['broken'])} unparseable replaced: {', '.join(result['broken'])}")
    if result["drifted"]:
        if force:
            parts.append(f"{len(result['drifted'])} changed replaced: {', '.join(result['drifted'])}")
        else:
            parts.append(
                f"{len(result['drifted'])} preserved (changed): {', '.join(result['drifted'])}"
                " — run `specflow refresh --checklists --force` to take the shipped version"
            )
    if result.get("backup_dir"):
        parts.append(f"backups in {result['backup_dir']}/checklists/")
    return "; ".join(parts) or "up to date"


def _refresh_active_packs(
    root: Path,
    platform_codes: list[str],
    *,
    dry_run: bool,
    force: bool,
    backup_stamp: str | None = None,
) -> list[tuple[str, str]]:
    """Preview or refresh assets for packs listed in project config.

    Names every differing / written / preserved / backed-up path (capped at
    ``_LIST_CAP`` + "more") so a user can see WHICH generated file moved.
    """
    summary: list[tuple[str, str]] = []
    active_packs = (config_lib.read_config(root) or {}).get("active_packs", []) or []
    for pack_name in active_packs:
        # STORY-681: a project-local pack wins over the bundled one.
        packs_dir = scaffold_lib.resolve_packs_dir(root, pack_name)
        preview = scaffold_lib.inspect_pack_refresh(root, pack_name, packs_dir, platform_codes)
        if not preview.get("ok"):
            summary.append((f"pack:{pack_name}", preview.get("error", "not found")))
            continue
        changes = preview["changes"]
        if dry_run:
            if changes:
                new = [str(dst.relative_to(root).as_posix()) for _s, dst, _k in changes if not dst.exists()]
                differ = [str(dst.relative_to(root).as_posix()) for _s, dst, _k in changes if dst.exists()]
                parts = []
                if new:
                    parts.append(f"would write {len(new)} new: {_list_paths(new)}")
                if differ:
                    verb = "would replace" if force else "would preserve"
                    parts.append(f"{verb} {len(differ)} changed: {_list_paths(differ)}")
                detail = "; ".join(parts)
            else:
                detail = "up to date"
            summary.append((f"pack:{pack_name}", detail))
            continue
        result = scaffold_lib.refresh_pack(
            root, pack_name, packs_dir, platform_codes, force=force, backup_stamp=backup_stamp,
        )
        written = result.get("written", [])
        preserved = result.get("preserved", [])
        parts = []
        if written:
            parts.append(f"{len(written)} written: {_list_paths(written)}")
        if preserved:
            parts.append(
                f"{len(preserved)} preserved (changed): {_list_paths(preserved)}"
                " — run `specflow refresh --packs --force` to take the pack version"
            )
        if result.get("backup_dir"):
            parts.append(f"backups in {result['backup_dir']}/packs/{pack_name}/")
        summary.append((f"pack:{pack_name}", "; ".join(parts) or "up to date"))
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
    backup_stamp = scaffold_lib.backup_run_dir(root).name

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
            shared_dir = plat_lib.get_skills_install_dir(root, platform_code).relative_to(root).as_posix()
            platform_summary.insert(0, (
                "skills",
                f"shared with {install_code} ({shared_dir}) — not copied again",
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
        force_schemas=force_schemas, backup_stamp=backup_stamp,
    )
    if args.get("packs", False):
        shared_summary.extend(_refresh_active_packs(
            root,
            [code for code, _ in detected],
            dry_run=dry_run,
            force=force_schemas,
            backup_stamp=backup_stamp,
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
    backup_stamp = scaffold_lib.backup_run_dir(root).name

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
        force_schemas=force_schemas, backup_stamp=backup_stamp,
    ))
    if args.get("packs", False):
        summary.extend(_refresh_active_packs(
            root,
            [platform_code],
            dry_run=dry_run,
            force=force_schemas,
            backup_stamp=backup_stamp,
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
