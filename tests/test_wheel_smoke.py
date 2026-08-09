"""Tests for wheel packaging completeness.

Builds the wheel once per test session and asserts every file under
``src/specflow/`` ships in the wheel — schemas, skills including their
``references/`` trees, checklists, packs, agent-context, adapters, platforms,
and Python modules. This is the fast, offline half of the wheel smoke; the
full isolated-install + init + brief/status pass lives in
``scripts/wheel_smoke.py`` (run by CI and before releases via
``scripts/wheel-smoke.sh``).
"""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
SRC_DIR = REPO_ROOT / "src" / "specflow"

_spec = importlib.util.spec_from_file_location(
    "wheel_smoke", SCRIPTS_DIR / "wheel_smoke.py"
)
assert _spec is not None and _spec.loader is not None, "could not locate wheel_smoke.py"
wheel_smoke = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wheel_smoke)


@pytest.fixture(scope="session")
def wheel_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if shutil.which("uv") is None:
        pytest.skip("uv not available on PATH")
    out_dir = tmp_path_factory.mktemp("wheel")
    return wheel_smoke.build_wheel(out_dir)


def test_wheel_contains_every_source_asset(wheel_path: Path) -> None:
    missing = wheel_smoke.verify_wheel_contents(wheel_path, SRC_DIR)
    assert not missing, (
        "wheel is missing packaged assets:\n" + "\n".join(missing)
    )


def test_wheel_asset_signals_present(wheel_path: Path) -> None:
    signals = wheel_smoke.verify_asset_signals(wheel_path)
    assert not signals, "wheel asset checks failed:\n" + "\n".join(signals)


def test_wheel_agent_context_is_nonempty(wheel_path: Path) -> None:
    with __import__("zipfile").ZipFile(wheel_path) as zf:
        info = zf.getinfo("specflow/templates/agent-context.md")
        assert info.file_size > 0, "agent-context.md is empty in the wheel"
