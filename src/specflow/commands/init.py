"""specflow init — Scaffold a SpecFlow project."""

import shutil
from pathlib import Path

import yaml

from specflow.lib import platform as plat_lib
from specflow.lib import scaffold as scaffold_lib
from specflow.lib import config as config_lib


def _get_package_templates() -> Path:
    """Return the path to the bundled templates inside the package."""
    return Path(__file__).parent.parent / "templates"


def _install_skills(root: Path, platform_label: str) -> None:
    """Copy skill facades to the detected platform's skills directory."""
    template_dir = _get_package_templates()
    skills_src = template_dir / "skills"

    platform_key = plat_lib.get_skills_platform_dir(platform_label)
    skills_dst = root / ".claude"  # default

    # Determine destination based on platform
    platform_dirs = {
        ".claude": "Claude Code",
        ".opencode": "OpenCode",
        ".gemini": "Gemini CLI",
    }
    for dir_name, label in platform_dirs.items():
        if label == platform_label:
            skills_dst = root / dir_name
            break

    skills_dst = skills_dst / "skills"
    skills_dst.mkdir(parents=True, exist_ok=True)

    # Copy skill directories
    if not (skills_src / platform_key).exists():
        platform_key = "claude"  # fallback

    src = skills_src / platform_key
    for skill_dir in src.iterdir():
        if skill_dir.is_dir():
            dst = skills_dst / skill_dir.name
            if dst.exists():
                shutil.rmtree(str(dst))
            shutil.copytree(str(skill_dir), str(dst))


def _append_agents_section(root: Path, target_file: str) -> None:
    """Append the SpecFlow section to the chosen instruction file."""
    template_dir = _get_package_templates()
    section_path = template_dir / "agents-section.md"
    section_content = section_path.read_text(encoding="utf-8")

    target = root / target_file
    header = "\n\n<!-- SpecFlow section (auto-generated, do not edit manually) -->\n"
    footer = "\n<!-- End SpecFlow section -->\n"

    if target.exists():
        existing = target.read_text(encoding="utf-8")
        if "SpecFlow section" in existing:
            # Already has a SpecFlow section
            print(f"  ⚠ SpecFlow section already exists in {target_file}")
            return
        target.write_text(existing + header + section_content + footer, encoding="utf-8")
    else:
        target.write_text(header + section_content + footer, encoding="utf-8")
    print(f"  ✓ Appended SpecFlow section to {target_file}")


def run(root: Path, args: dict) -> int:
    """Execute specflow init.

    Args:
        root: Project root directory
        args: Parsed arguments (currently unused, reserved for future options)

    Returns:
        Exit code (0 = success, 1 = error)
    """
    root = root.resolve()

    # 1. Detect platform
    platform_label = plat_lib.detect_platform(root)
    if platform_label is None:
        print("No AI code platform detected (.claude/, .opencode/, .gemini/).")
        # Default to Claude Code
        platform_label = "Claude Code"
        print(f"  Defaulting to: {platform_label}")
    else:
        print(f"  ✓ Detected platform: {platform_label}")

    # 2. Determine instruction file to append to
    instruction_file = "AGENTS.md"
    if (root / "CLAUDE.md").exists() and not (root / "AGENTS.md").exists():
        instruction_file = "CLAUDE.md"
    print(f"  → Using instruction file: {instruction_file}")

    # 3. Determine project name
    project_name = root.name

    # 4. Create .specflow/ structure
    print("  Creating .specflow/ internals...")
    scaffold_lib.create_internal_dirs(root, _get_package_templates())

    # 5. Create _specflow/ structure
    print("  Creating _specflow/ artifacts directory...")
    scaffold_lib.create_spec_dirs(root)

    # 6. Write config and state
    config = config_lib.default_config(project_name)
    config_lib.write_config(root, config)
    print(f"  ✓ config.yaml written (project: {project_name})")

    state = config_lib.default_state()
    config_lib.write_state(root, state)
    print("  ✓ state.yaml written")

    # 7. Copy schemas (already done in create_internal_dirs)
    print("  ✓ Schema files copied")

    # 8. Copy checklist templates
    print("  Copying checklist templates...")
    scaffold_lib.copy_checklists(root, _get_package_templates())
    print("  ✓ Checklist templates copied")

    # 9. Append AGENTS.md section
    _append_agents_section(root, instruction_file)

    # 10. Install skills
    print(f"  Installing skills for {platform_label}...")
    _install_skills(root, platform_label)
    skill_names = plat_lib.get_skill_names()
    for name in skill_names:
        print(f"  ✓ {name}")

    print(f"\n✓ SpecFlow initialized in {root}")
    print("  Run 'uv run specflow status' to see the project dashboard.")
    return 0
