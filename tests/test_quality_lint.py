"""Tests for specflow.commands.artifact_lint quality check."""

from __future__ import annotations

from pathlib import Path

from specflow.commands.artifact_lint import _check_quality
from specflow.lib import artifacts as art_lib


def _make_req(req_id: str, title: str, body: str) -> art_lib.Artifact:
    return art_lib.Artifact(
        path=Path(f"_specflow/specs/requirements/{req_id}.md"),
        frontmatter={"id": req_id, "title": title, "type": "requirement", "status": "approved"},
        body=body,
    )


def _make_art(art_id: str, art_type: str, body: str) -> art_lib.Artifact:
    return art_lib.Artifact(
        path=Path(f"artifact.md"),
        frontmatter={"id": art_id, "title": "Test", "type": art_type, "status": "approved"},
        body=body,
    )


class TestAmbiguityDetection:
    def test_clean_requirement(self):
        req = _make_req("REQ-100", "Clean", "The system **shall** respond within 200ms.")
        result = _check_quality([req])
        assert result["warning_count"] == 0

    def test_ambiguity_word_detected(self):
        req = _make_req("REQ-100", "Vague", "The system **shall** be fast and user-friendly.")
        result = _check_quality([req])
        assert result["warning_count"] >= 2

    def test_non_req_not_checked(self):
        art = _make_art("STORY-100", "story", "This is simple and easy")
        result = _check_quality([art])
        assert result["warning_count"] == 0


class TestPassiveVoiceDetection:
    def test_passive_voice_detected(self):
        req = _make_req("REQ-100", "Passive", "Data **shall** be validated before storage.")
        result = _check_quality([req])
        assert result["warning_count"] >= 1

    def test_active_voice_clean(self):
        req = _make_req("REQ-100", "Active", "The system **shall** validate data before storage.")
        result = _check_quality([req])
        assert result["warning_count"] == 0


class TestCompoundShallDetection:
    def test_compound_shall_detected(self):
        req = _make_req(
            "REQ-100", "Compound",
            "The system **shall** validate input and **shall** sanitize data.",
        )
        result = _check_quality([req])
        assert result["warning_count"] >= 1

    def test_single_shall_clean(self):
        req = _make_req("REQ-100", "Single", "The system **shall** validate input.")
        result = _check_quality([req])
        assert result["warning_count"] == 0


class TestMissingThresholdDetection:
    def test_missing_threshold_detected(self):
        req = _make_req("REQ-100", "Threshold", "The system **shall** respond quickly.")
        result = _check_quality([req])
        assert result["warning_count"] >= 1

    def test_quantified_threshold_clean(self):
        req = _make_req("REQ-100", "Quantified", "The system **shall** respond within 200ms.")
        result = _check_quality([req])
        assert result["warning_count"] == 0
