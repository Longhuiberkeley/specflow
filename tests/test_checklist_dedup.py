"""`specflow checklist-run --dedup` and ``lib.dedup.find_duplicates`` (STORY-718).

Tier 1 (tag Jaccard) and tier 2 (TF-IDF cosine) run here; tier 3 is the
skill's confirmation. The handler always exits 0 and writes the candidates
file the skill reads, with or without candidates.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from conftest import write_artifact

from specflow import cli
from specflow.commands import init as init_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import dedup


def _art(art_id: str, art_type: str, title: str, body: str, tags: list[str]) -> art_lib.Artifact:
    return art_lib.Artifact(
        path=Path(f"{art_id}.md"),
        frontmatter={"id": art_id, "title": title, "type": art_type, "status": "draft", "tags": tags},
        body=body,
    )


_LOGIN = (
    "Login with email and password",
    (
        "Users authenticate with email and password; "
        "failed attempts are rate limited and audited for security review."
    ),
)
_REPORT = (
    "Monthly revenue report",
    (
        "Finance exports the monthly revenue report as CSV "
        "with totals per region and currency conversion applied."
    ),
)


class TestFindDuplicates:
    def test_same_type_same_tags_near_identical_text_is_a_candidate(self):
        arts = [
            _art("STORY-001", "story", _LOGIN[0], _LOGIN[1], ["auth", "security"]),
            _art("STORY-002", "story", _LOGIN[0] + " (v2)", _LOGIN[1], ["auth", "security"]),
            _art("STORY-003", "story", _REPORT[0], _REPORT[1], ["finance"]),
        ]
        candidates = dedup.find_duplicates(arts)
        assert [c.pair for c in candidates] == [("STORY-001", "STORY-002")]
        candidate = candidates[0]
        assert candidate.tag_jaccard == 1.0 and candidate.tfidf_cosine >= 0.7
        assert candidate.confidence == "high" and candidate.tier_reached == 2

    def test_different_types_are_never_compared(self):
        arts = [
            _art("REQ-001", "requirement", _LOGIN[0], _LOGIN[1], ["auth"]),
            _art("STORY-001", "story", _LOGIN[0], _LOGIN[1], ["auth"]),
        ]
        assert dedup.find_duplicates(arts) == []

    def test_tag_prefilter_and_text_threshold_both_gate(self):
        shared_text = [
            _art("STORY-001", "story", _LOGIN[0], _LOGIN[1], ["auth"]),
            _art("STORY-002", "story", _LOGIN[0], _LOGIN[1], ["billing"]),
        ]
        assert dedup.find_duplicates(shared_text) == [], "disjoint tags never reach tier 2"
        shared_tags = [
            _art("STORY-001", "story", _LOGIN[0], _LOGIN[1], ["core"]),
            _art("STORY-002", "story", _REPORT[0], _REPORT[1], ["core"]),
        ]
        assert dedup.find_duplicates(shared_tags) == [], "shared tags with unrelated text is not a duplicate"
        assert dedup.find_duplicates(shared_tags, tfidf_threshold=0.0) != []


@pytest.fixture
def project(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "p"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    monkeypatch.chdir(root)
    return root


def test_dedup_handler_is_quiet_on_distinct_artifacts(project: Path, capsys):
    write_artifact(project, "STORY-001", "story", _LOGIN[0], body=_LOGIN[1], tags=["auth"])
    write_artifact(project, "STORY-002", "story", _REPORT[0], body=_REPORT[1], tags=["finance"])

    assert cli.main(["checklist-run", "--dedup"]) == 0
    out = capsys.readouterr().out
    assert "analyzed 2 artifact(s)" in out
    assert "No duplicate candidates found" in out
    candidates_file = dedup.candidates_file_path(project)
    assert candidates_file.exists(), "the skill reads this file even when empty"
    assert f"Candidates file: {candidates_file.relative_to(project)}" in out


def test_dedup_handler_reports_candidates_and_writes_the_file(project: Path, capsys):
    write_artifact(project, "STORY-001", "story", _LOGIN[0], body=_LOGIN[1], tags=["auth", "security"])
    write_artifact(project, "STORY-002", "story", _LOGIN[0] + " again", body=_LOGIN[1],
                   tags=["auth", "security"])
    write_artifact(project, "STORY-003", "story", _REPORT[0], body=_REPORT[1], tags=["finance"])

    assert cli.main(["checklist-run", "--dedup"]) == 0
    out = capsys.readouterr().out
    assert "1 candidate pair(s)" in out
    assert re.search(r"\[(high|medium)\] STORY-001 <-> STORY-002", out), out
    assert "Review with the check skill" in out

    written = yaml.safe_load(dedup.candidates_file_path(project).read_text(encoding="utf-8"))
    text = yaml.dump(written)
    assert "STORY-001" in text and "STORY-002" in text and "STORY-003" not in text
