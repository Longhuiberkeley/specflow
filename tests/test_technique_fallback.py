"""Tests for thinking technique generic fallback."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specflow.lib.artifacts import Artifact
from specflow.lib.ci import LLMConfig
from specflow.lib.techniques import (
    LENS_CATALOG,
    ALL_LENS_NAMES,
    TechniqueFinding,
    execute_technique,
)


def _make_artifact(art_id: str = "REQ-001", body: str = "The system shall do X") -> Artifact:
    return Artifact(
        path=Path("/fake.md"),
        frontmatter={"id": art_id, "title": f"Test {art_id}", "type": "requirement", "status": "approved"},
        body=body,
    )


def _make_cfg() -> LLMConfig:
    return LLMConfig(provider="openai", model="test", base_url="http://localhost", api_key="test")


def test_lens_catalog_has_16_entries():
    assert len(LENS_CATALOG) == 16


def test_all_lens_names_matches_catalog():
    assert ALL_LENS_NAMES == set(LENS_CATALOG.keys())


def test_dedicated_module_takes_precedence():
    art = _make_artifact()
    cfg = _make_cfg()
    mock_result = {"ok": True, "content": '[{"title": "test", "rationale": "r", "severity": "warn"}]'}

    with patch("specflow.lib.techniques.devils_advocate.call_llm", return_value=mock_result):
        findings = execute_technique("devils_advocate", art, "", cfg)
    assert len(findings) == 1
    assert findings[0].technique == "devils_advocate"


def test_generic_fallback_for_catalog_lens():
    art = _make_artifact()
    cfg = _make_cfg()
    mock_result = {"ok": True, "content": '[{"title": "Scale breaks", "rationale": "At 100x", "severity": "warn"}]'}

    with patch("specflow.lib.techniques.call_llm", return_value=mock_result):
        findings = execute_technique("stress_scale", art, "existing context", cfg)
    assert len(findings) == 1
    assert findings[0].technique == "stress_scale"
    assert findings[0].title == "Scale breaks"


def test_generic_fallback_uses_lens_prompt():
    art = _make_artifact()
    cfg = _make_cfg()
    captured_prompts = {}

    def capture_llm(cfg, system, user):
        captured_prompts["system"] = system
        captured_prompts["user"] = user
        return {"ok": True, "content": "[]"}

    with patch("specflow.lib.techniques.call_llm", side_effect=capture_llm):
        execute_technique("five_whys", art, "", cfg)
    assert "Five-Whys" in captured_prompts["system"]
    assert art.body in captured_prompts["user"]


def test_unknown_technique_returns_error():
    art = _make_artifact()
    cfg = _make_cfg()
    findings = execute_technique("nonexistent_lens", art, "", cfg)
    assert len(findings) == 1
    assert findings[0].severity == "error"
    assert findings[0].technique == "framework"
    assert "Unknown technique" in findings[0].title


def test_generic_fallback_llm_error():
    art = _make_artifact()
    cfg = _make_cfg()

    with patch("specflow.lib.techniques.call_llm", return_value={"ok": False, "error": "API error"}):
        findings = execute_technique("reversal", art, "", cfg)
    assert len(findings) == 1
    assert findings[0].severity == "error"
    assert findings[0].technique == "framework"


def test_generic_fallback_empty_response():
    art = _make_artifact()
    cfg = _make_cfg()

    with patch("specflow.lib.techniques.call_llm", return_value={"ok": True, "content": "[]"}):
        findings = execute_technique("cost_scaling", art, "", cfg)
    assert findings == []


def test_all_catalog_lenses_run_via_fallback():
    art = _make_artifact()
    cfg = _make_cfg()

    for lens_name in LENS_CATALOG:
        if lens_name in ("devils_advocate", "premortem", "assumption_surfacing", "red_blue_team"):
            continue
        with patch("specflow.lib.techniques.call_llm", return_value={"ok": True, "content": "[]"}):
            findings = execute_technique(lens_name, art, "", cfg)
        assert isinstance(findings, list), f"Failed for lens {lens_name}"


def test_run_subagents_caps_concurrency():
    from specflow.lib.techniques import run_subagents

    art = _make_artifact()
    cfg = _make_cfg()
    techniques = ["stress_scale", "reversal", "five_whys", "outside_view",
                   "worst_case_user", "regulator", "temporal_drift", "composition",
                   "inversion", "competitor_framing", "cost_scaling"]

    with patch("specflow.lib.techniques.call_llm", return_value={"ok": True, "content": "[]"}):
        with patch("specflow.lib.techniques.concurrent.futures.ThreadPoolExecutor",
                   wraps=__import__("concurrent.futures", fromlist=["ThreadPoolExecutor"]).ThreadPoolExecutor) as mock_pool:
            run_subagents(techniques, [art], "", cfg)
            call_args = mock_pool.call_args
            assert call_args[1]["max_workers"] <= 8
