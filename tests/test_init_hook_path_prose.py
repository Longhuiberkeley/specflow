"""Pins for STORY-747 prose fixes in shipped skill text (SPIKE-008)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TREES = [
    ROOT / ".claude" / "skills",
    ROOT / "src" / "specflow" / "templates" / "skills" / "shared",
]


def test_init_skill_hook_step_honors_hooks_path():
    # SPIKE-008 R1-090 -- hook.py installs where git runs hooks (core.hooksPath aware)
    for tree in TREES:
        text = (tree / "specflow-init" / "SKILL.md").read_text()
        assert "+ Installed .git/hooks/pre-commit" not in text
        assert "+ Installed <hooks-dir>/pre-commit" in text
        assert "it honors `core.hooksPath`" in text
