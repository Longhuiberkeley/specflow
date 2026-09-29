"""STORY-687 AC3 (scaffold part) — readiness/ checklists are gone from
templates and from the init scaffold."""

from __future__ import annotations

from pathlib import Path

from specflow.commands import init as init_cmd
from specflow.lib import scaffold as scaffold_lib

_TEMPLATES = Path(init_cmd.__file__).parent.parent / "templates"


def test_readiness_templates_deleted():
    assert not (_TEMPLATES / "checklists" / "readiness").exists()


def test_scaffold_no_longer_creates_readiness_dir():
    assert "checklists/readiness" not in scaffold_lib.INTERNAL_DIRS


def test_init_does_not_create_readiness_checklists(tmp_path: Path):
    root = tmp_path / "p"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    assert not (root / ".specflow" / "checklists" / "readiness").exists()
    assert (root / ".specflow" / "checklists" / "phase-gates").is_dir()
