"""Platform detection logic for SpecFlow init."""

import os
from pathlib import Path


# Platform identifiers: directory name -> platform label
PLATFORM_DIRS = {
    ".claude": "Claude Code",
    ".opencode": "OpenCode",
    ".gemini": "Gemini CLI",
}


def detect_platform(root: Path) -> str | None:
    """Detect which AI code platform is in use based on existing directories.

    Returns the platform label (e.g. 'Claude Code') or None if not detected.
    """
    for dir_name, label in PLATFORM_DIRS.items():
        if (root / dir_name).exists():
            return label
    return None


def get_skills_platform_dir(platform: str) -> str:
    """Return the skills subdirectory name for a given platform."""
    for dir_name, label in PLATFORM_DIRS.items():
        if label == platform:
            return dir_name
    # Default to claude if unknown
    return "claude"


def get_skill_names() -> list[str]:
    """Return the list of skill names to install."""
    return ["specflow-discover", "specflow-plan", "specflow-execute", "specflow-artifact-review"]
