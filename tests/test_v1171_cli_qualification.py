"""v1.17.1 qualification: the real `specflow` CLI, end to end, per story.

Each class drives subprocesses exactly as a user or CI would (STORY-701..705).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import specflow

ENV = {**os.environ, "NO_COLOR": "1"}


def _sf(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "specflow", *args], cwd=root, env=ENV,
                          capture_output=True, text=True)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "p"
    (root / ".claude").mkdir(parents=True)
    assert _sf(root, "init", "--platform", "claude-code").returncode == 0
    return root


def _story(root: Path, sid: str, **extra) -> Path:
    fm = {"id": sid, "title": sid, "type": "story", "status": "draft", "links": [],
          "created": "2026-09-30", **extra}
    path = root / "_specflow" / "work" / "stories" / f"{sid}.md"
    path.write_text(f"---\n{yaml.safe_dump(fm)}---\n\n## Acceptance Criteria\n\n1. a\n2. b\n")
    return path


class TestRatchetCli:
    """STORY-705 / REQ-053 AC7-AC8: the ratchet through the CLI."""

    def test_new_debt_fails_ci_until_fixed_or_accepted(self, project: Path):
        assert _sf(project, "artifact-lint").returncode == 0
        path = _story(project, "STORY-001")
        lint = _sf(project, "artifact-lint")
        assert lint.returncode == 1 and "[links/orphan] STORY-001" in lint.stdout
        assert _sf(project, "findings-baseline", "update").returncode == 1
        assert _sf(project, "findings-baseline", "update", "--accept-new").returncode == 0
        assert _sf(project, "artifact-lint").returncode == 0
        path.unlink()
        assert "no longer produced" in _sf(project, "artifact-lint").stdout
        assert _sf(project, "findings-baseline", "update").returncode == 0
        assert _sf(project, "findings-baseline", "diff").returncode == 0


class TestTypedFindingsCli:
    """STORY-704 / REQ-053 AC3-AC4: rendered text unchanged, findings keyed per kind."""

    def test_two_problems_one_artifact_two_new_keys(self, project: Path):
        _story(project, "STORY-001", output_files=["src/a.py", "src/b.py"])
        out = _sf(project, "artifact-lint").stdout
        assert "output file not found: src/a.py" in out
        assert "[output-files/missing] STORY-001 src/a.py" in out
        assert "[output-files/missing] STORY-001 src/b.py" in out


class TestReadOnlyLintCli:
    """STORY-703 / REQ-053 AC2, AC9."""

    def test_lint_leaves_specflow_untouched_and_records_inputs(self, project: Path):
        src = project / "src" / "m.py"
        src.parent.mkdir()
        src.write_text("x = 1\n")
        _story(project, "STORY-001", output_files=["src/m.py"])
        before = sorted((p, p.read_bytes()) for p in (project / ".specflow").rglob("*") if p.is_file())
        out = _sf(project, "artifact-lint", "--as-of", "2026-09-30").stdout
        after = sorted((p, p.read_bytes()) for p in (project / ".specflow").rglob("*") if p.is_file())
        assert before == after
        assert "Inputs: as-of 2026-09-30" in out
        assert _sf(project, "fingerprint-refresh", "--source").returncode == 0
        src.write_text("x = 2\n")
        assert "source file changed: src/m.py" in _sf(project, "artifact-lint").stdout


class TestGeminiRetiredCli:
    """STORY-701 / DEC-094."""

    def test_platform_gemini_rejected_cleanly(self, tmp_path: Path):
        root = tmp_path / "g"
        (root / ".gemini").mkdir(parents=True)
        for cmd in (["init", "--platform", "gemini"], ["refresh", "--platform", "gemini"]):
            proc = _sf(root, *cmd)
            assert proc.returncode == 1, cmd
            assert "Traceback" not in proc.stderr
        assert not (root / "GEMINI.md").exists()


class TestConfigAndPinCli:
    """STORY-702: legacy version key stripped; CI pin moved forward."""

    def test_refresh_strips_version_and_bumps_pin(self, project: Path):
        cfg = project / ".specflow" / "config.yaml"
        cfg.write_text("version: 1.15.0\n" + cfg.read_text())
        wf = project / ".github" / "workflows" / "specflow.yml"
        wf.parent.mkdir(parents=True, exist_ok=True)
        wf.write_text("- run: uvx --from git+https://github.com/Longhuiberkeley/specflow@v1.14.7 specflow x\n")
        proc = _sf(project, "refresh", "--no-skills", "--no-context")
        assert proc.returncode == 0
        assert "version" not in yaml.safe_load(cfg.read_text())
        assert f"specflow@v{specflow.__version__}" in wf.read_text()
