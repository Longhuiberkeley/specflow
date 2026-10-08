"""specflow init — Scaffold a SpecFlow project."""

import shutil
from pathlib import Path

import yaml

import specflow
from specflow.lib import platform as plat_lib
from specflow.lib import rbac as rbac_lib
from specflow.lib import scaffold as scaffold_lib
from specflow.lib import config as config_lib
from specflow.lib.adapters import load_adapters_config, get_adapter


def _apply_preset(root: Path, preset: str, platform_code: str | None = None) -> int:
    # STORY-681: .specflow/packs/<preset>/ resolves before the bundled pack.
    packs_dir = scaffold_lib.resolve_packs_dir(root, preset)
    result = scaffold_lib.apply_pack(root, preset, packs_dir, platform_code=platform_code)
    if not result["ok"]:
        print(f"  x Pack '{preset}' not applied: {result['error']}")
        return 1

    config = config_lib.read_config(root)
    active = config.setdefault("active_packs", [])
    if preset not in active:
        active.append(preset)

    types_added = result.get("types_added", []) or []
    if types_added:
        registered_types = config.setdefault("artifact_types", [])
        for t in types_added:
            if t not in registered_types:
                registered_types.append(t)

    config_lib.write_config(root, config)

    context_snippet = result.get("context_snippet", "") or ""
    context_injected = False
    if context_snippet:
        context_injected = scaffold_lib.inject_pack_context(
            root, preset, context_snippet, platform_code
        )

    pieces = []
    if types_added:
        pieces.append(f"{len(types_added)} artifact type(s)")
    standards_added = result.get("standards_added", []) or []
    if standards_added:
        pieces.append(f"{len(standards_added)} standard(s)")
    if context_injected:
        pieces.append("instruction file updated")
    detail = ", ".join(pieces) if pieces else "no new items"
    print(f"  + Pack '{preset}' applied ({detail})")
    return 0


def _get_package_templates() -> Path:
    return Path(__file__).parent.parent / "templates"


