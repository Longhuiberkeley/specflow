"""Tests for the knowledge accumulation lifecycle: learning feedback, init domain, plan enrichment."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import yaml
import pytest

from specflow.lib import learning as learn_lib
from specflow.lib import artifacts as art_lib


def _make_artifact(art_id: str, title: str = "", tags: list[str] | None = None) -> art_lib.Artifact:
    return art_lib.Artifact(
        path=Path("/fake") / f"{art_id}.md",
        frontmatter={"id": art_id, "title": title, "type": "requirement", "tags": tags or []},
        body="test body",
    )


class TestCreatePatternFromFinding:
    def test_creates_pattern_for_blocking_severity(self, tmp_path: Path):
        artifact = _make_artifact("REQ-001", "Define error handling", ["api"])
        path = learn_lib.create_pattern_from_finding(
            tmp_path, artifact,
            check_text="Missing error handling for external calls",
            reason="all external calls must define fallback behavior",
            severity="blocking",
        )
        assert path is not None
        assert path.exists()
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["items"][0]["severity"] == "blocking"
        assert "REQ-001" in data["discovered_from"]

    def test_creates_pattern_for_warning_severity(self, tmp_path: Path):
        artifact = _make_artifact("REQ-002", "Data freshness", ["web"])
        path = learn_lib.create_pattern_from_finding(
            tmp_path, artifact,
            check_text="Data freshness not quantified",
            reason="each view should specify staleness tolerance",
            severity="warning",
        )
        assert path is not None
        assert path.exists()
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["items"][0]["severity"] == "warning"

    def test_skips_info_severity(self, tmp_path: Path):
        artifact = _make_artifact("REQ-003", "Docs")
        path = learn_lib.create_pattern_from_finding(
            tmp_path, artifact,
            check_text="Minor formatting issue",
            reason="cosmetic",
            severity="info",
        )
        assert path is None

    def test_inherits_artifact_tags(self, tmp_path: Path):
        artifact = _make_artifact("REQ-004", "Auth", ["auth", "security"])
        path = learn_lib.create_pattern_from_finding(
            tmp_path, artifact,
            check_text="Missing auth on endpoint",
            reason="all endpoints need auth",
            severity="blocking",
        )
        assert path is not None
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert set(data["applies_to"]["tags"]) == {"auth", "security"}

    def test_auto_numbers_prev_files(self, tmp_path: Path):
        artifact = _make_artifact("REQ-001", "Test")
        p1 = learn_lib.create_pattern_from_finding(
            tmp_path, artifact, "Check 1", "Reason 1", "blocking",
        )
        p2 = learn_lib.create_pattern_from_finding(
            tmp_path, artifact, "Check 2", "Reason 2", "warning",
        )
        assert p1 is not None
        assert p2 is not None
        assert p1.name == "PREV-001.yaml"
        assert p2.name == "PREV-002.yaml"


class TestReviewFeedbackLoop:
    def test_create_learned_patterns_creates_patterns(self, tmp_path: Path):
        from specflow.commands import artifact_review
        from specflow.lib.techniques import TechniqueFinding

        targets = [_make_artifact("REQ-001", "Test", ["api"])]
        findings = [
            TechniqueFinding(
                title="Missing error model",
                rationale="Define error responses for all endpoints",
                severity="blocking",
                technique="checklist-run",
                target_id="REQ-001",
            ),
        ]
        count = artifact_review._create_learned_patterns(tmp_path, targets, findings)
        assert count == 1
        learned_dir = tmp_path / ".specflow" / "checklists" / "learned"
        assert learned_dir.exists()
        prev_files = list(learned_dir.glob("PREV-*.yaml"))
        assert len(prev_files) == 1

    def test_skips_info_findings(self, tmp_path: Path):
        from specflow.commands import artifact_review
        from specflow.lib.techniques import TechniqueFinding

        targets = [_make_artifact("REQ-001", "Test")]
        findings = [
            TechniqueFinding(
                title="Minor issue",
                rationale="cosmetic",
                severity="info",
                technique="checklist-run",
                target_id="REQ-001",
            ),
        ]
        count = artifact_review._create_learned_patterns(tmp_path, targets, findings)
        assert count == 0

    def test_skips_non_learnable_techniques(self, tmp_path: Path):
        from specflow.commands import artifact_review
        from specflow.lib.techniques import TechniqueFinding

        cfg_dir = tmp_path / ".specflow"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "config.yaml").write_text(
            yaml.dump({"project": {"name": "test"}, "learning": {"learnable_techniques": ["checklist-run"]}}, default_flow_style=False),
            encoding="utf-8",
        )

        targets = [_make_artifact("REQ-001", "Test")]
        findings = [
            TechniqueFinding(
                title="Devil's advocate issue",
                rationale="Assumed database always available",
                severity="blocking",
                technique="devils_advocate",
                target_id="REQ-001",
            ),
            TechniqueFinding(
                title="Premortem issue",
                rationale="Could fail at scale",
                severity="blocking",
                technique="premortem",
                target_id="REQ-001",
            ),
        ]
        count = artifact_review._create_learned_patterns(tmp_path, targets, findings)
        assert count == 0

    def test_caps_at_max_patterns(self, tmp_path: Path):
        from specflow.commands import artifact_review
        from specflow.lib.techniques import TechniqueFinding

        targets = [_make_artifact("REQ-001", "Test")]
        findings = [
            TechniqueFinding(
                title=f"Issue {i}",
                rationale=f"Reason {i}",
                severity="warning",
                technique="checklist-run",
                target_id="REQ-001",
            )
            for i in range(10)
        ]
        count = artifact_review._create_learned_patterns(tmp_path, targets, findings)
        assert count <= learn_lib._max_patterns_per_session(tmp_path)

    def test_configurable_max_patterns(self, tmp_path: Path):
        import yaml
        from specflow.lib import config as config_lib

        cfg_dir = tmp_path / ".specflow"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg = {"project": {"name": "test"}, "learning": {"max_patterns_per_session": 1}}
        (cfg_dir / "config.yaml").write_text(
            yaml.dump(cfg, default_flow_style=False), encoding="utf-8"
        )

        max_val = learn_lib._max_patterns_per_session(tmp_path)
        assert max_val == 1

    def test_skips_findings_without_matching_target(self, tmp_path: Path):
        from specflow.commands import artifact_review
        from specflow.lib.techniques import TechniqueFinding

        targets = [_make_artifact("REQ-001", "Test")]
        findings = [
            TechniqueFinding(
                title="Orphan finding",
                rationale="No matching artifact",
                severity="blocking",
                technique="checklist-run",
                target_id="REQ-999",
            ),
        ]
        count = artifact_review._create_learned_patterns(tmp_path, targets, findings)
        assert count == 0

    def test_created_pattern_is_loaded_by_checklists(self, tmp_path: Path):
        from specflow.commands import artifact_review
        from specflow.lib.techniques import TechniqueFinding

        targets = [_make_artifact("REQ-001", "Test", ["api"])]
        findings = [
            TechniqueFinding(
                title="Missing error model",
                rationale="Define error responses for all endpoints",
                severity="blocking",
                technique="checklist-run",
                target_id="REQ-001",
            ),
        ]
        artifact_review._create_learned_patterns(tmp_path, targets, findings)

        patterns = learn_lib.list_learned_patterns(tmp_path)
        assert len(patterns) == 1
        assert patterns[0]["items"][0]["check"].startswith("Verify that")


class TestInitDomainFlags:
    def _run_init(self, root: Path, domain: str | None, domain_tags: str = "") -> int:
        from specflow.commands import init as init_cmd

        root.mkdir(parents=True, exist_ok=True)

        with patch("specflow.commands.init.scaffold_lib.create_internal_dirs") as mock_int, \
             patch("specflow.commands.init.scaffold_lib.create_spec_dirs") as mock_spec, \
             patch("specflow.commands.init.scaffold_lib.copy_checklists") as mock_ckl, \
             patch("specflow.commands.init.scaffold_lib.copy_adapters_config") as mock_adp, \
             patch("specflow.commands.init.plat_lib") as mock_plat, \
             patch("specflow.commands.init.rbac_lib"), \
             patch("specflow.commands.init._install_skills"), \
             patch("specflow.commands.init._install_pre_commit_hook"), \
             patch("specflow.commands.init._render_codeowners"), \
             patch("specflow.commands.init._install_ci_workflow"):

            def _ensure_dirs(r, *a, **kw):
                (r / ".specflow").mkdir(parents=True, exist_ok=True)
                (r / "_specflow").mkdir(parents=True, exist_ok=True)

            mock_int.side_effect = _ensure_dirs
            mock_spec.side_effect = _ensure_dirs
            mock_plat.detect_platform.return_value = ("claude-code", {"name": "Claude Code"})
            mock_plat.get_platform.return_value = {"name": "Claude Code", "legacy_dirs": []}

            return init_cmd.run(root, {
                "platform": None,
                "preset": None,
                "with_types": "",
                "no_ci": True,
                "domain": domain,
                "domain_tags": domain_tags,
            })

    def test_init_persists_domain(self, tmp_path: Path):
        from specflow.lib import config as config_lib

        root = tmp_path / "test-project"
        self._run_init(root, "embedded", "real-time,safety-critical")

        domain, tags = config_lib.get_domain(root)
        assert domain == "embedded"
        assert tags == ["real-time", "safety-critical"]

    def test_init_without_domain_leaves_empty(self, tmp_path: Path):
        from specflow.lib import config as config_lib

        root = tmp_path / "test-project"
        self._run_init(root, None)

        domain, tags = config_lib.get_domain(root)
        assert domain == ""
        assert tags == []

    def test_init_generates_project_bps_when_domain_set(self, tmp_path: Path):
        from specflow.lib import best_practices as bp_lib

        root = tmp_path / "test-project"

        yaml_output = yaml.dump({
            "domain": "embedded",
            "level": "project",
            "best_practices": [{"id": "BP-PROJ-01", "title": "Safety first"}],
        }, default_flow_style=False)

        with patch("specflow.lib.ci.load_llm_config") as mock_load, \
             patch("specflow.lib.ci.call_llm") as mock_call:
            mock_load.return_value = MagicMock(api_key="test-key")
            mock_call.return_value = {"ok": True, "content": yaml_output}

            self._run_init(root, "embedded")

        cached = bp_lib.read_cached(root, "embedded", "project", "embedded")
        assert cached is not None
        assert cached["best_practices"][0]["title"] == "Safety first"


class TestLearnableTechniquesConfig:
    def test_default_includes_adversarial(self, tmp_path: Path):
        cfg_dir = tmp_path / ".specflow"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "config.yaml").write_text(
            yaml.dump({"project": {"name": "test"}}, default_flow_style=False),
            encoding="utf-8",
        )
        result = learn_lib._learnable_techniques(tmp_path)
        assert "checklist-run" in result
        assert "devils_advocate" in result
        assert "premortem" in result
        assert "assumption_surfacing" in result
        assert "red_blue_team" in result

    def test_custom_overrides_default(self, tmp_path: Path):
        cfg_dir = tmp_path / ".specflow"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg = {
            "project": {"name": "test"},
            "learning": {"learnable_techniques": ["checklist-run"]},
        }
        (cfg_dir / "config.yaml").write_text(
            yaml.dump(cfg, default_flow_style=False),
            encoding="utf-8",
        )
        result = learn_lib._learnable_techniques(tmp_path)
        assert result == {"checklist-run"}

    def test_empty_config_uses_defaults(self, tmp_path: Path):
        cfg_dir = tmp_path / ".specflow"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "config.yaml").write_text(
            yaml.dump({"project": {"name": "test"}}, default_flow_style=False),
            encoding="utf-8",
        )
        result = learn_lib._learnable_techniques(tmp_path)
        assert "devils_advocate" in result


class TestDoneAutoExtract:
    def test_auto_extracts_from_implemented_stories(self, tmp_path: Path):
        from specflow.commands import done as done_cmd
        from specflow.lib import artifacts as art_lib

        spec_dir = tmp_path / "_specflow" / "specs" / "requirements"
        spec_dir.mkdir(parents=True, exist_ok=True)
        schema_dir = tmp_path / ".specflow" / "schema"
        schema_dir.mkdir(parents=True, exist_ok=True)
        (schema_dir / "story.yaml").write_text(yaml.dump({
            "type": "story", "prefix": "STORY",
            "allowed_status": {"implemented": ["draft"]},
        }), encoding="utf-8")
        story_dir = tmp_path / "_specflow" / "work" / "stories"
        story_dir.mkdir(parents=True, exist_ok=True)

        story_path = story_dir / "STORY-001.md"
        story_path.write_text(
            "---\nid: STORY-001\ntitle: Implement auth\nstatus: implemented\ntype: story\ntags: []\n---\n\nAcceptance:\n- User can log in\n- Token is refreshed\n",
            encoding="utf-8",
        )
        idx_path = story_dir / "_index.yaml"
        idx_path.write_text(yaml.dump({"artifacts": {"STORY-001": str(story_path)}, "next_id": 2}), encoding="utf-8")

        state_dir = tmp_path / ".specflow"
        (state_dir / "state.yaml").write_text(
            yaml.dump({"current": "executing", "history": []}, default_flow_style=False),
            encoding="utf-8",
        )

        rc = done_cmd.run(tmp_path, {"auto": True, "no_patterns": False})
        assert rc == 0
        patterns = learn_lib.list_learned_patterns(tmp_path)
        assert len(patterns) >= 1
        assert patterns[0]["discovered_from"] == "STORY-001"

    def test_no_patterns_flag_skips_extraction(self, tmp_path: Path):
        from specflow.commands import done as done_cmd

        state_dir = tmp_path / ".specflow"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "state.yaml").write_text(
            yaml.dump({"current": "idle", "history": []}, default_flow_style=False),
            encoding="utf-8",
        )

        rc = done_cmd.run(tmp_path, {"auto": True, "no_patterns": True})
        assert rc == 0
        patterns = learn_lib.list_learned_patterns(tmp_path)
        assert len(patterns) == 0
