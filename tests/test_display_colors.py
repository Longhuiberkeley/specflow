"""F-023: ANSI colour honours NO_COLOR / FORCE_COLOR / non-TTY stdout."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PROBE = "from specflow.lib.display import RED, NC; import sys; sys.stdout.write(repr(RED + 'x' + NC))"


def _probe(**env: str) -> str:
    base = {k: v for k, v in os.environ.items() if k not in ("NO_COLOR", "FORCE_COLOR")}
    base.update(env)
    base.setdefault("PYTHONPATH", str(ROOT / "src"))
    out = subprocess.run([sys.executable, "-c", PROBE], capture_output=True, text=True, env=base, check=True)
    return out.stdout


def test_piped_stdout_has_no_escapes():
    assert _probe() == "'x'"


def test_no_color_disables_even_with_tty_like_force_absent():
    assert _probe(NO_COLOR="1") == "'x'"


def test_force_color_enables_when_piped():
    assert "\\x1b[0;31m" in _probe(FORCE_COLOR="1")


def test_no_color_beats_nothing_but_force_color_wins():
    assert "\\x1b[" in _probe(FORCE_COLOR="1", NO_COLOR="1")
    assert _probe(FORCE_COLOR="0", NO_COLOR="1") == "'x'"


@pytest.mark.slow
def test_cli_output_piped_is_plain(tmp_path: Path):
    """End to end: a piped `specflow artifact-lint` carries no escape sequences."""
    from specflow.commands import init as init_cmd

    root = tmp_path / "p"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    env = {k: v for k, v in os.environ.items() if k not in ("NO_COLOR", "FORCE_COLOR")}
    env["PYTHONPATH"] = str(ROOT / "src")
    out = subprocess.run([sys.executable, "-m", "specflow", "artifact-lint"], cwd=root, capture_output=True, text=True, env=env)
    assert "\x1b[" not in out.stdout + out.stderr, out.stdout[:400]