def _install_optional_types(root: Path, type_names: list[str], *, force: bool = False) -> int:
    """Install optional artifact type schemas from templates/schemas/optional/.

    An already-installed type is skipped; with ``force`` (``init --force
    --with-types X``) a requested type whose installed copy drifted from the
    shipped template is reset to it, matching what ``--force`` does to the
    base schemas (the backup taken earlier in the run holds the old copy).
    Drift in an installed optional type is otherwise surfaced by
    ``specflow refresh --schemas`` / ``brief`` like any base schema.

    Returns 0 on success, 1 on error.
    """
    optional_dir = _get_package_templates() / "schemas" / "optional"
    schema_dst = root / ".specflow" / "schema"
    schema_dst.mkdir(parents=True, exist_ok=True)
    available = sorted(f.stem for f in optional_dir.glob("*.yaml")) if optional_dir.is_dir() else []

    installed = []
    for type_name in type_names:
        type_name = type_name.strip()
        if not type_name:
            continue
        src = optional_dir / f"{type_name}.yaml"
        if not src.exists():
            print(f"  x Optional type '{type_name}' not found (available: {', '.join(available)})")
            return 1

        data = yaml.safe_load(src.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            print(f"  x Invalid schema for '{type_name}'")
            return 1

        dst = schema_dst / f"{type_name}.yaml"
        if dst.exists():
            if force and dst.read_bytes() != src.read_bytes():
                shutil.copy2(str(src), str(dst))
                print(f"  + Type '{type_name}' reset to the shipped schema (--force)")
            else:
                print(f"  = Type '{type_name}' already installed — skipping")
            continue

        shutil.copy2(str(src), str(dst))

        directory = data.get("directory", "")
        if directory:
            rel = directory
            if rel.startswith("_specflow/"):
                rel = rel[len("_specflow/"):]
            rel = rel.rstrip("/")
            spec_dir = root / "_specflow" / rel
            spec_dir.mkdir(parents=True, exist_ok=True)
            index = spec_dir / "_index.yaml"
            if not index.exists():
                from specflow.lib import locks as locks_lib

                locks_lib.locked_exclusive_write(
                    root, index, yaml.dump({"artifacts": {}, "next_id": 1}, default_flow_style=False)
                )

        installed.append(type_name)
        print(f"  + Optional type '{type_name}' installed (schema + directory)")

    if installed:
        config = config_lib.read_config(root)
        registered_types = config.setdefault("artifact_types", [])
        for t in installed:
            if t not in registered_types:
                registered_types.append(t)
        config_lib.write_config(root, config)

    return 0


def _install_skills(root: Path, platform_code: str) -> None:
    template_dir = _get_package_templates()
    skills_src = template_dir / "skills" / "shared"
    skills_dst = plat_lib.get_skills_install_dir(root, platform_code)

    skills_dst.mkdir(parents=True, exist_ok=True)

    # STORY-685: only specflow-owned entries; never the instruction file's dir.
    plat_lib.cleanup_legacy_dirs(root, platform_code)

    for skill_dir in skills_src.iterdir():
        if skill_dir.is_dir():
            dst = skills_dst / skill_dir.name
            if dst.exists():
                shutil.rmtree(str(dst))
            shutil.copytree(str(skill_dir), str(dst))


def _multi_platform_warning(root: Path, installed_code: str, explicit_platform: bool) -> str | None:
    """Return a warning if other detected hosts still need their own skill tree.

    OpenCode consumes ``.claude/skills`` — it is not a missing install target.
    No warning when the platform was explicitly requested via ``--platform``.
    Leftover ``.opencode/skills/specflow-*`` copies are always reported (they
    silently override the Claude tree on OpenCode) even if ``--platform`` was set.
    """
    leftovers: list[str] = []
    leftover_note = ""
    for code, _ in plat_lib.detect_platforms(root) or [(installed_code, {})]:
        found = plat_lib.leftover_specflow_skills(root, code)
        if found:
            leftovers.extend(f"{code}:{name}" for name in found)
    if leftovers:
        leftover_note = (
            f" Leftover SpecFlow skills in a host tree OpenCode would prefer over "
            f".claude/skills ({', '.join(leftovers)}). Remove them to avoid a "
            f"silent per-harness fork."
        )

    if explicit_platform:
        return leftover_note.strip() or None
    detected = plat_lib.detect_platforms(root)
    if len(detected) <= 1:
        return leftover_note.strip() or None
    install_code = plat_lib.get_skills_install_code(installed_code)
    other_codes = [
        code for code, _ in detected
        if plat_lib.get_skills_install_code(code) != install_code
    ]
    if not other_codes:
        if leftover_note:
            return leftover_note.strip()
        return None
    others_str = ", ".join(other_codes)
    return (
        f"⚠ Multiple AI-host platforms detected: {installed_code} (installed), {others_str}. "
        f"Skills were installed only for {install_code} "
        f"(hosts that share its skills tree are covered; other hosts need their own copy). "
        f"Run 'specflow refresh --platform <code>' for each other host, "
        f"or 'specflow refresh --all-platforms'."
        f"{leftover_note}"
    )


def run(root: Path, args: dict) -> int:
    root = root.resolve()

    explicit_platform = bool(args.get("platform"))
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
            print("  No AI platform detected. Defaulting to Claude Code.")
        else:
            platform_name = cfg["name"]
    print(f"  + Platform: {platform_name}")

    project_name = root.name
    force = args.get("force", False)
    specflow_dir = root / ".specflow"
    # A `.specflow/` that holds only project-local packs (pack-first flow,
    # STORY-681/690) is not an initialised project: treat it as a fresh init.
    is_reinit = (specflow_dir / "config.yaml").exists()

    if is_reinit and force:
        backup_dir = scaffold_lib.backup_run_dir(root)
        previous_packs = [
            str(p) for p in (config_lib.read_config(root) or {}).get("active_packs", []) or []
        ]
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            backed_up = config_lib.backup_specflow_internals(root, backup_dir)
            if backed_up:
                print(f"  + Backed up to {backup_dir.relative_to(root)}: {', '.join(backed_up)}")
        except Exception as e:
            print(f"  x Backup failed: {e}. Aborting --force re-init.")
            return 1

        reset_note = "config.yaml, state.yaml and schema/ reset to fresh defaults"
        if previous_packs:
            reset_note += (
                f"; active_packs cleared ({', '.join(previous_packs)}) along with their "
                "pack artifact_types"
            )
            if not args.get("preset"):
                reset_note += " — re-apply with --preset"
        print(f"  + --force: clean re-initialization — {reset_note}")
        is_reinit = False
        _force_overwrite_schemas = True
    else:
        # --force on a `.specflow/` without config.yaml still resets schemas.
        _force_overwrite_schemas = bool(force)

    if is_reinit:
        print("  Re-initializing existing SpecFlow project (merge mode)...")

        existing_config = config_lib.read_config(root)

        scaffold_lib.create_internal_dirs(root, _get_package_templates())
        scaffold_lib.create_spec_dirs(root)

        defaults = config_lib.default_config(project_name)
        new_fields = sorted(set(defaults) - set(existing_config or {}))
        merged = config_lib.merge_config(existing_config, defaults)
        config_lib.write_config(root, merged)

        if new_fields:
            print(f"  + New config fields added: {', '.join(new_fields)}")
        print(f"  + config.yaml merged (SpecFlow v{specflow.__version__})")

        scaffold_lib.copy_checklists(root, _get_package_templates())
        scaffold_lib.copy_adapters_config(root, _get_package_templates())

        if not config_lib.read_state(root):
            config_lib.write_state(root, config_lib.default_state())
            print("  + state.yaml written (was missing)")
    else:
        print("  Creating .specflow/ internals...")
        scaffold_lib.create_internal_dirs(root, _get_package_templates(), overwrite_schemas=_force_overwrite_schemas)

        print("  Creating _specflow/ artifacts directory...")
        scaffold_lib.create_spec_dirs(root)

        config = config_lib.default_config(project_name)
        config_lib.write_config(root, config)
        print(f"  + config.yaml written (project: {project_name})")

        state = config_lib.default_state()
        config_lib.write_state(root, state)
        print("  + state.yaml written")

        # DEC-099: new projects start with the findings ratchet on
        # (an empty baseline, written by the baseline command's routine).
        # F-117: a --force re-init keeps an existing baseline — it is accepted
        # debt, not scaffolding, and emptying it would silently re-arm every
        # accepted finding.
        from specflow.commands.findings_baseline import write_baseline
        from specflow.core.findings_baseline import BASELINE_FILE

        if (root / BASELINE_FILE).exists():
            print(f"  = {BASELINE_FILE} kept (existing accepted findings preserved)")
        else:
            write_baseline(root, set())
            print(f"  + {BASELINE_FILE} written (empty — findings ratchet on)")

    domain = args.get("domain")
    domain_tags_str = args.get("domain_tags", "")
    if domain:
        domain_tags = [t.strip() for t in domain_tags_str.split(",") if t.strip()] if domain_tags_str else []
        config_lib.set_domain(root, domain, domain_tags)
        print(f"  + Domain set: {domain}" + (f" (tags: {', '.join(domain_tags)})" if domain_tags else ""))

    print("  + Schema files copied")

    print("  Copying checklist templates...")
    scaffold_lib.copy_checklists(root, _get_package_templates())
    print("  + Checklist templates copied")

    print("  Copying adapters config...")
    scaffold_lib.copy_adapters_config(root, _get_package_templates())
    print("  + adapters.yaml copied")

    # STORY-685: skills (and legacy cleanup) land BEFORE any context injection,
    # matching refresh, so no cleanup step can run after the blocks are written.
    install_code = plat_lib.get_skills_install_code(platform_code)
    dest = plat_lib.get_skills_install_dir(root, platform_code)
    dest_rel = dest.relative_to(root)
    if install_code != platform_code:
        print(f"  Installing skills for {platform_name} into {dest_rel} "
              f"(shared with {install_code}; not copying a second tree)...")
    else:
        print(f"  Installing skills for {platform_name}...")
    _install_skills(root, platform_code)
    skills_src = _get_package_templates() / "skills" / "shared"
    for skill_dir in sorted(skills_src.iterdir()):
        if skill_dir.is_dir():
            print(f"  + {skill_dir.name}")
    leftovers = plat_lib.leftover_specflow_skills(root, platform_code)
    if leftovers:
        print(
            f"  ! Leftover SpecFlow skills in {plat_lib.get_skills_dir(root, platform_code).relative_to(root)} "
            f"({', '.join(leftovers)}) would override {dest_rel} on OpenCode — remove them."
        )

    if scaffold_lib.inject_base_context(root, _get_package_templates(), platform_code):
        print("  + SpecFlow instructions injected into your instruction file.")

    preset_str = args.get("preset")
    if preset_str:
        presets = [p.strip() for p in preset_str.split(",") if p.strip()]
        for preset in presets:
            print(f"  Applying preset pack '{preset}'...")
            if _apply_preset(root, preset, platform_code) != 0:
                return 1

    with_types = args.get("with_types", "")
    if with_types:
        type_names = [t.strip() for t in with_types.split(",") if t.strip()]
        if type_names:
            print(f"  Installing optional artifact types: {', '.join(type_names)}...")
            if _install_optional_types(root, type_names, force=force) != 0:
                return 1

    _install_pre_commit_hook(root)

    _render_codeowners(root)

    # STORY-668: provenance stamping follows the schema and pack assets landed
    # during init/re-init, and is safe to repeat on every invocation.
    from specflow.lib.practices import migrate_practices
    migration = migrate_practices(root)
    if migration.get("status_map_repaired"):
        print("  + Repaired best-practice status map to transitional values")
    if migration.get("stamped"):
        print(
            f"  + Migrated provenance on {len(migration['stamped'])} "
            "best-practice artifact(s)"
        )
    for warning in migration.get("warnings", []):
        print(f"  ! Practice migration: {warning}")
    for error in migration.get("errors", []):
        print(f"  ! Practice migration failed: {error}")

    want_ci = not args.get("no_ci", False)
    if want_ci:
        _install_ci_workflow(root)

    warning = _multi_platform_warning(root, platform_code, explicit_platform)
    if warning:
        print(f"\n  {warning}")

    print(f"\n+ SpecFlow initialized in {root}")
    print(f"  Platform: {platform_name}")
    print("  Run 'specflow status' to see the project dashboard.")
    return 0


def _install_pre_commit_hook(root: Path) -> None:
    """Install the pre-commit hook via the installer shared with ``specflow hook install``.

    Resolves the hooks directory through git (linked worktrees, core.hooksPath),
    never replaces a hook specflow does not own, and reports what happened.
    """
    from specflow.commands import hook as hook_cmd

    res = hook_cmd.install_pre_commit_hook(root, force=False)
    status, display = res["status"], res["display"]
    if status == "not-git":
        print("  ! Not a git repository (or not its top level) -- run `specflow hook install` after `git init`")
        return
    if status == "refused-hooks-path":
        print(f"  ! core.hooksPath={res['hooks_path']} is set in your {res['hooks_path_scope']} "
              f"git config -- not installing a machine-wide hook")
        print(f"    (set a repo-local core.hooksPath, or install anyway: {hook_cmd.FORCE_HINT})")
        return
    if status == "refused":
        print(f"  ! {display} exists and is not specflow-owned -- leaving as-is")
        print(f"    (replace it after a backup: {hook_cmd.FORCE_HINT})")
        return
    if res["backup"] is not None:
        print(f"  ! Backed up the previous hook to {hook_cmd._display_path(root, res['backup'])}")
    if status == "unchanged":
        print(f"  = {display} already up to date")
    else:
        print(f"  + Installed {display}")
    if res["hooks_path"]:
        print(f"    note: core.hooksPath={res['hooks_path']} -- git runs hooks from there")


def _render_codeowners(root: Path) -> None:
    body = rbac_lib.render_codeowners(root)
    if not body:
        return
    target = root / "CODEOWNERS"
    if target.exists():
        print(f"  ! CODEOWNERS already exists -- leaving as-is")
        return
    target.write_text(body, encoding="utf-8")
    print(f"  + Generated CODEOWNERS")


def _install_ci_workflow(root: Path) -> None:
    config = load_adapters_config(root)
    ci_cfg = config.get("ci") or {}
    provider = ci_cfg.get("provider")

    if not provider:
        return

    try:
        adapter = get_adapter(provider)
    except ValueError:
        return

    if "generate_ci_workflow" not in adapter.supported_operations:
        return

    ops = ci_cfg.get("operations", []) or []
    if not ops:
        return

    files = adapter.generate_ci_workflow(ops)
    for rel_path, content in files.items():
        out_path = root / rel_path
        if out_path.exists():
            print(f"  ! {rel_path} already exists -- leaving as-is")
            continue
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        print(f"  + Generated {rel_path}")
