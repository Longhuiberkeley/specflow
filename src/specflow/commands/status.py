"""specflow status — Show project dashboard."""

from pathlib import Path

import yaml

from specflow.lib import config as config_lib


def _count_artifacts(root: Path) -> dict[str, int]:
    """Count artifact files in each _specflow/ subdirectory."""
    counts: dict[str, int] = {}
    specflow_dir = root / "_specflow"
    if not specflow_dir.exists():
        return counts

    for d in sorted(specflow_dir.rglob("*")):
        if d.is_dir() and d.name not in ("specs", "work"):
            md_count = len(list(d.glob("*.md")))
            rel = str(d.relative_to(specflow_dir))
            if md_count > 0:
                counts[rel] = md_count

    return counts


def _count_issues(root: Path) -> int:
    """Count artifacts with suspect=true or invalid status."""
    issues = 0
    specflow_dir = root / "_specflow"
    if not specflow_dir.exists():
        return 0

    for md_file in specflow_dir.rglob("*.md"):
        if md_file.name.startswith("_"):
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            if text.strip().startswith("---"):
                end = text.find("---", 3)
                if end != -1:
                    fm = yaml.safe_load(text[3:end])
                    if isinstance(fm, dict):
                        if fm.get("suspect"):
                            issues += 1
        except Exception:
            pass

    return issues


def run(root: Path, args: dict) -> int:
    """Execute specflow status.

    Args:
        root: Project root directory
        args: Parsed arguments (currently unused)

    Returns:
        Exit code (0 = success, 1 = not initialized)
    """
    root = root.resolve()

    # Check if SpecFlow is initialized
    config = config_lib.read_config(root)
    state = config_lib.read_state(root)

    if not config or not state:
        print("SpecFlow is not initialized in this project.")
        print("Run 'uv run specflow init' to scaffold the project.")
        return 1

    project_name = config.get("project", {}).get("name", "unknown")
    phase = state.get("current", "idle")
    created = config.get("project", {}).get("created", "unknown")

    print(f"\n{'=' * 50}")
    print(f"  SpecFlow — {project_name}")
    print(f"{'=' * 50}")
    print(f"  Phase:     {phase}")
    print(f"  Created:   {created}")

    # Count artifacts
    artifacts = _count_artifacts(root)
    total = sum(artifacts.values())
    print(f"  Artifacts: {total}")

    if artifacts:
        print("\n  By directory:")
        for dir_name, count in sorted(artifacts.items()):
            print(f"    {dir_name}: {count}")

    # Count issues
    issues = _count_issues(root)
    if issues > 0:
        print(f"\n  ⚠ Issues: {issues} artifact(s) flagged as suspect")
    else:
        print(f"\n  ✓ No issues")

    # Suggested next action
    if total == 0:
        print(f"\n  → Suggested: Start with 'specflow-new' to capture your first requirement")
    elif phase == "idle":
        print(f"\n  → Suggested: Run 'specflow-new' to begin discovery")

    print()
    return 0
