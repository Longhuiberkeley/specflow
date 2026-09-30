"""findings-baseline command, init/refresh migration (STORY-705, REQ-053 AC7/AC8) — integration."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from specflow.commands import artifact_lint as lint_cmd
from specflow.commands import findings_baseline as fb_cmd
from specflow.commands import init as init_cmd
from specflow.commands import refresh as refresh_cmd
from specflow.core import findings_baseline as fb
from specflow.lib import locks


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "p"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    return root


def _orphan(root: Path, sid: str = "STORY-001") -> Path:
    fm = {"id": sid, "title": sid, "type": "story", "status": "draft", "links": []}
    path = root / "_specflow" / "work" / "stories" / f"{sid}.md"
    path.write_text(f"---\n{yaml.safe_dump(fm)}---\n\n## Acceptance Criteria\n\n1. a\n2. b\n")
    return path


def _update(root: Path, **kw) -> int:
    return fb_cmd.run(root, {"findings_baseline_subcommand": "update", **kw})


def test_init_writes_empty_baseline(project: Path):
    keys, err = fb.load(project)
    assert err is None and keys == frozenset()


def test_update_refuses_new_without_flag_and_writes_nothing(project: Path, capsys):
    before = fb.baseline_path(project).read_bytes()
    _orphan(project)
    assert _update(project) == 1
    assert fb.baseline_path(project).read_bytes() == before
    assert "nothing written" in capsys.readouterr().out


def test_accept_new_prints_additions_and_is_idempotent(project: Path, capsys):
    _orphan(project)
    capsys.readouterr()
    assert _update(project, accept_new=True) == 0
    out = capsys.readouterr().out
    assert "+ [links/orphan] STORY-001" in out
    first = fb.baseline_path(project).read_bytes()
    assert _update(project) == 0
    assert fb.baseline_path(project).read_bytes() == first, "byte-idempotent"


def test_update_ratchets_down_on_resolved(project: Path):
    path = _orphan(project)
    assert _update(project, accept_new=True) == 0
    path.unlink()
    assert _update(project) == 0
    keys, _ = fb.load(project)
    assert keys == frozenset()


def test_seed_when_absent(project: Path):
    fb.baseline_path(project).unlink()
    _orphan(project)
    assert _update(project) == 0
    keys, _ = fb.load(project)
    assert ("links/orphan", ("STORY-001",)) in keys


def test_diff_is_read_only(project: Path):
    _orphan(project)
    before = fb.baseline_path(project).read_bytes()
    assert fb_cmd.run(project, {"findings_baseline_subcommand": "diff"}) == 1
    assert fb.baseline_path(project).read_bytes() == before


def test_write_requires_mutation_lock(project: Path):
    with pytest.raises(locks.MutationLockNotHeld):
        locks.atomic_write(fb.baseline_path(project), fb.dumps(frozenset()))


def test_refresh_removes_legacy_history_without_seeding(project: Path, capsys):
    fb.baseline_path(project).unlink()
    legacy = project / lint_cmd.LEGACY_HISTORY_FILE
    legacy.write_text("links: {abc: 7}\n")
    (project / ".claude").mkdir(exist_ok=True)
    assert refresh_cmd.run(project, {"dry_run": True, "no_skills": True, "no_context": True}) == 0
    assert legacy.exists()
    assert refresh_cmd.run(project, {"no_skills": True, "no_context": True}) == 0
    out = capsys.readouterr().out
    assert not legacy.exists()
    assert not fb.baseline_path(project).exists(), "refresh never seeds the baseline"
    assert "findings-baseline update" in out


def test_refresh_seeds_absent_source_store(project: Path):
    src = project / "src" / "m.py"
    src.parent.mkdir()
    src.write_text("x = 1\n")
    fm = {"id": "STORY-001", "title": "s", "type": "story", "status": "draft",
          "links": [], "output_files": ["src/m.py"]}
    (project / "_specflow" / "work" / "stories" / "STORY-001.md").write_text(
        f"---\n{yaml.safe_dump(fm)}---\n\n## Acceptance Criteria\n\n1. a\n2. b\n")
    (project / ".claude").mkdir(exist_ok=True)
    assert refresh_cmd.run(project, {"no_skills": True, "no_context": True}) == 0
    store = yaml.safe_load((project / ".specflow" / "source-fingerprints.yaml").read_text())
    assert "src/m.py" in store["STORY-001"]
