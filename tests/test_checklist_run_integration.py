"""Integration: `specflow checklist-run` on a freshly initialised project runs
the shipped story-writing spec-link check (STORY-687 AC1) and honours severity
(STORY-682). Before STORY-687 the shipped story-writing.yaml did not parse, so
CKL-IP-004-01 never ran on any consumer project."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from specflow import cli
from specflow.commands import init as init_cmd


@pytest.fixture
def project(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "p"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    monkeypatch.chdir(root)
    assert cli.main(["create", "--type", "requirement", "--title", "Login",
                     "--body", "## Acceptance Criteria\n1. The system shall log in.\n"]) == 0
    return root


def _latest_log(root: Path, artifact_id: str) -> dict:
    logs = sorted((root / ".specflow" / "checklist-log").glob(f"*check-{artifact_id}.yaml"))
    assert logs, "checklist-run persisted no log"
    return yaml.safe_load(logs[-1].read_text(encoding="utf-8"))


def _result(log: dict, item: str) -> str:
    return next(r["result"] for r in log["results"] if r["item"] == item)


def test_story_with_spec_link_passes_spec_link_check(project: Path, capsys):
    assert cli.main(["create", "--type", "story", "--title", "Log in",
                     "--links", "REQ-001:implements", "--body", "## Acceptance Criteria\n1. Works.\n"]) == 0
    capsys.readouterr()
    rc = cli.main(["checklist-run", "STORY-001"])
    out = capsys.readouterr().out
    log = _latest_log(project, "STORY-001")
    assert _result(log, "CKL-IP-004-01") == "passed"
    assert log["blocking_failures"] == 0
    assert "parse_errors" not in log
    assert "failed to parse" not in out
    assert rc == 0


def test_story_without_spec_link_blocks(project: Path, capsys):
    assert cli.main(["create", "--type", "story", "--title", "Orphan", "--body", "## Acceptance Criteria\n1. Works.\n"]) == 0
    capsys.readouterr()
    rc = cli.main(["checklist-run", "STORY-001"])
    log = _latest_log(project, "STORY-001")
    assert _result(log, "CKL-IP-004-01") == "failed"
    assert log["blocking_failures"] == 1
    assert rc == 1
