"""Tests for specflow.lib.baselines — creation, immutability, diff."""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.lib import artifacts as art_lib
from specflow.lib import baselines as baseline_lib


def _scaffold(root: Path) -> None:
    (root / ".specflow" / "baselines").mkdir(parents=True, exist_ok=True)


class TestCreateBaseline:
    def test_valid_name(self, tmp_path: Path):
        _scaffold(tmp_path)
        result = baseline_lib.create_baseline(tmp_path, "v1.0")
        assert result["ok"]
        assert result["artifact_count"] == 0

    def test_invalid_name(self, tmp_path: Path):
        _scaffold(tmp_path)
        result = baseline_lib.create_baseline(tmp_path, "has spaces")
        assert not result["ok"]
        assert "Invalid" in result["error"]

    def test_immutability(self, tmp_path: Path):
        _scaffold(tmp_path)
        r1 = baseline_lib.create_baseline(tmp_path, "v1.0")
        assert r1["ok"]
        r2 = baseline_lib.create_baseline(tmp_path, "v1.0")
        assert not r2["ok"]
        assert "immutable" in r2["error"]

    def test_special_chars_in_name(self, tmp_path: Path):
        _scaffold(tmp_path)
        result = baseline_lib.create_baseline(tmp_path, "v1.0-rc.1")
        assert result["ok"]

    def test_fingerprint_recomputed_from_body_not_stored(self, tmp_path: Path):
        # An artifact whose stored frontmatter fingerprint is empty/stale must
        # still produce a correct baseline — recompute from the body, don't trust
        # the stored value (the cs2_bet adoption-v0 baseline was all empty hashes).
        _scaffold(tmp_path)
        art_dir = tmp_path / "_specflow" / "specs" / "requirements"
        art_dir.mkdir(parents=True)
        body = "## Rationale\nReal, non-empty content for the requirement.\n"
        (art_dir / "REQ-001.md").write_text(
            "---\n"
            "id: REQ-001\ntype: requirement\nstatus: approved\ntitle: T\n"
            # Deliberately NO fingerprint field — stored value is empty.
            "---\n" + body,
            encoding="utf-8",
        )
        result = baseline_lib.create_baseline(tmp_path, "v1.0")
        assert result["ok"] and result["artifact_count"] == 1
        data = baseline_lib.load_baseline(tmp_path, "v1.0")
        fp = data["artifacts"]["REQ-001"]["fingerprint"]
        parsed = art_lib.discover_artifacts(tmp_path)[0]
        assert fp == art_lib.compute_fingerprint(parsed.body)
        # Not the empty-body hash (sha256 of "").
        assert fp != "sha256:e3b0c44298fc"


class TestLoadBaseline:
    def test_load_existing(self, tmp_path: Path):
        _scaffold(tmp_path)
        baseline_lib.create_baseline(tmp_path, "v1.0")
        data = baseline_lib.load_baseline(tmp_path, "v1.0")
        assert data is not None
        assert data["name"] == "v1.0"

    def test_load_nonexistent(self, tmp_path: Path):
        _scaffold(tmp_path)
        data = baseline_lib.load_baseline(tmp_path, "nonexistent")
        assert data is None


class TestDiffBaselines:
    def test_empty_diff(self, tmp_path: Path):
        _scaffold(tmp_path)
        baseline_lib.create_baseline(tmp_path, "a")
        baseline_lib.create_baseline(tmp_path, "b")
        result = baseline_lib.diff_baselines(tmp_path, "a", "b")
        assert result["ok"]
        assert result["added"] == []
        assert result["removed"] == []

    def test_missing_baseline(self, tmp_path: Path):
        _scaffold(tmp_path)
        baseline_lib.create_baseline(tmp_path, "a")
        result = baseline_lib.diff_baselines(tmp_path, "a", "nonexistent")
        assert not result["ok"]

    def test_status_change_detected(self, tmp_path: Path):
        _scaffold(tmp_path)
        dir_a = tmp_path / ".specflow" / "baselines"
        baseline_a = {
            "name": "a",
            "artifacts": {
                "REQ-001": {"status": "draft", "fingerprint": "sha256:aaa", "title": "T", "type": "requirement"},
            },
        }
        baseline_b = {
            "name": "b",
            "artifacts": {
                "REQ-001": {"status": "approved", "fingerprint": "sha256:aaa", "title": "T", "type": "requirement"},
            },
        }
        (dir_a / "a.yaml").write_text(yaml.dump(baseline_a, default_flow_style=False), encoding="utf-8")
        (dir_a / "b.yaml").write_text(yaml.dump(baseline_b, default_flow_style=False), encoding="utf-8")

        result = baseline_lib.diff_baselines(tmp_path, "a", "b")
        assert result["ok"]
        assert len(result["status_changed"]) == 1
        assert result["status_changed"][0]["id"] == "REQ-001"
        assert result["status_changed"][0]["old"] == "draft"
        assert result["status_changed"][0]["new"] == "approved"
