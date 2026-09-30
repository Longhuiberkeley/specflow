"""refresh moves the generated CI workflow's SpecFlow pin forward (STORY-705 AC2)."""

from __future__ import annotations

from pathlib import Path

import specflow
from specflow.commands import refresh as refresh_cmd
from specflow.lib.adapters.github_actions import WORKFLOW_PATH, bump_workflow_pin

REPO = "git+https://github.com/Longhuiberkeley/specflow"


def _project(tmp_path: Path, workflow: str) -> Path:
    root = tmp_path / "p"
    (root / ".claude").mkdir(parents=True)
    (root / ".specflow").mkdir()
    (root / ".specflow" / "config.yaml").write_text("format_version: 1\nactive_packs: []\n")
    wf = root / WORKFLOW_PATH
    wf.parent.mkdir(parents=True)
    wf.write_text(workflow)
    return root


def _wf(*refs: str) -> str:
    return "".join(f"      - run: uvx --from {REPO}@{r} specflow artifact-lint\n" for r in refs)


def test_old_release_pins_bumped_to_running_version(tmp_path: Path, capsys):
    root = _project(tmp_path, "name: SpecFlow\n" + _wf("v1.14.7", "v1.14.7"))
    assert refresh_cmd.run(root, {"no_skills": True, "no_context": True}) == 0
    text = (root / WORKFLOW_PATH).read_text()
    assert text.count(f"{REPO}@v{specflow.__version__}") == 2
    assert "v1.14.7" not in text
    assert "name: SpecFlow" in text, "only the pin changes"
    assert f"v1.14.7 → v{specflow.__version__} (2)" in capsys.readouterr().out


def test_dry_run_reports_without_writing(tmp_path: Path, capsys):
    root = _project(tmp_path, _wf("v1.14.7"))
    assert refresh_cmd.run(root, {"dry_run": True, "no_skills": True, "no_context": True}) == 0
    assert "v1.14.7" in (root / WORKFLOW_PATH).read_text()
    assert "would bump" in capsys.readouterr().out


def test_never_downgrades_a_newer_pin(tmp_path: Path):
    root = _project(tmp_path, _wf("v99.0.0"))
    assert bump_workflow_pin(root)["count"] == 0
    assert "v99.0.0" in (root / WORKFLOW_PATH).read_text()


def test_branch_and_sha_pins_left_and_reported(tmp_path: Path):
    root = _project(tmp_path, _wf("main", "0123abcd", "v1.0.0"))
    result = bump_workflow_pin(root)
    text = (root / WORKFLOW_PATH).read_text()
    assert result["skipped"] == ["0123abcd", "main"]
    assert result["count"] == 1
    assert f"{REPO}@main" in text and f"{REPO}@0123abcd" in text


def test_other_repos_untouched(tmp_path: Path):
    fork = "      - run: uvx --from git+https://github.com/someone/specflow@v1.0.0 specflow x\n"
    root = _project(tmp_path, fork)
    assert bump_workflow_pin(root)["count"] == 0
    assert (root / WORKFLOW_PATH).read_text() == fork


def test_no_workflow_is_a_noop(tmp_path: Path):
    root = tmp_path / "p"
    root.mkdir()
    assert bump_workflow_pin(root) == {"old": [], "new": None, "count": 0, "skipped": []}
