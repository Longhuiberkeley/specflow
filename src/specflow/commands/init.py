"""specflow init — Scaffold a SpecFlow project."""

import shutil
import stat
from pathlib import Path

import yaml

from specflow.lib import platform as plat_lib
from specflow.lib import rbac as rbac_lib
from specflow.lib import scaffold as scaffold_lib
from specflow.lib import config as config_lib
from specflow.lib.adapters import load_adapters_config, get_adapter


def _get_packs_dir() -> Path:
    return Path(__file__).parent.parent / "packs"


def _apply_preset(root: Path, preset: str) -> int:
    packs_dir = _get_packs_dir()
    result = scaffold_lib.apply_pack(root, preset, packs_dir)
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

    pieces = []
    if types_added:
        pieces.append(f"{len(types_added)} artifact type(s)")
    standards_added = result.get("standards_added", []) or []
    if standards_added:
        pieces.append(f"{len(standards_added)} standard(s)")
    detail = ", ".join(pieces) if pieces else "no new items"
    print(f"  + Pack '{preset}' applied ({detail})")
    return 0


def _get_package_templates() -> Path:
    return Path(__file__).parent.parent / "templates"


def _install_skills(root: Path, platform_code: str) -> None:
    template_dir = _get_package_templates()
    skills_src = template_dir / "skills" / "shared"
    skills_dst = plat_lib.get_skills_dir(root, platform_code)

    skills_dst.mkdir(parents=True, exist_ok=True)

    cfg = plat_lib.get_platform(platform_code)
    legacy = cfg.get("legacy_dirs", []) if cfg else []
    for legacy_dir in legacy:
        legacy_path = root / legacy_dir
        if legacy_path.exists():
            shutil.rmtree(str(legacy_path), ignore_errors=True)

    for skill_dir in skills_src.iterdir():
        if skill_dir.is_dir():
            dst = skills_dst / skill_dir.name
            if dst.exists():
                shutil.rmtree(str(dst))
            shutil.copytree(str(skill_dir), str(dst))


def run(root: Path, args: dict) -> int:
    root = root.resolve()

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

    print("  Creating .specflow/ internals...")
    scaffold_lib.create_internal_dirs(root, _get_package_templates())

    print("  Creating _specflow/ artifacts directory...")
    scaffold_lib.create_spec_dirs(root)

    config = config_lib.default_config(project_name)
    config_lib.write_config(root, config)
    print(f"  + config.yaml written (project: {project_name})")

    state = config_lib.default_state()
    config_lib.write_state(root, state)
    print("  + state.yaml written")

    print("  + Schema files copied")

    print("  Copying checklist templates...")
    scaffold_lib.copy_checklists(root, _get_package_templates())
    print("  + Checklist templates copied")

    print("  Copying adapters config...")
    scaffold_lib.copy_adapters_config(root, _get_package_templates())
    print("  + adapters.yaml copied")

    preset = args.get("preset")
    if preset:
        print(f"  Applying preset pack '{preset}'...")
        if _apply_preset(root, preset) != 0:
            return 1

    print(f"  Installing skills for {platform_name}...")
    _install_skills(root, platform_code)
    skills_src = _get_package_templates() / "skills" / "shared"
    for skill_dir in sorted(skills_src.iterdir()):
        if skill_dir.is_dir():
            print(f"  + {skill_dir.name}")

    _install_pre_commit_hook(root)

    _render_codeowners(root)

    want_ci = not args.get("no_ci", False)
    if want_ci:
        _install_ci_workflow(root)

    print(f"\n+ SpecFlow initialized in {root}")
    print(f"  Platform: {platform_name}")
    print("  Next: your AI assistant will inject SpecFlow instructions into your instruction file.")
    print("  Run 'specflow status' to see the project dashboard.")
    return 0


def _install_pre_commit_hook(root: Path) -> None:
    git_dir = root / ".git"
    if not git_dir.is_dir():
        return
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "pre-commit"
    if hook_path.exists() and "specflow hook pre-commit" not in hook_path.read_text(encoding="utf-8", errors="ignore"):
        print(f"  ! .git/hooks/pre-commit exists and is not specflow-owned -- leaving as-is")
        return
    hook_path.write_text(
        "#!/usr/bin/env bash\n"
        "# specflow pre-commit hook -- installed by `specflow init`\n"
        "exec uv run specflow hook pre-commit \"$@\"\n",
        encoding="utf-8",
    )
    mode = hook_path.stat().st_mode
    hook_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"  + Installed .git/hooks/pre-commit")


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
