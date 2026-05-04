"""Tests for generic best-practice fallback when no API key is available."""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.lib import best_practices as bp_lib


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / ".specflow" / "cache" / "best-practices").mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "schema").mkdir(parents=True, exist_ok=True)
    return root


class TestCopyGenericFallback:
    def test_copies_template_for_plan_arc(self, project_root: Path):
        result = bp_lib.copy_generic_fallback(
            project_root, "generic", "phase", "plan-arc"
        )
        assert result is not None
        assert result.exists()
        data = yaml.safe_load(result.read_text(encoding="utf-8"))
        assert data["phase"] == "plan-arc"
        assert len(data["best_practices"]) >= 4

    def test_copies_template_for_plan_ddd(self, project_root: Path):
        result = bp_lib.copy_generic_fallback(
            project_root, "generic", "phase", "plan-ddd"
        )
        assert result is not None
        assert result.exists()
        data = yaml.safe_load(result.read_text(encoding="utf-8"))
        assert data["phase"] == "plan-ddd"

    def test_copies_template_for_plan_story(self, project_root: Path):
        result = bp_lib.copy_generic_fallback(
            project_root, "generic", "phase", "plan-story"
        )
        assert result is not None
        assert result.exists()
        data = yaml.safe_load(result.read_text(encoding="utf-8"))
        assert data["phase"] == "plan-story"

    def test_returns_none_for_unknown_phase(self, project_root: Path):
        result = bp_lib.copy_generic_fallback(
            project_root, "generic", "phase", "nonexistent-phase"
        )
        assert result is None

    def test_returns_none_for_project_level(self, project_root: Path):
        result = bp_lib.copy_generic_fallback(
            project_root, "generic", "project", "generic"
        )
        assert result is None

    def test_preserves_existing_file(self, project_root: Path):
        cache_path = bp_lib.cache_path(project_root, "generic", "phase", "plan-arc")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        existing_data = {"custom": "data"}
        cache_path.write_text(yaml.dump(existing_data), encoding="utf-8")

        result = bp_lib.copy_generic_fallback(
            project_root, "generic", "phase", "plan-arc"
        )
        assert result is not None
        data = yaml.safe_load(result.read_text(encoding="utf-8"))
        assert data == existing_data


class TestSynthesizeAndCacheFallback:
    def test_fallback_when_no_api_key(self, project_root: Path):
        result = bp_lib.synthesize_and_cache(
            project_root, "generic", [], "phase", "plan-arc"
        )
        assert result["ok"] is True
        assert result.get("fallback") is True
        assert result["data"] is not None

    def test_no_fallback_for_project_level(self, project_root: Path):
        result = bp_lib.synthesize_and_cache(
            project_root, "generic", [], "project", "generic"
        )
        assert result["ok"] is False
        assert "missing" in result.get("error", "").lower() or result.get("error") is not None
