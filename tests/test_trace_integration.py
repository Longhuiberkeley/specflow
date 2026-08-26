"""STORY-637 (v1.14.2): integration-level assertions on the REAL dogfood repo.

IT-038's contract claims that `specflow trace STORY-632` renders its actual
chain — REQ-005/REQ-001 upstream via `implements`, DEC-077 via `guided_by`,
and UT-069/IT-037/QT-044 downstream via `verified_by`. An exit-code-only
`verify_command` cannot prove rendered content; these tests do. They run the
real CLI against the real `_specflow/` tree, so they live in this repo only
(and are skipped if the dogfood artifacts are absent, e.g. in a source
export without `_specflow/`).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_STORY = _REPO_ROOT / "_specflow/work/stories/STORY-632.md"

pytestmark = pytest.mark.skipif(
    not _STORY.exists(), reason="dogfood _specflow/ tree not present"
)


def _trace(artifact_id: str) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "specflow", "trace", artifact_id],
        capture_output=True, text=True, cwd=_REPO_ROOT,
    )
    assert result.returncode == 0, f"trace {artifact_id} failed:\n{result.stderr}"
    return result.stdout


class TestTraceStory632Integration:
    def test_implements_links_render_upstream(self):
        out = _trace("STORY-632")
        for req in ("REQ-005", "REQ-001"):
            assert req in out, f"{req} missing from STORY-632 upstream"
            row = next(l for l in out.splitlines() if req in l)
            assert "(implements)" in row, f"{req} not rendered via implements"

    def test_decision_renders_upstream_via_guided_by(self):
        out = _trace("STORY-632")
        assert "DEC-077" in out
        row = next(l for l in out.splitlines() if "DEC-077" in l)
        assert "(guided_by)" in row

    def test_verification_contracts_render_downstream(self):
        out = _trace("STORY-632")
        for test_id in ("UT-069", "IT-037", "QT-044"):
            assert test_id in out, f"{test_id} missing from STORY-632 downstream"
