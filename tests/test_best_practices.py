"""Tests for specflow.lib.best_practices — domain BP synthesis, caching, and review prefix."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import yaml

from specflow.lib import best_practices as bp_lib
from specflow.lib import standards as standards_lib


def _write_config(root: Path, domain: str = "", tags: list[str] | None = None) -> None:
    cfg_dir = root / ".specflow"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg = {
        "project": {"name": "test", "domain": domain, "domain_tags": tags or []},
        "ci": {"llm": {"api_key_env": "TEST_KEY"}},
    }
    (cfg_dir / "config.yaml").write_text(
        yaml.dump(cfg, default_flow_style=False), encoding="utf-8"
    )


def _write_domain_checklist(root: Path, domain: str, items: list[dict]) -> None:
    path = root / ".specflow" / "checklists" / "domain" / f"{domain}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "id": f"CKL-DOMAIN-{domain.upper()}",
        "name": f"{domain} domain checks",
        "applies_to": {"types": ["requirement", "architecture"]},
        "items": items,
    }
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


def _write_standard(root: Path, name: str, clauses: list[dict]) -> None:
    d = root / ".specflow" / "standards"
    d.mkdir(parents=True, exist_ok=True)
    data = {
        "standard": name,
        "title": f"Test {name}",
        "clauses": clauses,
    }
    (d / f"{name}.yaml").write_text(
        yaml.dump(data, default_flow_style=False), encoding="utf-8"
    )


class TestCachePath:
    def test_project_level(self, tmp_path: Path):
        result = bp_lib.cache_path(tmp_path, "embedded", "project", "embedded")
        assert result.name == "embedded-project.yaml"
        assert "best-practices" in str(result)

    def test_phase_level(self, tmp_path: Path):
        result = bp_lib.cache_path(tmp_path, "embedded", "phase", "plan-arc")
        assert result.name == "embedded-phase-plan-arc.yaml"

    def test_sanitizes_domain(self, tmp_path: Path):
        result = bp_lib.cache_path(tmp_path, "Web App", "phase", "plan-arc")
        assert result.name == "web-app-phase-plan-arc.yaml"

    def test_falls_back_to_generic(self, tmp_path: Path):
        result = bp_lib.cache_path(tmp_path, "", "phase", "")
        assert "generic" in result.name
        assert "review" in result.name


class TestReadCached:
    def test_returns_none_when_missing(self, tmp_path: Path):
        result = bp_lib.read_cached(tmp_path, "embedded", "phase", "plan-arc")
        assert result is None

    def test_returns_data_when_present(self, tmp_path: Path):
        bp_lib.cache_dir(tmp_path).mkdir(parents=True, exist_ok=True)
        data = {"domain": "embedded", "level": "phase", "best_practices": []}
        path = bp_lib.cache_path(tmp_path, "embedded", "phase", "plan-arc")
        path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
        result = bp_lib.read_cached(tmp_path, "embedded", "phase", "plan-arc")
        assert result is not None
        assert result["domain"] == "embedded"
        assert result["level"] == "phase"

    def test_returns_none_on_invalid_yaml(self, tmp_path: Path):
        bp_lib.cache_dir(tmp_path).mkdir(parents=True, exist_ok=True)
        path = bp_lib.cache_path(tmp_path, "embedded", "phase", "plan-arc")
        path.write_text("{{invalid yaml", encoding="utf-8")
        result = bp_lib.read_cached(tmp_path, "embedded", "phase", "plan-arc")
        assert result is None

    def test_returns_none_on_empty_file(self, tmp_path: Path):
        bp_lib.cache_dir(tmp_path).mkdir(parents=True, exist_ok=True)
        path = bp_lib.cache_path(tmp_path, "embedded", "phase", "plan-arc")
        path.write_text("", encoding="utf-8")
        result = bp_lib.read_cached(tmp_path, "embedded", "phase", "plan-arc")
        assert result is None


class TestWriteCached:
    def test_creates_directories_and_writes(self, tmp_path: Path):
        data = {"domain": "test", "level": "project", "best_practices": [{"id": "BP-01"}]}
        written = bp_lib.write_cached(tmp_path, "test", "project", "test", data)
        assert written.exists()
        loaded = yaml.safe_load(written.read_text(encoding="utf-8"))
        assert loaded["domain"] == "test"
        assert len(loaded["best_practices"]) == 1

    def test_overwrites_existing(self, tmp_path: Path):
        bp_lib.write_cached(tmp_path, "test", "project", "test", {"v": 1})
        bp_lib.write_cached(tmp_path, "test", "project", "test", {"v": 2})
        result = bp_lib.read_cached(tmp_path, "test", "project", "test")
        assert result["v"] == 2


class TestStripYamlFences:
    def test_strips_yaml_fences(self):
        assert bp_lib._strip_yaml_fences("```yaml\nfoo: bar\n```") == "foo: bar"

    def test_strips_plain_fences(self):
        assert bp_lib._strip_yaml_fences("```\nfoo: bar\n```") == "foo: bar"

    def test_passes_through_plain_yaml(self):
        assert bp_lib._strip_yaml_fences("foo: bar") == "foo: bar"

    def test_handles_empty(self):
        assert bp_lib._strip_yaml_fences("") == ""


class TestSynthesizeAndCache:
    def test_returns_cached_without_llm(self, tmp_path: Path):
        existing = {"domain": "embedded", "best_practices": [{"id": "BP-01"}]}
        bp_lib.write_cached(tmp_path, "embedded", "phase", "plan-arc", existing)
        result = bp_lib.synthesize_and_cache(tmp_path, "embedded", [], "phase", "plan-arc")
        assert result["ok"]
        assert result["cached"]
        assert result["data"]["domain"] == "embedded"

    def test_returns_error_no_api_key(self, tmp_path: Path):
        _write_config(tmp_path, domain="embedded")
        result = bp_lib.synthesize_and_cache(
            tmp_path, "embedded", [], "phase", "plan-arc", overwrite=True,
        )
        assert result["ok"]
        assert result.get("fallback") is True

    def test_calls_llm_and_caches(self, tmp_path: Path):
        _write_config(tmp_path, domain="embedded")
        yaml_output = yaml.dump({
            "domain": "embedded",
            "level": "phase",
            "phase": "plan-arc",
            "best_practices": [{"id": "BP-01", "title": "Test"}],
        }, default_flow_style=False)
        with patch("specflow.lib.ci.load_llm_config") as mock_load, \
             patch("specflow.lib.ci.call_llm") as mock_call:
            mock_load.return_value = MagicMock(api_key="test-key")
            mock_call.return_value = {"ok": True, "content": yaml_output}
            result = bp_lib.synthesize_and_cache(
                tmp_path, "embedded", [], "phase", "plan-arc", overwrite=True,
            )
        assert result["ok"]
        assert not result["cached"]
        assert result["data"]["best_practices"][0]["id"] == "BP-01"
        assert bp_lib.read_cached(tmp_path, "embedded", "phase", "plan-arc") is not None

    def test_handles_llm_failure(self, tmp_path: Path):
        _write_config(tmp_path, domain="embedded")
        with patch("specflow.lib.ci.load_llm_config") as mock_load, \
             patch("specflow.lib.ci.call_llm") as mock_call:
            mock_load.return_value = MagicMock(api_key="test-key")
            mock_call.return_value = {"ok": False, "error": "timeout"}
            result = bp_lib.synthesize_and_cache(
                tmp_path, "embedded", [], "phase", "plan-arc", overwrite=True,
            )
        assert not result["ok"]
        assert "timeout" in result["error"]

    def test_handles_invalid_yaml_output(self, tmp_path: Path):
        _write_config(tmp_path, domain="embedded")
        with patch("specflow.lib.ci.load_llm_config") as mock_load, \
             patch("specflow.lib.ci.call_llm") as mock_call:
            mock_load.return_value = MagicMock(api_key="test-key")
            mock_call.return_value = {"ok": True, "content": "not valid yaml: ["}
            result = bp_lib.synthesize_and_cache(
                tmp_path, "embedded", [], "phase", "plan-arc", overwrite=True,
            )
        assert not result["ok"]
        assert "YAML" in result["error"]


class TestEnsureProjectBps:
    def test_auto_synthesizes(self, tmp_path: Path):
        _write_config(tmp_path, domain="api-service")
        yaml_output = yaml.dump({
            "domain": "api-service",
            "level": "project",
            "best_practices": [{"id": "BP-PROJ-01", "title": "Define API contracts"}],
        }, default_flow_style=False)
        with patch("specflow.lib.ci.load_llm_config") as mock_load, \
             patch("specflow.lib.ci.call_llm") as mock_call:
            mock_load.return_value = MagicMock(api_key="test-key")
            mock_call.return_value = {"ok": True, "content": yaml_output}
            result = bp_lib.ensure_project_bps(tmp_path, "api-service", ["rest"])
        assert result["ok"]
        assert bp_lib.read_cached(tmp_path, "api-service", "project", "api-service") is not None

    def test_returns_cached(self, tmp_path: Path):
        existing = {"domain": "api-service", "best_practices": []}
        bp_lib.write_cached(tmp_path, "api-service", "project", "api-service", existing)
        result = bp_lib.ensure_project_bps(tmp_path, "api-service", [])
        assert result["ok"]
        assert result["cached"]


class TestEnsurePhaseBps:
    def test_auto_synthesizes(self, tmp_path: Path):
        _write_config(tmp_path, domain="embedded")
        yaml_output = yaml.dump({
            "domain": "embedded",
            "level": "phase",
            "phase": "plan-arc",
            "best_practices": [{"id": "BP-PA-01", "title": "Task decomposition"}],
        }, default_flow_style=False)
        with patch("specflow.lib.ci.load_llm_config") as mock_load, \
             patch("specflow.lib.ci.call_llm") as mock_call:
            mock_load.return_value = MagicMock(api_key="test-key")
            mock_call.return_value = {"ok": True, "content": yaml_output}
            result = bp_lib.ensure_phase_bps(tmp_path, "embedded", [], "plan-arc")
        assert result["ok"]
        assert not result["cached"]


class TestComposeReviewPrefix:
    def test_returns_empty_when_no_domain(self, tmp_path: Path):
        result = bp_lib.compose_review_prefix(tmp_path, "", [], "plan-arc", [])
        assert result == ""

    def test_includes_project_bps(self, tmp_path: Path):
        _write_config(tmp_path, domain="embedded")
        bp_lib.write_cached(tmp_path, "embedded", "project", "embedded", {
            "domain": "embedded",
            "level": "project",
            "purpose": "Build safe firmware.",
            "best_practices": [{"id": "BP-PROJ-01", "title": "Safety first", "evaluation": "Does the project identify hazards?"}],
            "common_pitfalls": ["Ignoring watchdog"],
        })
        result = bp_lib.compose_review_prefix(tmp_path, "embedded", [], "plan-arc", [])
        assert "Project-level guidance" in result
        assert "Safety first" in result
        assert "Ignoring watchdog" in result

    def test_includes_clause_context(self, tmp_path: Path):
        _write_config(tmp_path, domain="embedded")
        _write_standard(tmp_path, "iso26262", [
            {"id": "SEC-1", "title": "Access Control", "description": "Enforce RBAC."},
        ])
        result = bp_lib.compose_review_prefix(tmp_path, "embedded", [], "plan-arc", ["SEC-1"])
        assert "Authoritative clause context" in result
        assert "SEC-1" in result
        assert "Access Control" in result

    def test_includes_phase_bps(self, tmp_path: Path):
        _write_config(tmp_path, domain="embedded")
        bp_lib.write_cached(tmp_path, "embedded", "phase", "plan-arc", {
            "domain": "embedded",
            "level": "phase",
            "phase": "plan-arc",
            "process_area": "SWE.2",
            "best_practices": [
                {"id": "BP-PA-01", "title": "Task decomposition", "description": "Break into tasks.", "evaluation": "Does the architecture define tasks?", "pitfalls": ["No priorities"]},
            ],
            "common_pitfalls": ["Flat priority scheme"],
        })
        result = bp_lib.compose_review_prefix(tmp_path, "embedded", [], "plan-arc", [])
        assert "Phase-level best practices" in result
        assert "Task decomposition" in result
        assert "Flat priority scheme" in result

    def test_auto_synthesizes_phase_bps(self, tmp_path: Path):
        _write_config(tmp_path, domain="embedded")
        yaml_output = yaml.dump({
            "domain": "embedded",
            "level": "phase",
            "phase": "plan-arc",
            "best_practices": [{"id": "BP-01", "title": "Auto-generated"}],
        }, default_flow_style=False)
        with patch("specflow.lib.ci.load_llm_config") as mock_load, \
             patch("specflow.lib.ci.call_llm") as mock_call:
            mock_load.return_value = MagicMock(api_key="test-key")
            mock_call.return_value = {"ok": True, "content": yaml_output}
            result = bp_lib.compose_review_prefix(tmp_path, "embedded", [], "plan-arc", [])
        assert "Auto-generated" in result

    def test_combined_all_three_sections(self, tmp_path: Path):
        _write_config(tmp_path, domain="embedded")
        _write_standard(tmp_path, "iso", [
            {"id": "C1", "title": "Safety", "description": "Be safe."},
        ])
        bp_lib.write_cached(tmp_path, "embedded", "project", "embedded", {
            "domain": "embedded",
            "level": "project",
            "purpose": "Safe firmware",
            "best_practices": [{"id": "BP-PROJ-01", "title": "Identify hazards"}],
            "common_pitfalls": [],
        })
        bp_lib.write_cached(tmp_path, "embedded", "phase", "plan-arc", {
            "domain": "embedded",
            "level": "phase",
            "phase": "plan-arc",
            "process_area": "SWE.2",
            "best_practices": [{"id": "BP-PA-01", "title": "Decompose tasks"}],
            "common_pitfalls": [],
        })
        result = bp_lib.compose_review_prefix(tmp_path, "embedded", [], "plan-arc", ["C1"])
        assert "Authoritative clause context" in result
        assert "Project-level guidance" in result
        assert "Phase-level best practices" in result

    def test_graceful_fallback_no_api_key(self, tmp_path: Path):
        _write_config(tmp_path, domain="embedded")
        result = bp_lib.compose_review_prefix(tmp_path, "embedded", [], "plan-arc", [])
        assert "Phase-level best practices" in result

    def test_includes_staleness_note(self, tmp_path: Path):
        _write_config(tmp_path, domain="embedded")
        from specflow.commands import create as create_cmd
        schema_dir = tmp_path / ".specflow" / "schema"
        schema_dir.mkdir(parents=True, exist_ok=True)
        (schema_dir / "decision.yaml").write_text(yaml.dump({
            "type": "decision", "prefix": "DEC",
            "allowed_status": {"draft": [], "approved": ["draft"]},
        }), encoding="utf-8")
        dec_dir = tmp_path / "_specflow" / "work" / "decisions"
        dec_dir.mkdir(parents=True, exist_ok=True)
        (dec_dir / "_index.yaml").write_text(yaml.dump({"artifacts": {}, "next_id": 1}), encoding="utf-8")
        create_cmd.run(tmp_path, {
            "type": "decision",
            "title": "Use event sourcing",
            "status": "approved",
            "body": "We chose event sourcing for audit trail.",
        })
        # Write a stale BP cache (mtime will be older than the DEC artifact)
        bp_data = {
            "domain": "embedded",
            "level": "phase",
            "phase": "plan-arc",
            "best_practices": [{"id": "BP-PA-01", "title": "Old practice"}],
            "common_pitfalls": [],
        }
        bp_lib.write_cached(tmp_path, "embedded", "phase", "plan-arc", bp_data)
        # Touch the DEC artifact to make it newer than the BP cache
        dec_path = tmp_path / "_specflow" / "work" / "decisions" / "DEC-001.md"
        if dec_path.exists():
            import time
            time.sleep(0.1)
            dec_path.touch()
        result = bp_lib.compose_review_prefix(tmp_path, "embedded", [], "plan-arc", [])
        assert "stale" in result or "recent architectural decisions" in result

    def test_truncates_phase_bps(self, tmp_path: Path):
        _write_config(tmp_path, domain="embedded")
        bp_data = {
            "domain": "embedded",
            "level": "phase",
            "phase": "plan-arc",
            "best_practices": [
                {"id": f"BP-{i}", "title": f"Practice {i}", "description": "desc", "evaluation": "eval", "pitfalls": []}
                for i in range(12)
            ],
            "common_pitfalls": [f"Pitfall {i}" for i in range(10)],
        }
        bp_lib.write_cached(tmp_path, "embedded", "phase", "plan-arc", bp_data)
        result = bp_lib.compose_review_prefix(tmp_path, "embedded", [], "plan-arc", [])
        # Should cap at 8 practices and 5 pitfalls
        practice_count = result.count("### BP-")
        assert practice_count == 8
        assert result.count("Pitfall") <= 5


class TestBuildSynthesisPrompt:
    def test_project_prompt_includes_domain(self):
        system, user = bp_lib.build_project_synthesis_prompt("automotive", ["safety"])
        assert "automotive" in user
        assert "safety" in user
        assert "YAML" in user

    def test_phase_prompt_includes_process_area(self):
        system, user = bp_lib.build_phase_synthesis_prompt(
            "embedded", [], "plan-arc",
        )
        assert "plan-arc" in user
        assert "SWE.2" in user

    def test_phase_prompt_includes_installed_clauses(self):
        clauses = [{"id": "C1", "title": "Safety", "_standard": "ISO 26262"}]
        system, user = bp_lib.build_phase_synthesis_prompt(
            "embedded", [], "plan-arc", installed_clauses=clauses,
        )
        assert "C1" in user
        assert "Do NOT duplicate" in user

    def test_project_prompt_includes_anti_pattern_field(self):
        system, user = bp_lib.build_project_synthesis_prompt("embedded", [])
        assert "anti_pattern" in user
        assert "concrete example of violating this practice" in user

    def test_phase_prompt_includes_anti_pattern_field(self):
        _, user = bp_lib.build_phase_synthesis_prompt(
            "embedded", [], "plan-arc",
        )
        assert "anti_pattern" in user
        assert "concrete example of violating this practice at this phase" in user

    def test_project_prompt_has_exclusion_instruction(self):
        system, user = bp_lib.build_project_synthesis_prompt("api-service", [])
        assert "CRITICAL: Omit any practice that applies equally to ALL software" in user
        assert "Only include practices where violation would cause a domain-specific" in user

    def test_phase_prompt_has_exclusion_instruction(self):
        _, user = bp_lib.build_phase_synthesis_prompt(
            "embedded", [], "execute-impl",
        )
        assert "CRITICAL: Omit any practice that applies equally to ALL software" in user
        assert "Only include practices where violation causes a domain-specific" in user

    def test_project_prompt_has_few_shot_examples(self):
        system, user = bp_lib.build_project_synthesis_prompt("fintech", [])
        assert "Example practice (embedded/safety-critical)" in user
        assert "Example practice (api-service/high-traffic)" in user
        assert "BP-PROJ-01" in user

    def test_phase_prompt_has_few_shot_example(self):
        _, user = bp_lib.build_phase_synthesis_prompt(
            "embedded", [], "plan-arc",
        )
        assert "Example practice (embedded, plan-arc, SWE.2)" in user
        assert "BP-PHASE-ARC-01" in user

    def test_phase_prompt_includes_existing_domain_checks(self):
        system, user = bp_lib.build_phase_synthesis_prompt(
            "embedded", [], "plan-arc",
            existing_domain_checks="- Check real-time constraints\n- Verify memory bounds",
        )
        assert "Do NOT duplicate these checks" in user


class TestInstalledClausesForPhase:
    def test_returns_empty_when_no_standards(self, tmp_path: Path):
        result = bp_lib._installed_clauses_for_phase(tmp_path, "plan-arc")
        assert result == []

    def test_returns_matching_clauses(self, tmp_path: Path):
        _write_standard(tmp_path, "iso", [
            {"id": "C1", "title": "Arch", "process_area": "SWE.2 — software architectural design"},
            {"id": "C2", "title": "Unrelated", "process_area": "SWE.5 — verification"},
        ])
        result = bp_lib._installed_clauses_for_phase(tmp_path, "plan-arc")
        ids = [c["id"] for c in result]
        assert "C1" in ids
        assert "C2" not in ids


class TestExistingDomainChecksText:
    def test_returns_empty_when_no_domain(self, tmp_path: Path):
        result = bp_lib._existing_domain_checks_text(tmp_path, "embedded")
        assert result == ""

    def test_returns_empty_when_no_checklist(self, tmp_path: Path):
        result = bp_lib._existing_domain_checks_text(tmp_path, "nonexistent")
        assert result == ""

    def test_returns_check_texts(self, tmp_path: Path):
        _write_domain_checklist(tmp_path, "embedded", [
            {"id": "CKL-01", "check": "Verify real-time constraints"},
            {"id": "CKL-02", "check": "Check memory bounds"},
        ])
        result = bp_lib._existing_domain_checks_text(tmp_path, "embedded")
        assert "Verify real-time constraints" in result
        assert "Check memory bounds" in result

    def test_filters_by_artifact_type(self, tmp_path: Path):
        _write_domain_checklist(tmp_path, "embedded", [
            {"id": "CKL-01", "check": "Test"},
        ])
        result = bp_lib._existing_domain_checks_text(tmp_path, "embedded", artifact_type="unit-test")
        assert result == ""


class TestPerItemAppliesTo:
    def test_per_item_type_filter(self, tmp_path: Path):
        from specflow.lib import checklists as ckl_lib
        from specflow.lib import config as config_lib

        # Set domain in config
        cfg_dir = tmp_path / ".specflow"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        config_lib.write_config(tmp_path, {"project": {"name": "t", "domain": "web-app"}})

        # Create domain checklist with per-item applies_to
        domain_dir = tmp_path / ".specflow" / "checklists" / "domain"
        domain_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "id": "CKL-DOMAIN-WEB",
            "name": "Web domain checks",
            "applies_to": {"types": ["requirement", "architecture", "detailed-design", "story"]},
            "items": [
                {
                    "id": "CKL-WEB-01",
                    "check": "Rendering strategy",
                    "severity": "blocking",
                    "applies_to": {"types": ["architecture", "detailed-design"]},
                },
                {
                    "id": "CKL-WEB-02",
                    "check": "Accessibility requirements",
                    "severity": "warning",
                },
            ],
        }
        (domain_dir / "web-app.yaml").write_text(
            yaml.dump(data, default_flow_style=False), encoding="utf-8"
        )

        # Test filtering: requirement should get WEB-02 but not WEB-01
        req_art = ckl_lib.Artifact(
            path=tmp_path / "REQ-001.md",
            frontmatter={"id": "REQ-001", "type": "requirement", "tags": []},
            body="test",
        )
        items = ckl_lib._load_domain_checklist(tmp_path, "web-app", "requirement")
        assert len(items) == 1
        assert items[0].id == "CKL-WEB-02"

        # Architecture should get both
        arch_art = ckl_lib.Artifact(
            path=tmp_path / "ARCH-001.md",
            frontmatter={"id": "ARCH-001", "type": "architecture", "tags": []},
            body="test",
        )
        items = ckl_lib._load_domain_checklist(tmp_path, "web-app", "architecture")
        assert len(items) == 2


class TestHandbookBackwardCompat:
    def test_handbook_delegates_to_best_practices(self, tmp_path: Path):
        from specflow.lib import handbook
        data = {"domain": "embedded", "level": "phase", "best_practices": [{"id": "BP-01"}]}
        bp_lib.write_cached(tmp_path, "embedded", "phase", "plan-arc", data)
        result = handbook.read_cached(tmp_path, "embedded", "plan-arc")
        assert result is not None
        assert "BP-01" in result

    def test_handbook_cache_path_uses_best_practices_dir(self, tmp_path: Path):
        from specflow.lib import handbook
        path = handbook.cache_path(tmp_path, "embedded", "plan-arc")
        assert "best-practices" in str(path)


class TestRecentDecisionSummaries:
    def test_returns_empty_when_no_decisions(self, tmp_path: Path):
        result = bp_lib._recent_decision_summaries(tmp_path)
        assert result == ""

    def test_returns_decision_summaries(self, tmp_path):
        from specflow.commands import create as create_cmd
        schema_dir = tmp_path / ".specflow" / "schema"
        schema_dir.mkdir(parents=True, exist_ok=True)
        (schema_dir / "decision.yaml").write_text(yaml.dump({
            "type": "decision", "prefix": "DEC",
            "allowed_status": {"draft": [], "approved": ["draft"]},
        }), encoding="utf-8")
        dec_dir = tmp_path / "_specflow" / "work" / "decisions"
        dec_dir.mkdir(parents=True, exist_ok=True)
        (dec_dir / "_index.yaml").write_text(yaml.dump({"artifacts": {}, "next_id": 1}), encoding="utf-8")
        create_cmd.run(tmp_path, {
            "type": "decision",
            "title": "Use event sourcing",
            "status": "approved",
            "body": "We chose event sourcing for audit trail.",
        })
        result = bp_lib._recent_decision_summaries(tmp_path)
        assert "DEC-001" in result
        assert "Use event sourcing" in result
        assert "approved" in result

    def test_limits_to_max_items(self, tmp_path):
        from specflow.commands import create as create_cmd
        schema_dir = tmp_path / ".specflow" / "schema"
        schema_dir.mkdir(parents=True, exist_ok=True)
        (schema_dir / "decision.yaml").write_text(yaml.dump({
            "type": "decision", "prefix": "DEC",
            "allowed_status": {"draft": [], "approved": ["draft"]},
        }), encoding="utf-8")
        dec_dir = tmp_path / "_specflow" / "work" / "decisions"
        dec_dir.mkdir(parents=True, exist_ok=True)
        (dec_dir / "_index.yaml").write_text(yaml.dump({"artifacts": {}, "next_id": 1}), encoding="utf-8")
        for i in range(7):
            create_cmd.run(tmp_path, {
                "type": "decision",
                "title": f"Decision {i+1}",
                "status": "draft",
                "body": f"Decision {i+1} body",
                "skip_dedup_check": True,
            })
        result = bp_lib._recent_decision_summaries(tmp_path, max_items=3)
        lines = [l for l in result.strip().split("\n") if l.strip()]
        assert len(lines) <= 3


class TestBuildPhaseSynthesisPromptDecisionContext:
    def test_prompt_includes_decisions(self):
        _, user = bp_lib.build_phase_synthesis_prompt(
            "embedded", [], "execute-impl",
            decision_summaries="  - [approved] DEC-001: Use event sourcing\n  - [draft] DEC-002: Choose database",
        )
        assert "DEC-001" in user
        assert "architectural decisions" in user
        assert "event sourcing" in user

    def test_prompt_omits_decisions_block_when_empty(self):
        _, user = bp_lib.build_phase_synthesis_prompt(
            "embedded", [], "execute-impl",
            decision_summaries="",
        )
        assert "architectural decisions" not in user


class TestAutoBackupOnOverwrite:
    def test_backup_created_on_overwrite(self, tmp_path: Path):
        original = {"domain": "test", "level": "project", "best_practices": [{"id": "BP-01"}]}
        bp_lib.write_cached(tmp_path, "test", "project", "test", original)
        old_path = bp_lib.cache_path(tmp_path, "test", "project", "test")
        assert old_path.exists()
        backup = bp_lib._backup_existing(old_path)
        assert backup is not None
        assert backup.exists()
        assert "backups" in str(backup)
        backup_data = yaml.safe_load(backup.read_text(encoding="utf-8"))
        assert backup_data == original

    def test_backup_returns_none_when_no_existing(self, tmp_path: Path):
        path = bp_lib.cache_path(tmp_path, "test", "project", "test")
        assert not path.exists()
        result = bp_lib._backup_existing(path)
        assert result is None

    def test_synthesize_and_cache_returns_backup_path_on_overwrite(self, tmp_path: Path):
        _write_config(tmp_path, "embedded")
        original = {"domain": "embedded", "level": "project", "best_practices": []}
        bp_lib.write_cached(tmp_path, "embedded", "project", "embedded", original)
        with patch("specflow.lib.ci.load_llm_config") as mock_load, \
             patch("specflow.lib.ci.call_llm") as mock_call:
            mock_load.return_value = MagicMock(api_key="test-key")
            mock_call.return_value = {
                "ok": True,
                "content": yaml.dump({"domain": "embedded", "level": "project", "best_practices": [{"id": "BP-PROJ-01", "title": "New"}]}),
            }
            result = bp_lib.synthesize_and_cache(
                tmp_path, "embedded", [], "project", "embedded", overwrite=True,
            )
        assert result["ok"]
        assert "backup" in result
        assert "backups" in result["backup"]


class TestComposeReviewPrefixSkipSynthesis:
    def test_skip_synthesis_uses_cached_only(self, tmp_path: Path):
        _write_config(tmp_path, "embedded")
        cached_data = {
            "domain": "embedded",
            "level": "phase",
            "process_area": "SWE.2",
            "best_practices": [{"id": "BP-01", "title": "Cached BP", "description": "desc"}],
        }
        bp_lib.write_cached(tmp_path, "embedded", "phase", "plan-arc", cached_data)
        with patch("specflow.lib.best_practices.ensure_phase_bps") as mock_ensure:
            prefix = bp_lib.compose_review_prefix(
                tmp_path, "embedded", [], "plan-arc", [],
                skip_synthesis=True,
            )
            mock_ensure.assert_not_called()
        assert "Cached BP" in prefix

    def test_skip_synthesis_returns_empty_when_no_cache(self, tmp_path: Path):
        _write_config(tmp_path, "embedded")
        prefix = bp_lib.compose_review_prefix(
            tmp_path, "embedded", [], "plan-arc", [],
            skip_synthesis=True,
        )
        assert prefix == ""


class TestPhasePromptDualFewShot:
    def test_phase_prompt_includes_both_domain_examples(self):
        _, user = bp_lib.build_phase_synthesis_prompt("embedded", [], "plan-arc")
        assert "Example practice (embedded, plan-arc, SWE.2)" in user
        assert "Example practice (api-service, plan-arc)" in user

    def test_phase_prompt_api_example_has_anti_pattern(self):
        _, user = bp_lib.build_phase_synthesis_prompt("fintech", [], "plan-arc")
        assert "cascading failure" in user
