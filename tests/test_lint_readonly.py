"""artifact-lint is read-only and deterministic (STORY-703/705, REQ-053 AC1/AC2/AC9) — integration."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

from specflow.commands import artifact_lint as lint_cmd
from specflow.commands import init as init_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import source_drift


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "p"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    pkg = root / "src" / "pkg"
    pkg.mkdir(parents=True)
    for name in ("a.py", "b.py", "c.py", "d.py"):
        (pkg / name).write_text(f"# {name}\n")
    for sid, of in (("STORY-001", ["src/pkg/*.py"]), ("STORY-002", ["src/gone.py"])):
        fm = {"id": sid, "title": sid, "type": "story", "status": "draft",
              "links": [], "output_files": of}
        (root / "_specflow" / "work" / "stories" / f"{sid}.md").write_text(
            f"---\n{yaml.safe_dump(fm)}---\n\n## Acceptance Criteria\n\n1. a\n2. b\n")
    return root


def _snapshot(root: Path) -> dict[str, str]:
    base = root / ".specflow"
    return {
        str(p.relative_to(base)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(base.rglob("*")) if p.is_file()
    }


def test_full_lint_writes_nothing_without_store(project: Path):
    before = _snapshot(project)
    lint_cmd.run(project, {})
    assert _snapshot(project) == before
    assert not (project / ".specflow" / "source-fingerprints.yaml").exists()


def test_full_lint_writes_nothing_with_store_and_drift(project: Path):
    source_drift.seed(project)
    (project / "src" / "pkg" / "a.py").write_text("# changed\n")
    before = _snapshot(project)
    lint_cmd.run(project, {})
    assert _snapshot(project) == before


def _lint_subprocess(root: Path, seed: str) -> tuple[int, str]:
    env = {**os.environ, "PYTHONHASHSEED": seed, "NO_COLOR": "1"}
    proc = subprocess.run(
        [sys.executable, "-m", "specflow", "artifact-lint", "--as-of", "2026-09-30"],
        cwd=root, env=env, capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout


def test_identical_output_across_runs_and_hash_seeds(project: Path):
    """AC1: same repo + as-of → identical output and exit code."""
    source_drift.seed(project)
    for name in ("a.py", "c.py", "d.py"):
        (project / "src" / "pkg" / name).write_text("# drifted\n")
    first = _lint_subprocess(project, "1")
    assert first == _lint_subprocess(project, "1")
    assert first == _lint_subprocess(project, "2")
    assert "source file changed" in first[1]


def test_as_of_drives_spike_staleness_as_accounting(project: Path):
    fm = {"id": "SPIKE-001", "title": "s", "type": "spike", "status": "draft",
          "links": [], "created": "2026-01-01", "timebox": 10}
    (project / "_specflow" / "work" / "spikes").mkdir(parents=True, exist_ok=True)
    (project / "_specflow" / "work" / "spikes" / "SPIKE-001.md").write_text(
        f"---\n{yaml.safe_dump(fm)}---\n\nbody\n")
    arts = art_lib.discover_artifacts(project)
    early = lint_cmd._check_spike_lifecycle(arts, project, date(2026, 1, 5))
    late = lint_cmd._check_spike_lifecycle(arts, project, date(2026, 3, 1))
    assert early["warning_count"] == 0
    assert late["warning_count"] == 1
    (finding,) = late["findings"]
    assert finding.klass == "accounting"
    assert dict(finding.args)["as_of"] == "2026-03-01"


def test_inputs_line_records_as_of_and_store(project: Path, capsys):
    lint_cmd.run(project, {"as_of": "2026-09-30"})
    out = capsys.readouterr().out
    assert "Inputs: as-of 2026-09-30; source-drift store: 0 artifact(s) seeded, 1 unseeded" in out


def test_bad_as_of_rejected(project: Path):
    assert lint_cmd.run(project, {"as_of": "30/09/2026"}) == 1
