"""Tests for specflow status command coverage metrics."""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.commands.status import _compute_coverage
from specflow.lib import artifacts as art_lib


def _make_art(art_id: str, art_type: str, status: str = "implemented",
              links: list[art_lib.Link] | None = None) -> art_lib.Artifact:
    return art_lib.Artifact(
        path=Path(f"artifact.md"),
        frontmatter={"id": art_id, "title": f"Test {art_id}", "type": art_type, "status": status},
        body="body",
        links=links or [],
    )


class TestReqCoverage:
    def test_no_reqs(self):
        result = _compute_coverage([_make_art("STORY-001", "story")])
        assert result["req_pct"] is None
        assert result["req_total"] == 0

    def test_req_with_story(self):
        arts = [
            _make_art("REQ-001", "requirement"),
            _make_art("STORY-001", "story", links=[art_lib.Link(target="REQ-001", role="implements")]),
        ]
        result = _compute_coverage(arts)
        assert result["req_total"] == 1
        assert result["req_covered"] == 1
        assert result["req_pct"] == 100.0

    def test_req_without_story(self):
        arts = [
            _make_art("REQ-001", "requirement"),
            _make_art("REQ-002", "requirement"),
            _make_art("STORY-001", "story", links=[art_lib.Link(target="REQ-001", role="implements")]),
        ]
        result = _compute_coverage(arts)
        assert result["req_total"] == 2
        assert result["req_covered"] == 1
        assert result["req_pct"] == 50.0


class TestStoryTestCoverage:
    def test_no_stories(self):
        result = _compute_coverage([_make_art("REQ-001", "requirement")])
        assert result["story_pct"] is None
        assert result["story_total"] == 0

    def test_story_with_verified_spec(self):
        arts = [
            _make_art("REQ-001", "requirement"),
            _make_art("STORY-001", "story", links=[art_lib.Link(target="REQ-001", role="implements")]),
            _make_art("QT-001", "qualification-test", links=[art_lib.Link(target="REQ-001", role="verified_by")]),
        ]
        result = _compute_coverage(arts)
        assert result["story_total"] == 1
        assert result["story_tested"] == 1
        assert result["story_pct"] == 100.0

    def test_story_without_verified_spec(self):
        arts = [
            _make_art("REQ-001", "requirement"),
            _make_art("STORY-001", "story", links=[art_lib.Link(target="REQ-001", role="implements")]),
        ]
        result = _compute_coverage(arts)
        assert result["story_total"] == 1
        assert result["story_tested"] == 0
        assert result["story_pct"] == 0.0


class TestChainCompleteness:
    def test_no_specs(self):
        result = _compute_coverage([_make_art("STORY-001", "story")])
        assert result["chain_pct"] is None
        assert result["chain_total"] == 0

    def test_spec_with_verification(self):
        arts = [
            _make_art("DDD-001", "detailed-design"),
            _make_art("UT-001", "unit-test", links=[art_lib.Link(target="DDD-001", role="verified_by")]),
        ]
        result = _compute_coverage(arts)
        assert result["chain_total"] == 1
        assert result["chain_verified"] == 1
        assert result["chain_pct"] == 100.0

    def test_spec_without_verification(self):
        arts = [
            _make_art("DDD-001", "detailed-design"),
            _make_art("REQ-001", "requirement"),
        ]
        result = _compute_coverage(arts)
        assert result["chain_total"] == 2
        assert result["chain_verified"] == 0
        assert result["chain_pct"] == 0.0

    def test_mixed_verification(self):
        arts = [
            _make_art("DDD-001", "detailed-design"),
            _make_art("UT-001", "unit-test", links=[art_lib.Link(target="DDD-001", role="verified_by")]),
            _make_art("REQ-001", "requirement"),
        ]
        result = _compute_coverage(arts)
        assert result["chain_total"] == 2
        assert result["chain_verified"] == 1
        assert result["chain_pct"] == 50.0
