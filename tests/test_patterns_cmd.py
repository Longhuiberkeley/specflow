"""`specflow patterns list|show` behaviour (STORY-718)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from specflow import cli
from specflow.commands import patterns as patterns_cmd


def _write_pattern(root: Path, pattern_id: str, **overrides) -> dict:
    data = {
        "id": pattern_id,
        "name": f"Pattern {pattern_id}",
        "discovered_from": "check-REQ-001",
        "items": [{"check": "Every AC names an observable outcome", "severity": "warning"}],
    }
    data.update(overrides)
    learned = root / ".specflow" / "checklists" / "learned"
    learned.mkdir(parents=True, exist_ok=True)
    (learned / f"{pattern_id}.yaml").write_text(yaml.dump(data, sort_keys=False), encoding="utf-8")
    return data


@pytest.fixture
def project(tmp_path: Path, monkeypatch) -> Path:
    (tmp_path / ".specflow").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_list_without_patterns_is_a_neutral_note(project: Path, capsys):
    assert cli.main(["patterns", "list"]) == 0
    assert "(no learned patterns" in capsys.readouterr().out


def test_list_prints_id_severity_name_source_and_check(project: Path, capsys):
    _write_pattern(project, "PREV-001")
    _write_pattern(project, "PREV-002", items=[{"check": "x" * 120, "severity": "blocking"}],
                   discovered_from="")
    (project / ".specflow" / "checklists" / "learned" / "PREV-003.yaml").write_text(
        "- not: a mapping\n", encoding="utf-8"
    )

    assert cli.main(["patterns", "list"]) == 0
    out = capsys.readouterr().out
    assert "Learned prevention patterns: 2" in out, "non-mapping files are skipped, not fatal"
    assert "PREV-001  [warning]  Pattern PREV-001" in out
    assert "from: check-REQ-001" in out
    assert "check: Every AC names an observable outcome" in out
    assert "PREV-002  [blocking]" in out
    assert "x" * 80 in out and "x" * 81 not in out, "check preview is capped at 80 chars"


def test_show_dumps_the_pattern_yaml(project: Path, capsys):
    data = _write_pattern(project, "PREV-007")
    assert cli.main(["patterns", "show", "PREV-007"]) == 0
    assert yaml.safe_load(capsys.readouterr().out) == data


def test_show_unknown_pattern_and_missing_subcommand_exit_one(project: Path, capsys):
    assert cli.main(["patterns", "show", "PREV-404"]) == 1
    assert "PREV-404 not found" in capsys.readouterr().err
    assert patterns_cmd.run(project, {}) == 1
    assert "subcommand required" in capsys.readouterr().err
    assert patterns_cmd.run(project, {"patterns_subcommand": "show"}) == 1
    assert "pattern ID required" in capsys.readouterr().err
