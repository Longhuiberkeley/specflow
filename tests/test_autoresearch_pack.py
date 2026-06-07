"""STORY-075: Autoresearch pack lifecycle and integration tests.

Five test classes covering:
1. Schema lifecycle — valid/invalid statuses + transition structure for COMP/LOOP/EXPT/FIND
2. Pack install — apply_pack() copies schemas, creates dirs, installs skills
3. EXPT terminal status — all 4 EXPT statuses are valid, none allow transitions
4. End-to-end chain — COMP→LOOP→3 EXPTs→FIND; trace COMP walks the hierarchy
5. Skill no-overwrite — reinstall does not clobber user-edited skill files
"""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from specflow.commands import artifact_lint as lint_cmd
from specflow.commands import autoresearch as autoresearch_cmd
from specflow.commands import trace as trace_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import scaffold as scaffold_lib

PACKS_DIR = Path(__file__).parent.parent / "src" / "specflow" / "packs"

RESEARCH_SCHEMAS = {
    "competition": {
        "prefix": "COMP",
        "statuses": ["active", "paused", "completed", "archived"],
    },
    "loop": {
        "prefix": "LOOP",
        "statuses": ["draft", "running", "completed", "plateaued", "aborted"],
    },
    "experiment": {
        "prefix": "EXPT",
        "statuses": ["kept", "discarded", "crashed", "no_op"],
    },
    "finding": {
        "prefix": "FIND",
        "statuses": ["draft", "confirmed", "superseded", "falsified"],
    },
}

_BASE_SPEC_TYPES = [
    ("requirement", "REQ"), ("architecture", "ARCH"), ("detailed-design", "DDD"),
    ("unit-test", "UT"), ("integration-test", "IT"), ("qualification-test", "QT"),
    ("story", "STORY"), ("spike", "SPIKE"), ("decision", "DEC"), ("defect", "DEF"),
]

_BASE_STATUS_FLOW = {
    "draft": [], "approved": ["draft"], "implemented": ["approved"],
    "verified": ["implemented"],
}


def _write_artifact(
    root: Path,
    artifact_id: str,
    art_type: str,
    title: str,
    status: str = "draft",
    body: str = "",
    links: list[dict] | None = None,
    extra_fm: dict | None = None,
) -> Path:
    rel_dir = art_lib.TYPE_TO_DIR.get(art_type, "")
    if not rel_dir:
        raise ValueError(f"Unknown type: {art_type}")
    target_dir = root / "_specflow" / rel_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    fm: dict = {
        "id": artifact_id,
        "title": title,
        "type": art_type,
        "status": status,
        "tags": [],
        "suspect": False,
        "links": links or [],
    }
    if extra_fm:
        fm.update(extra_fm)

    fm_yaml = yaml.dump(fm, default_flow_style=False, sort_keys=False)
    content = f"---\n{fm_yaml}---\n\n# {title}\n\n{body}\n"
    file_path = target_dir / f"{artifact_id}.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def _make_art(
    art_id: str,
    art_type: str,
    status: str = "draft",
    body: str = "body",
    links: list[art_lib.Link] | None = None,
    extra_fm: dict | None = None,
) -> art_lib.Artifact:
    fm: dict = {
        "id": art_id, "title": f"Test {art_id}",
        "type": art_type, "status": status,
    }
    if extra_fm:
        fm.update(extra_fm)
    return art_lib.Artifact(
        path=Path(f"{art_id}.md"),
        frontmatter=fm,
        body=body,
        links=links or [],
    )


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Temp project with base schemas + autoresearch schemas installed."""
    root = tmp_path / "project"
    root.mkdir()
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)

    for art_type, prefix in _BASE_SPEC_TYPES:
        schema = {
            "type": art_type,
            "prefix": prefix,
            "allowed_status": dict(_BASE_STATUS_FLOW),
        }
        (schema_dir / f"{art_type}.yaml").write_text(
            yaml.dump(schema), encoding="utf-8"
        )

    for schema_name in ("competition", "loop", "experiment", "finding"):
        src = PACKS_DIR / "autoresearch" / "schemas" / f"{schema_name}.yaml"
        (schema_dir / f"{schema_name}.yaml").write_text(
            src.read_text(encoding="utf-8"), encoding="utf-8"
        )

    config = {
        "project": {"name": "test-project", "created": "2026-01-01"},
        "impact_analysis": {
            "auto_flag": True, "auto_resolve": False, "remind_after": "7d",
        },
        "artifact_types": (
            [t for t, _ in _BASE_SPEC_TYPES]
            + ["competition", "loop", "experiment", "finding"]
        ),
        "active_packs": ["autoresearch"],
    }
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump(config), encoding="utf-8"
    )

    state = {"current": "idle", "history": []}
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump(state), encoding="utf-8"
    )

    for subdir in [
        "_specflow/specs/requirements", "_specflow/specs/architecture",
        "_specflow/specs/detailed-design", "_specflow/specs/unit-tests",
        "_specflow/specs/integration-tests", "_specflow/specs/qualification-tests",
        "_specflow/work/stories", "_specflow/work/spikes",
        "_specflow/work/decisions", "_specflow/work/defects",
        "_specflow/specs/competitions", "_specflow/specs/loops",
        "_specflow/specs/experiments", "_specflow/specs/findings",
    ]:
        (root / subdir).mkdir(parents=True, exist_ok=True)

    art_lib._load_active_packs(root)

    yield root

    for art_type in ("competition", "loop", "experiment", "finding"):
        prefix = art_lib.TYPE_TO_PREFIX.pop(art_type, None)
        art_lib.TYPE_TO_DIR.pop(art_type, None)
        if prefix:
            art_lib.PREFIX_TO_TYPE.pop(prefix, None)


# ── 1. Schema lifecycle ─────────────────────────────────────────────────────

class TestSchemaLifecycle:

    @pytest.mark.parametrize("art_type,info", list(RESEARCH_SCHEMAS.items()))
    def test_valid_statuses_pass(self, project_root: Path, art_type: str, info: dict):
        for status in info["statuses"]:
            arts = [_make_art(f"{info['prefix']}-001", art_type, status=status)]
            result = lint_cmd._check_status(
                arts, project_root / ".specflow" / "schema"
            )
            assert result["blocking_count"] == 0, (
                f"{art_type} status '{status}' should be valid"
            )

    @pytest.mark.parametrize("art_type,info", list(RESEARCH_SCHEMAS.items()))
    def test_invalid_status_is_blocking(self, project_root: Path, art_type: str, info: dict):
        arts = [_make_art(f"{info['prefix']}-002", art_type, status="nonexistent")]
        result = lint_cmd._check_status(
            arts, project_root / ".specflow" / "schema"
        )
        assert result["blocking_count"] >= 1
        assert "invalid status" in result["detail"]

    def test_comp_does_not_accept_standard_statuses(self, project_root: Path):
        for bad_status in ("draft", "approved", "implemented", "verified"):
            arts = [_make_art("COMP-003", "competition", status=bad_status)]
            result = lint_cmd._check_status(
                arts, project_root / ".specflow" / "schema"
            )
            assert result["blocking_count"] >= 1, (
                f"COMP should not accept status '{bad_status}'"
            )

    def test_loop_does_not_accept_comp_statuses(self, project_root: Path):
        for bad_status in ("active", "archived"):
            arts = [_make_art("LOOP-003", "loop", status=bad_status)]
            result = lint_cmd._check_status(
                arts, project_root / ".specflow" / "schema"
            )
            assert result["blocking_count"] >= 1, (
                f"LOOP should not accept status '{bad_status}'"
            )

    def test_loop_transition_structure(self, project_root: Path):
        schema_path = project_root / ".specflow" / "schema" / "loop.yaml"
        schema = yaml.safe_load(schema_path.read_text())
        allowed = schema["allowed_status"]
        assert allowed["draft"] == [], "draft is an initial status"
        assert "draft" in allowed["running"], "draft→running allowed"
        assert "running" in allowed["completed"], "running→completed allowed"
        assert "running" in allowed["plateaued"], "running→plateaued allowed"
        assert "draft" not in allowed["completed"], "draft→completed NOT allowed"

    def test_comp_transition_structure(self, project_root: Path):
        schema_path = project_root / ".specflow" / "schema" / "competition.yaml"
        schema = yaml.safe_load(schema_path.read_text())
        allowed = schema["allowed_status"]
        assert allowed["active"] == [], "active is an initial status"
        assert "active" in allowed["paused"], "active→paused allowed"
        assert "active" in allowed["completed"], "active→completed allowed"
        assert "paused" not in allowed["completed"], "paused→completed NOT allowed (must resume first)"

    def test_find_transition_structure(self, project_root: Path):
        schema_path = project_root / ".specflow" / "schema" / "finding.yaml"
        schema = yaml.safe_load(schema_path.read_text())
        allowed = schema["allowed_status"]
        assert allowed["draft"] == [], "draft is an initial status"
        assert "draft" in allowed["confirmed"], "draft→confirmed allowed"
        assert "confirmed" in allowed["superseded"], "confirmed→superseded allowed"
        assert "confirmed" in allowed["falsified"], "confirmed→falsified allowed"
        assert "draft" not in allowed["superseded"], "draft→superseded NOT allowed"


# ── 2. Pack install integration ─────────────────────────────────────────────

@pytest.fixture
def fresh_project(tmp_path: Path) -> Path:
    """Minimal project dir with .claude/ marker so platform detection works."""
    root = tmp_path / "fresh-project"
    root.mkdir()
    (root / ".claude").mkdir()
    (root / ".specflow" / "schema").mkdir(parents=True)
    (root / ".specflow" / "standards").mkdir(parents=True)
    config = {
        "project": {"name": "fresh-project", "created": "2026-01-01"},
        "artifact_types": [],
        "active_packs": [],
    }
    (root / ".specflow" / "config.yaml").write_text(
        yaml.dump(config), encoding="utf-8"
    )
    state = {"current": "idle", "history": []}
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump(state), encoding="utf-8"
    )
    return root


class TestPackInstall:

    def test_schemas_copied(self, fresh_project: Path):
        result = scaffold_lib.apply_pack(fresh_project, "autoresearch", PACKS_DIR)
        assert result["ok"]
        schema_dir = fresh_project / ".specflow" / "schema"
        for name in ("competition", "loop", "experiment", "finding"):
            assert (schema_dir / f"{name}.yaml").exists(), f"{name}.yaml not copied"

    def test_directories_created(self, fresh_project: Path):
        scaffold_lib.apply_pack(fresh_project, "autoresearch", PACKS_DIR)
        for rel in ("competitions", "loops", "experiments", "findings"):
            d = fresh_project / "_specflow" / "specs" / rel
            assert d.is_dir(), f"_specflow/specs/{rel}/ not created"
            assert (d / "_index.yaml").exists(), f"_index.yaml missing in {rel}"

    def test_skill_installed(self, fresh_project: Path):
        result = scaffold_lib.apply_pack(fresh_project, "autoresearch", PACKS_DIR)
        assert result["ok"]
        assert "specflow-autoresearch" in result.get("skills_added", [])
        skill_dir = fresh_project / ".claude" / "skills" / "specflow-autoresearch"
        assert skill_dir.is_dir()
        assert (skill_dir / "SKILL.md").exists()

    def test_return_value(self, fresh_project: Path):
        result = scaffold_lib.apply_pack(fresh_project, "autoresearch", PACKS_DIR)
        assert result["ok"]
        assert result["pack"] == "autoresearch"
        for t in ("competition", "loop", "experiment", "finding"):
            assert t in result["types_added"]

    def test_nonexistent_pack_returns_error(self, fresh_project: Path):
        result = scaffold_lib.apply_pack(fresh_project, "no-such-pack", PACKS_DIR)
        assert not result["ok"]
        assert "error" in result

    def test_reinstall_preserves_edited_schema(self, fresh_project: Path):
        result1 = scaffold_lib.apply_pack(fresh_project, "autoresearch", PACKS_DIR)
        assert result1["ok"]

        schema_file = fresh_project / ".specflow" / "schema" / "competition.yaml"
        assert schema_file.exists()

        original = schema_file.read_text(encoding="utf-8")
        edited = original + "\n# user customization — must survive reinstall\n"
        schema_file.write_text(edited, encoding="utf-8")

        result2 = scaffold_lib.apply_pack(fresh_project, "autoresearch", PACKS_DIR)
        assert result2["ok"]

        after = schema_file.read_text(encoding="utf-8")
        assert after == edited, "Edited schema must survive reinstall byte-for-byte"


# ── 3. EXPT terminal status ─────────────────────────────────────────────────

class TestExptTerminalStatus:

    @pytest.mark.parametrize("status", ["kept", "discarded", "crashed", "no_op"])
    def test_all_four_statuses_valid(self, project_root: Path, status: str):
        arts = [_make_art("EXPT-001", "experiment", status=status)]
        result = lint_cmd._check_status(
            arts, project_root / ".specflow" / "schema"
        )
        assert result["blocking_count"] == 0, f"EXPT status '{status}' should be valid"

    def test_no_status_transitions_exist(self, project_root: Path):
        schema_path = project_root / ".specflow" / "schema" / "experiment.yaml"
        schema = yaml.safe_load(schema_path.read_text())
        for status, prereqs in schema["allowed_status"].items():
            assert prereqs == [], (
                f"EXPT '{status}' should be terminal (no incoming transitions), "
                f"but has prereqs {prereqs}"
            )

    def test_invalid_expt_status_blocked(self, project_root: Path):
        for bad in ("draft", "running", "active", "approved"):
            arts = [_make_art("EXPT-002", "experiment", status=bad)]
            result = lint_cmd._check_status(
                arts, project_root / ".specflow" / "schema"
            )
            assert result["blocking_count"] >= 1, (
                f"EXPT should not accept status '{bad}'"
            )

    def test_expt_schemas_are_category_research(self, project_root: Path):
        schema_path = project_root / ".specflow" / "schema" / "experiment.yaml"
        schema = yaml.safe_load(schema_path.read_text())
        assert schema.get("category") == "research"

    def test_auxiliary_metrics_in_optional_fields(self, project_root: Path):
        schema_path = project_root / ".specflow" / "schema" / "experiment.yaml"
        schema = yaml.safe_load(schema_path.read_text())
        assert "auxiliary_metrics" in schema.get("optional_fields", [])

    def test_expt_with_auxiliary_metrics_passes_lint(self, project_root: Path):
        arts = [
            _make_art(
                "EXPT-050", "experiment", status="kept",
                extra_fm={
                    "metric_value": 1.23,
                    "change_category": "features",
                    "summary": "Test with aux metrics",
                    "auxiliary_metrics": {
                        "max_drawdown": 0.12,
                        "total_trades": 340,
                        "f1_score": 0.87,
                        "runtime_seconds": 12.4,
                    },
                },
            )
        ]
        result = lint_cmd._check_status(
            arts, project_root / ".specflow" / "schema"
        )
        assert result["blocking_count"] == 0, "EXPT with auxiliary_metrics should pass lint"


# ── 4. End-to-end chain ─────────────────────────────────────────────────────

class TestEndToEndChain:

    def test_trace_comp_shows_full_hierarchy(self, project_root: Path, capsys):
        _write_artifact(
            project_root, "COMP-001", "competition", "Test Competition",
            status="active",
            extra_fm={
                "created": "2026-05-15",
                "verify_command": "pytest",
                "metric_name": "accuracy",
                "metric_direction": "maximize",
            },
        )
        _write_artifact(
            project_root, "LOOP-001", "loop", "Explore Loop",
            status="completed",
            links=[{"target": "COMP-001", "role": "operates_on"}],
            extra_fm={
                "created": "2026-05-15",
                "competition": "COMP-001",
                "mode": "explore",
                "budget": 10,
            },
        )
        for i, (sid, s) in enumerate(
            [("EXPT-001", "kept"), ("EXPT-002", "discarded"), ("EXPT-003", "kept")]
        ):
            _write_artifact(
                project_root, sid, "experiment", f"Experiment {i+1}",
                status=s,
                links=[{"target": "LOOP-001", "role": "belongs_to"}],
                extra_fm={
                    "created": "2026-05-15",
                    "loop": "LOOP-001",
                    "metric_value": 0.5 + i * 0.1,
                    "change_category": "parameter",
                    "summary": f"Test experiment {i+1}",
                },
            )
        _write_artifact(
            project_root, "FIND-001", "finding", "Key Finding",
            status="confirmed",
            links=[
                {"target": "COMP-001", "role": "belongs_to"},
                {"target": "LOOP-001", "role": "condenses"},
            ],
            extra_fm={
                "created": "2026-05-15",
                "summary": "Explored the space",
                "confidence": "high",
                "competition": "COMP-001",
            },
        )

        rc = trace_cmd.run(project_root, {"artifact_id": "COMP-001"})
        assert rc == 0

        out = capsys.readouterr().out

        assert "COMP-001" in out
        assert "LOOP-001" in out, "LOOP should appear under COMP"
        assert "EXPT-001" in out, "EXPT-001 should appear under LOOP"
        assert "EXPT-002" in out, "EXPT-002 should appear under LOOP"
        assert "EXPT-003" in out, "EXPT-003 should appear under LOOP"
        assert "FIND-001" in out, "FIND should appear under COMP"

        loop_pos = out.find("LOOP-001")
        expt1_pos = out.find("EXPT-001")
        expt2_pos = out.find("EXPT-002")
        expt3_pos = out.find("EXPT-003")
        assert loop_pos < expt1_pos, "EXPT-001 should nest under LOOP-001"
        assert loop_pos < expt2_pos, "EXPT-002 should nest under LOOP-001"
        assert loop_pos < expt3_pos, "EXPT-003 should nest under LOOP-001"

    def test_trace_loop_shows_parent_and_expts(self, project_root: Path, capsys):
        _write_artifact(
            project_root, "COMP-002", "competition", "Comp Two",
            status="active",
            extra_fm={
                "created": "2026-05-15",
                "verify_command": "pytest",
                "metric_name": "f1",
                "metric_direction": "maximize",
            },
        )
        _write_artifact(
            project_root, "LOOP-002", "loop", "Loop Two",
            status="running",
            links=[{"target": "COMP-002", "role": "operates_on"}],
            extra_fm={
                "created": "2026-05-15",
                "competition": "COMP-002",
                "mode": "exploit",
                "budget": 5,
            },
        )
        _write_artifact(
            project_root, "EXPT-010", "experiment", "Expt Ten",
            status="kept",
            links=[{"target": "LOOP-002", "role": "belongs_to"}],
            extra_fm={
                "created": "2026-05-15",
                "loop": "LOOP-002",
                "metric_value": 0.9,
                "change_category": "feature",
                "summary": "Good result",
            },
        )

        rc = trace_cmd.run(project_root, {"artifact_id": "LOOP-002"})
        assert rc == 0

        out = capsys.readouterr().out
        assert "LOOP-002" in out
        assert "COMP-002" in out, "Parent COMP should appear"
        assert "EXPT-010" in out, "EXPT should appear under LOOP"


# ── 5. Skill no-overwrite ───────────────────────────────────────────────────

class TestSkillNoOverwrite:

    def test_reinstall_preserves_edited_skill(self, fresh_project: Path):
        result1 = scaffold_lib.apply_pack(fresh_project, "autoresearch", PACKS_DIR)
        assert result1["ok"]
        assert "specflow-autoresearch" in result1["skills_added"]

        skill_file = (
            fresh_project / ".claude" / "skills"
            / "specflow-autoresearch" / "SKILL.md"
        )
        assert skill_file.exists()

        original = skill_file.read_text(encoding="utf-8")
        edited = original.replace(
            "SpecFlow Autoresearch", "MY CUSTOM EDITED TITLE"
        )
        skill_file.write_text(edited, encoding="utf-8")

        result2 = scaffold_lib.apply_pack(fresh_project, "autoresearch", PACKS_DIR)
        assert result2["ok"]
        assert result2.get("skills_added") == [], "Reinstall should not add skills"

        after = skill_file.read_text(encoding="utf-8")
        assert "MY CUSTOM EDITED TITLE" in after, (
            "User edits should survive reinstall"
        )
        assert after == edited, "Skill file should be byte-identical after reinstall"


# ── 6. Autoresearch CLI subcommand ───────────────────────────────────────

class TestAutoresearchCLI:

    def _setup_comp_and_loop(self, root: Path) -> None:
        _write_artifact(
            root, "COMP-001", "competition", "Test Competition",
            status="active",
            extra_fm={
                "created": "2026-05-15",
                "verify_command": "pytest",
                "metric_name": "Sharpe ratio",
                "metric_direction": "higher_is_better",
            },
        )
        _write_artifact(
            root, "LOOP-001", "loop", "Explore Loop",
            status="running",
            links=[{"target": "COMP-001", "role": "operates_on"}],
            extra_fm={
                "created": "2026-05-15",
                "competition": "COMP-001",
                "mode": "explore",
                "budget": 50,
                "iteration_count": 5,
                "kept_count": 2,
                "discarded_count": 3,
                "best_metric": 1.83,
                "best_experiment": "EXPT-003",
            },
        )
        for i, (sid, status, mv) in enumerate(
            [("EXPT-001", "discarded", 0.5), ("EXPT-002", "kept", 1.2), ("EXPT-003", "kept", 1.83)]
        ):
            _write_artifact(
                root, sid, "experiment", f"Experiment {i+1}",
                status=status,
                links=[{"target": "LOOP-001", "role": "belongs_to"}],
                extra_fm={
                    "created": "2026-05-15",
                    "loop": "LOOP-001",
                    "metric_value": mv,
                    "change_category": "features",
                    "summary": f"Test experiment {i+1}",
                    "auxiliary_metrics": {"max_drawdown": 0.1 * (i + 1), "total_trades": 100 * (i + 1)},
                },
            )
        _write_artifact(
            root, "FIND-001", "finding", "Key Finding",
            status="confirmed",
            links=[
                {"target": "COMP-001", "role": "belongs_to"},
                {"target": "LOOP-001", "role": "condenses"},
            ],
            extra_fm={
                "created": "2026-05-15",
                "summary": "Features beat params",
                "confidence": "high",
                "competition": "COMP-001",
            },
        )

    def test_plan_auto_detects_single_comp(self, project_root: Path, capsys):
        self._setup_comp_and_loop(project_root)
        rc = autoresearch_cmd.run(project_root, {"autoresearch_subcommand": "plan"})
        assert rc == 0
        out = capsys.readouterr().out
        assert "COMP-001" in out
        assert "Sharpe ratio" in out
        assert "Running LOOP detected" in out

    def test_run_prints_protocol(self, project_root: Path, capsys):
        self._setup_comp_and_loop(project_root)
        rc = autoresearch_cmd.run(
            project_root,
            {"autoresearch_subcommand": "run", "competition": "COMP-001"},
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "8-Phase Protocol" in out
        assert "Phase 5: Verify" in out
        assert "Phase 7: Log" in out

    def test_review_shows_findings_and_leaderboard(self, project_root: Path, capsys):
        self._setup_comp_and_loop(project_root)
        rc = autoresearch_cmd.run(
            project_root,
            {"autoresearch_subcommand": "review", "competition": "COMP-001", "top": 5},
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "FIND-001" in out
        assert "EXPT-003" in out
        assert "1.83" in out
        assert "aux:" in out

    def test_leaderboard_ranks_by_metric(self, project_root: Path, capsys):
        self._setup_comp_and_loop(project_root)
        rc = autoresearch_cmd.run(
            project_root,
            {"autoresearch_subcommand": "leaderboard", "competition": "COMP-001", "top": 10},
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "Leaderboard" in out
        pos_003 = out.find("EXPT-003")
        pos_002 = out.find("EXPT-002")
        assert pos_003 < pos_002, "EXPT-003 (1.83) should rank above EXPT-002 (1.2)"

    def test_leaderboard_all_flag(self, project_root: Path, capsys):
        self._setup_comp_and_loop(project_root)
        _write_artifact(
            project_root, "COMP-002", "competition", "Second Competition",
            status="active",
            extra_fm={
                "created": "2026-05-15",
                "verify_command": "pytest",
                "metric_name": "accuracy",
                "metric_direction": "higher_is_better",
            },
        )
        rc = autoresearch_cmd.run(
            project_root,
            {"autoresearch_subcommand": "leaderboard", "all": True, "top": 10},
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "COMP-001" in out
        assert "COMP-002" in out

    def test_no_competitions_returns_error(self, project_root: Path, capsys):
        rc = autoresearch_cmd.run(
            project_root,
            {"autoresearch_subcommand": "plan"},
        )
        assert rc == 1
        out = capsys.readouterr().out
        assert "No competitions found" in out

    def test_no_subcommand_returns_error(self, project_root: Path, capsys):
        rc = autoresearch_cmd.run(project_root, {})
        assert rc == 1


# ── 7. Pack context injection ────────────────────────────────────────────

class TestPackContextInjection:

    def test_apply_pack_returns_context_snippet(self, fresh_project: Path):
        result = scaffold_lib.apply_pack(fresh_project, "autoresearch", PACKS_DIR)
        assert result["ok"]
        assert "context_snippet" in result
        assert "autoresearch" in result["context_snippet"].lower()
        assert "COMP" in result["context_snippet"]
        assert "LOOP" in result["context_snippet"]

    def test_inject_pack_context_creates_section(self, fresh_project: Path):
        agents_md = fresh_project / "AGENTS.md"
        agents_md.write_text("# Existing content\n\nSome text.\n", encoding="utf-8")

        result = scaffold_lib.apply_pack(fresh_project, "autoresearch", PACKS_DIR)
        assert result["ok"]

        snippet = result["context_snippet"]
        assert snippet

        modified = scaffold_lib.inject_pack_context(
            fresh_project, "autoresearch", snippet
        )
        assert modified

        content = agents_md.read_text(encoding="utf-8")
        assert "# Existing content" in content
        assert "<!-- pack:autoresearch context" in content
        assert "Autoresearch Pack" in content

    def test_inject_pack_context_idempotent(self, fresh_project: Path):
        agents_md = fresh_project / "AGENTS.md"
        agents_md.write_text("# Content\n", encoding="utf-8")

        result = scaffold_lib.apply_pack(fresh_project, "autoresearch", PACKS_DIR)
        snippet = result["context_snippet"]

        modified1 = scaffold_lib.inject_pack_context(
            fresh_project, "autoresearch", snippet
        )
        assert modified1

        modified2 = scaffold_lib.inject_pack_context(
            fresh_project, "autoresearch", snippet
        )
        assert not modified2, "Second injection should be no-op"

        content = agents_md.read_text(encoding="utf-8")
        assert content.count("<!-- pack:autoresearch context") == 1


# ── 7b. Base context injection ────────────────────────────────────────────

TEMPLATES_DIR = Path(__file__).parent.parent / "src" / "specflow" / "templates"


class TestBaseContextInjection:

    def test_creates_agents_md_on_fresh_repo(self, fresh_project: Path):
        agents_md = fresh_project / "AGENTS.md"
        assert not agents_md.exists()

        modified = scaffold_lib.inject_base_context(
            fresh_project, TEMPLATES_DIR, "claude-code"
        )
        assert modified

        content = agents_md.read_text(encoding="utf-8")
        assert "<!-- SpecFlow section (auto-generated, do not edit manually) -->" in content
        assert "<!-- End SpecFlow section -->" in content
        assert "## SpecFlow" in content
        assert "specflow update" in content

    def test_appends_to_existing_agents_md(self, fresh_project: Path):
        agents_md = fresh_project / "AGENTS.md"
        agents_md.write_text("# My Project\n\nExisting user content.\n", encoding="utf-8")

        modified = scaffold_lib.inject_base_context(
            fresh_project, TEMPLATES_DIR, "claude-code"
        )
        assert modified

        content = agents_md.read_text(encoding="utf-8")
        assert "# My Project" in content
        assert "Existing user content." in content
        assert "<!-- SpecFlow section (auto-generated, do not edit manually) -->" in content
        lines_before = content.index("<!-- SpecFlow section") < content.index("Existing user content.")
        assert lines_before is False

    def test_idempotent_on_rerun(self, fresh_project: Path):
        agents_md = fresh_project / "AGENTS.md"
        agents_md.write_text("# Content\n", encoding="utf-8")

        modified1 = scaffold_lib.inject_base_context(
            fresh_project, TEMPLATES_DIR, "claude-code"
        )
        assert modified1

        modified2 = scaffold_lib.inject_base_context(
            fresh_project, TEMPLATES_DIR, "claude-code"
        )
        assert not modified2

        content = agents_md.read_text(encoding="utf-8")
        assert content.count("<!-- SpecFlow section (auto-generated, do not edit manually) -->") == 1

    def test_updates_existing_block_on_template_change(self, fresh_project: Path):
        agents_md = fresh_project / "AGENTS.md"
        agents_md.write_text(
            "# Content\n\n<!-- SpecFlow section (auto-generated, do not edit manually) -->\n## Old\n<!-- End SpecFlow section -->\n",
            encoding="utf-8",
        )

        modified = scaffold_lib.inject_base_context(
            fresh_project, TEMPLATES_DIR, "claude-code"
        )
        assert modified

        content = agents_md.read_text(encoding="utf-8")
        assert "## Old" not in content
        assert "## SpecFlow" in content
        assert "# Content" in content
        assert content.count("<!-- SpecFlow section (auto-generated, do not edit manually) -->") == 1

    def test_falls_back_to_claude_md(self, tmp_path: Path):
        root = tmp_path / "project"
        root.mkdir()
        (root / ".claude").mkdir()
        (root / ".specflow" / "schema").mkdir(parents=True)
        (root / ".specflow" / "standards").mkdir(parents=True)
        claude_md = root / "CLAUDE.md"
        claude_md.write_text("# Existing CLAUDE.md\n", encoding="utf-8")

        modified = scaffold_lib.inject_base_context(
            root, TEMPLATES_DIR, "claude-code"
        )
        assert modified

        assert not (root / "AGENTS.md").exists()
        content = claude_md.read_text(encoding="utf-8")
        assert "<!-- SpecFlow section (auto-generated, do not edit manually) -->" in content
        assert "# Existing CLAUDE.md" in content

    def test_base_before_packs_ordering(self, fresh_project: Path):
        agents_md = fresh_project / "AGENTS.md"
        agents_md.write_text("# Content\n", encoding="utf-8")

        scaffold_lib.inject_base_context(fresh_project, TEMPLATES_DIR, "claude-code")

        result = scaffold_lib.apply_pack(fresh_project, "autoresearch", PACKS_DIR)
        snippet = result["context_snippet"]
        scaffold_lib.inject_pack_context(fresh_project, "autoresearch", snippet, "claude-code")

        content = agents_md.read_text(encoding="utf-8")
        base_pos = content.index("<!-- SpecFlow section (auto-generated, do not edit manually) -->")
        pack_pos = content.index("<!-- pack:autoresearch context")
        assert base_pos < pack_pos


# ── 7c. Multi-preset support ────────────────────────────────────────────

class TestMultiPreset:

    def test_two_packs_create_two_sentinel_blocks(self, fresh_project: Path):
        agents_md = fresh_project / "AGENTS.md"
        agents_md.write_text("# Content\n", encoding="utf-8")

        for pack_name in ("autoresearch", "tldr-communication"):
            result = scaffold_lib.apply_pack(fresh_project, pack_name, PACKS_DIR)
            assert result["ok"]
            snippet = result["context_snippet"]
            if snippet:
                scaffold_lib.inject_pack_context(
                    fresh_project, pack_name, snippet, "claude-code"
                )

        content = agents_md.read_text(encoding="utf-8")
        assert "<!-- pack:autoresearch context" in content
        assert "<!-- pack:tldr-communication context" in content
        assert "# Content" in content

    def test_reinstall_preserves_both_packs(self, fresh_project: Path):
        agents_md = fresh_project / "AGENTS.md"
        agents_md.write_text("# Content\n", encoding="utf-8")

        for pack_name in ("autoresearch", "tldr-communication"):
            result = scaffold_lib.apply_pack(fresh_project, pack_name, PACKS_DIR)
            snippet = result["context_snippet"]
            if snippet:
                scaffold_lib.inject_pack_context(
                    fresh_project, pack_name, snippet, "claude-code"
                )

        content_before = agents_md.read_text(encoding="utf-8")

        for pack_name in ("autoresearch", "tldr-communication"):
            result = scaffold_lib.apply_pack(fresh_project, pack_name, PACKS_DIR)
            snippet = result["context_snippet"]
            if snippet:
                scaffold_lib.inject_pack_context(
                    fresh_project, pack_name, snippet, "claude-code"
                )

        content_after = agents_md.read_text(encoding="utf-8")
        assert content_before == content_after


# ── 8. New schema fields (v1.6.1) ───────────────────────────────────────────

class TestNewSchemaFields:

    def test_competition_schema_has_new_fields(self, project_root: Path):
        schema_path = project_root / ".specflow" / "schema" / "competition.yaml"
        schema = yaml.safe_load(schema_path.read_text())
        opts = schema.get("optional_fields", [])
        for field in ("objective_type", "success_criteria", "domain", "pre_check_command",
                      "post_check_command", "noise_characterization", "goals"):
            assert field in opts, f"competition.yaml should have optional field '{field}'"

    def test_experiment_schema_has_new_fields(self, project_root: Path):
        schema_path = project_root / ".specflow" / "schema" / "experiment.yaml"
        schema = yaml.safe_load(schema_path.read_text())
        opts = schema.get("optional_fields", [])
        for field in ("parameters", "model_origin", "sweep_results", "checks",
                      "baseline_note", "diversity_metrics", "failure_analysis",
                      "hypothesis", "hypothesis_outcome"):
            assert field in opts, f"experiment.yaml should have optional field '{field}'"

    def test_loop_schema_has_new_fields(self, project_root: Path):
        schema_path = project_root / ".specflow" / "schema" / "loop.yaml"
        schema = yaml.safe_load(schema_path.read_text())
        opts = schema.get("optional_fields", [])
        for field in ("goal", "required_findings", "termination_suggestions"):
            assert field in opts, f"loop.yaml should have optional field '{field}'"

    def test_finding_schema_has_new_fields(self, project_root: Path):
        schema_path = project_root / ".specflow" / "schema" / "finding.yaml"
        schema = yaml.safe_load(schema_path.read_text())
        opts = schema.get("optional_fields", [])
        for field in ("deployability", "safety_assessment", "applies_to_domain"):
            assert field in opts, f"finding.yaml should have optional field '{field}'"


# ── 9. Autoresearch logging lint (v1.6.1) ──────────────────────────────────

class TestAutoresearchLoggingLint:

    def test_warns_on_missing_domain_aux_metrics(self, project_root: Path):
        _write_artifact(
            project_root, "COMP-010", "competition", "Quant Comp",
            status="active",
            extra_fm={
                "created": "2026-05-15",
                "verify_command": "pytest",
                "metric_name": "Sharpe ratio",
                "metric_direction": "higher_is_better",
                "domain": "quant",
            },
        )
        _write_artifact(
            project_root, "EXPT-100", "experiment", "Quant Test",
            status="kept",
            extra_fm={
                "created": "2026-05-15",
                "loop": "LOOP-010",
                "metric_value": 1.5,
                "change_category": "params",
                "summary": "Test",
                "competition": "COMP-010",
                "parameters": {"learning_rate": 0.01},
                "auxiliary_metrics": {"win_rate": 0.6},  # missing max_drawdown, total_trades, profit_factor, oos_decay
            },
        )
        arts = art_lib.discover_artifacts(project_root)
        result = lint_cmd._check_autoresearch_logging(arts, project_root)
        assert result["warning_count"] > 0
        assert "max_drawdown" in result["detail"]

    def test_warns_on_missing_parameters_for_model_change(self, project_root: Path):
        _write_artifact(
            project_root, "EXPT-101", "experiment", "Model Test",
            status="kept",
            extra_fm={
                "created": "2026-05-15",
                "loop": "LOOP-010",
                "metric_value": 0.9,
                "change_category": "model",
                "summary": "Test",
                "competition": "COMP-010",
            },
        )
        arts = art_lib.discover_artifacts(project_root)
        result = lint_cmd._check_autoresearch_logging(arts, project_root)
        assert result["warning_count"] > 0
        assert "parameters" in result["detail"]

    def test_warns_on_missing_failure_analysis(self, project_root: Path):
        _write_artifact(
            project_root, "EXPT-102", "experiment", "Failed Test",
            status="discarded",
            extra_fm={
                "created": "2026-05-15",
                "loop": "LOOP-010",
                "metric_value": 0.1,
                "change_category": "params",
                "summary": "Test",
                "competition": "COMP-010",
            },
        )
        arts = art_lib.discover_artifacts(project_root)
        result = lint_cmd._check_autoresearch_logging(arts, project_root)
        assert result["warning_count"] > 0
        assert "failure_analysis" in result["detail"]


# ── 10. Autoresearch review warnings (v1.6.1) ──────────────────────────────

class TestAutoresearchReviewWarnings:

    def test_review_warns_completed_loop_with_zero_finds(self, project_root: Path, capsys):
        _write_artifact(
            project_root, "COMP-020", "competition", "Review Test Comp",
            status="active",
            extra_fm={
                "created": "2026-05-15",
                "verify_command": "pytest",
                "metric_name": "accuracy",
                "metric_direction": "higher_is_better",
            },
        )
        _write_artifact(
            project_root, "LOOP-020", "loop", "Review Test Loop",
            status="completed",
            extra_fm={
                "created": "2026-05-15",
                "competition": "COMP-020",
                "mode": "explore",
                "budget": 10,
                "iteration_count": 10,
                "kept_count": 2,
                "discarded_count": 8,
            },
        )
        _write_artifact(
            project_root, "EXPT-200", "experiment", "Review Test Expt",
            status="kept",
            extra_fm={
                "created": "2026-05-15",
                "loop": "LOOP-020",
                "metric_value": 0.95,
                "change_category": "features",
                "summary": "Test expt",
                "parameters": {"lr": 0.01},
            },
        )
        rc = autoresearch_cmd.run(
            project_root,
            {"autoresearch_subcommand": "review", "competition": "COMP-020", "top": 5},
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "zero FINDs" in out


# ── 11. Leaderboard grouping (v1.6.1) ──────────────────────────────────────

class TestLeaderboardGrouping:

    def test_leaderboard_groups_by_model_origin(self, project_root: Path, capsys):
        _write_artifact(
            project_root, "COMP-030", "competition", "Group Comp",
            status="active",
            extra_fm={
                "created": "2026-05-15",
                "verify_command": "pytest",
                "metric_name": "accuracy",
                "metric_direction": "higher_is_better",
            },
        )
        _write_artifact(
            project_root, "LOOP-030", "loop", "Group Loop",
            status="completed",
            extra_fm={
                "created": "2026-05-15",
                "competition": "COMP-030",
                "mode": "explore",
                "budget": 10,
            },
        )
        for i, (mid, mo, mv) in enumerate([
            ("EXPT-301", "pretrained", 0.95),
            ("EXPT-302", "pretrained", 0.92),
            ("EXPT-303", "trained_from_scratch", 0.88),
        ]):
            _write_artifact(
                project_root, mid, "experiment", f"Group Expt {i+1}",
                status="kept",
                extra_fm={
                    "created": "2026-05-15",
                    "loop": "LOOP-030",
                    "metric_value": mv,
                    "change_category": "model",
                    "summary": f"Test {i+1}",
                    "model_origin": mo,
                },
            )
        rc = autoresearch_cmd.run(
            project_root,
            {
                "autoresearch_subcommand": "leaderboard",
                "competition": "COMP-030",
                "group_by": "model_origin",
                "top": 10,
            },
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "pretrained:" in out
        assert "trained_from_scratch:" in out


# ── 12. Generic --set CLI flag (v1.6.1) ────────────────────────────────────
# These exercise the *CLI parser path* (specflow.cli.main), not direct file
# writes. The autoresearch protocols depend on writing arbitrary frontmatter
# (metric_value, change_category, goals, ...) through `create`/`update --set`;
# without this wiring the documented loop fails with "unrecognized arguments".

class TestCreateUpdateSetFlag:

    def _find(self, root: Path, art_id: str):
        for a in art_lib.discover_artifacts(root):
            if a.id == art_id:
                return a
        return None

    def test_create_set_writes_typed_fields(self, project_root: Path, monkeypatch):
        from specflow import cli
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "create", "--type", "experiment", "--title", "CLI experiment",
            "--status", "kept", "--skip-dedup-check", "--body", "experiment body",
            "--set", "loop=LOOP-900",
            "--set", "metric_value=0.93",
            "--set", "change_category=model",
            "--set", "summary=logged via --set",
            "--set", 'parameters={"lr": 0.001, "epochs": 50}',
            "--set", "hypothesis_outcome=supported",
        ])
        assert rc == 0
        # Created EXPT should round-trip the typed fields into frontmatter.
        expts = [a for a in art_lib.discover_artifacts(project_root)
                 if art_lib.get_prefix_from_id(a.id) == "EXPT"]
        assert len(expts) == 1
        fm = expts[0].frontmatter
        assert fm["loop"] == "LOOP-900"
        assert fm["metric_value"] == 0.93           # JSON-parsed to float
        assert fm["change_category"] == "model"
        assert fm["parameters"] == {"lr": 0.001, "epochs": 50}  # JSON dict
        assert fm["hypothesis_outcome"] == "supported"

    def test_update_set_writes_list_field(self, project_root: Path, monkeypatch):
        from specflow import cli
        _write_artifact(
            project_root, "COMP-900", "competition", "Set Comp",
            status="active",
            extra_fm={
                "created": "2026-05-15", "verify_command": "pytest",
                "metric_name": "accuracy", "metric_direction": "higher_is_better",
            },
        )
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "update", "COMP-900",
            "--set", 'goals=["find 3 uncorrelated strategies", "stable walk-forward"]',
            "--set", "domain=quant",
        ])
        assert rc == 0
        fm = self._find(project_root, "COMP-900").frontmatter
        assert fm["domain"] == "quant"
        assert fm["goals"] == ["find 3 uncorrelated strategies", "stable walk-forward"]

    def test_create_set_malformed_returns_error(self, project_root: Path, monkeypatch):
        from specflow import cli
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "create", "--type", "requirement", "--title", "Bad set",
            "--skip-dedup-check", "--set", "noequalshere",
        ])
        assert rc == 1


class TestCLIFlagWiring:
    """Argparse must accept the autoresearch flags — the wiring bug class."""

    def test_leaderboard_accepts_group_and_family_flags(self, project_root: Path, monkeypatch):
        from specflow import cli
        _write_artifact(
            project_root, "COMP-901", "competition", "LB Comp",
            status="active",
            extra_fm={
                "created": "2026-05-15", "verify_command": "pytest",
                "metric_name": "accuracy", "metric_direction": "higher_is_better",
            },
        )
        monkeypatch.chdir(project_root)
        # Previously these flags raised SystemExit(2): "unrecognized arguments".
        rc = cli.main([
            "autoresearch", "leaderboard", "--competition", "COMP-901",
            "--group-by", "model_origin", "--show-family",
        ])
        assert rc == 0


class TestResearchThinkingLenses:
    """v1.6.2: 7 new research lenses registered, per-level defaults, methodology handbook."""

    def test_new_lens_names_in_all_lens_names(self):
        from specflow.lib.techniques import ALL_LENS_NAMES, LENS_CATALOG
        expected = {
            "leakage_audit", "overfitting_multiple_comparisons", "baseline_sanity",
            "distribution_shift", "ablation_attribution", "metric_validity",
            "reproducibility",
        }
        for name in expected:
            assert name in ALL_LENS_NAMES, f"{name} missing from ALL_LENS_NAMES"
            assert name in LENS_CATALOG, f"{name} missing from LENS_CATALOG"

    def test_lens_categories_covers_all(self):
        from specflow.lib.techniques import ALL_LENS_NAMES, LENS_CATEGORIES
        assert set(LENS_CATEGORIES.keys()) == ALL_LENS_NAMES
        valid_cats = {"software", "research", "both"}
        for name, cat in LENS_CATEGORIES.items():
            assert cat in valid_cats, f"{name} has invalid category: {cat}"

    def test_research_lens_names_subset(self):
        from specflow.lib.techniques import RESEARCH_LENS_NAMES, ALL_LENS_NAMES, LENS_CATEGORIES
        assert RESEARCH_LENS_NAMES <= ALL_LENS_NAMES
        for name in RESEARCH_LENS_NAMES:
            assert LENS_CATEGORIES[name] in ("research", "both")

    def test_artifact_level_defaults_all_valid(self):
        from specflow.lib.techniques import (
            ARTIFACT_LEVEL_DEFAULT_LENSES, ALL_LENS_NAMES,
        )
        assert set(ARTIFACT_LEVEL_DEFAULT_LENSES.keys()) == {
            "competition", "loop", "experiment", "finding",
        }
        for level, lenses in ARTIFACT_LEVEL_DEFAULT_LENSES.items():
            for lens in lenses:
                assert lens in ALL_LENS_NAMES, f"{lens} in {level} defaults not in catalog"

    def test_reproducibility_not_in_any_default(self):
        from specflow.lib.techniques import ARTIFACT_LEVEL_DEFAULT_LENSES
        for level, lenses in ARTIFACT_LEVEL_DEFAULT_LENSES.items():
            assert "reproducibility" not in lenses, f"reproducibility in {level} defaults"

    def test_update_accepts_new_lens_names(self, project_root: Path, monkeypatch):
        from specflow import cli
        _write_artifact(
            project_root, "COMP-750", "competition", "Lens Test Comp",
            status="active",
            extra_fm={
                "created": "2026-05-20", "verify_command": "echo 0.5",
                "metric_name": "acc", "metric_direction": "higher_is_better",
            },
        )
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "update", "COMP-750",
            "--thinking-techniques", "leakage_audit,metric_validity,reproducibility",
        ])
        assert rc == 0
        parsed = art_lib.parse_artifact(
            art_lib.resolve_link_target(project_root, "COMP-750")
        )
        techniques = parsed.frontmatter.get("thinking_techniques", [])
        assert "leakage_audit" in techniques
        assert "reproducibility" in techniques

    def test_methodology_handbook_exists(self):
        handbook = (
            PACKS_DIR / "autoresearch" / "skills" / "specflow-autoresearch"
            / "references" / "methodology-handbook.md"
        )
        assert handbook.exists(), f"methodology-handbook.md not found at {handbook}"
        content = handbook.read_text()
        assert "BP-01" in content
        assert "BP-09" in content
        assert "applies_to" in content

    def test_setup_protocol_references_handbook(self):
        proto = (
            PACKS_DIR / "autoresearch" / "skills" / "specflow-autoresearch"
            / "references" / "competition-setup-protocol.md"
        )
        content = proto.read_text()
        assert "methodology-handbook.md" in content

    def test_loop_protocol_references_handbook(self):
        proto = (
            PACKS_DIR / "autoresearch" / "skills" / "specflow-autoresearch"
            / "references" / "autonomous-loop-protocol.md"
        )
        content = proto.read_text()
        assert "methodology-handbook.md" in content

    def test_generic_lens_suffix_present(self):
        from specflow.lib.techniques import _GENERIC_LENS_SUFFIX
        assert "JSON array" in _GENERIC_LENS_SUFFIX
        assert "CHECKLIST CONTEXT" in _GENERIC_LENS_SUFFIX

    def test_lens_prompts_do_not_repeat_boilerplate(self):
        from specflow.lib.techniques import LENS_CATALOG
        for name, prompt in LENS_CATALOG.items():
            assert "JSON array" not in prompt, f"{name} still embeds JSON boilerplate"
            assert "CHECKLIST CONTEXT" not in prompt, f"{name} still embeds checklist boilerplate"

    def test_mixed_review_uses_both_lenses_only(self, monkeypatch):
        from specflow.commands.artifact_review import _prompt_for_techniques
        from specflow.lib.techniques import LENS_CATEGORIES

        monkeypatch.setattr("sys.stdout.isatty", lambda: False)

        mixed = [
            _make_art("EXPT-001", "experiment", status="kept"),
            _make_art("STORY-001", "story", status="draft"),
        ]
        techniques = _prompt_for_techniques(mixed)
        for t in techniques:
            assert LENS_CATEGORIES[t] == "both", f"{t} is not a 'both' lens"

    def test_homogeneous_research_review_uses_level_defaults(self, monkeypatch):
        from specflow.commands.artifact_review import _prompt_for_techniques
        from specflow.lib.techniques import ARTIFACT_LEVEL_DEFAULT_LENSES

        monkeypatch.setattr("sys.stdout.isatty", lambda: False)

        research_only = [
            _make_art("EXPT-002", "experiment", status="kept"),
            _make_art("EXPT-003", "experiment", status="discarded"),
        ]
        techniques = _prompt_for_techniques(research_only)
        expected = ARTIFACT_LEVEL_DEFAULT_LENSES["experiment"]
        assert techniques == expected

    def test_homogeneous_software_review_uses_software_defaults(self, monkeypatch):
        from specflow.commands.artifact_review import _prompt_for_techniques

        monkeypatch.setattr("sys.stdout.isatty", lambda: False)

        software_only = [
            _make_art("STORY-002", "story", status="draft"),
            _make_art("REQ-002", "requirement", status="approved"),
        ]
        techniques = _prompt_for_techniques(software_only)
        assert "devils_advocate" in techniques
        assert "premortem" in techniques
        assert "red_blue_team" in techniques
        assert "assumption_surfacing" in techniques


class TestAutoresearchLogAndSuggestFinds:
    """v1.6.2: smoke tests for autoresearch log and suggest-finds CLI commands."""

    def _setup_comp_and_loop(self, root: Path) -> None:
        _write_artifact(
            root, "COMP-400", "competition", "Log Test Comp",
            status="active",
            extra_fm={
                "created": "2026-05-20",
                "verify_command": "pytest",
                "metric_name": "accuracy",
                "metric_direction": "higher_is_better",
            },
        )
        _write_artifact(
            root, "LOOP-400", "loop", "Log Test Loop",
            status="running",
            extra_fm={
                "created": "2026-05-20",
                "competition": "COMP-400",
                "mode": "explore",
                "budget": 50,
                "iteration_count": 5,
                "kept_count": 2,
                "discarded_count": 3,
                "best_metric": 0.85,
                "best_experiment": "EXPT-401",
            },
        )

    def test_log_creates_expt_and_updates_loop(self, project_root: Path, monkeypatch, capsys):
        from specflow import cli
        self._setup_comp_and_loop(project_root)
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "autoresearch", "log",
            "--loop", "LOOP-400",
            "--status", "kept",
            "--metric-value", "0.92",
            "--change-category", "features",
            "--summary", "Added cross-asset momentum",
        ])
        assert rc == 0

        expts = [a for a in art_lib.discover_artifacts(project_root)
                 if art_lib.get_prefix_from_id(a.id) == "EXPT"]
        assert len(expts) == 1
        fm = expts[0].frontmatter
        assert fm["loop"] == "LOOP-400"
        assert fm["metric_value"] == 0.92
        assert fm["change_category"] == "features"
        assert fm["status"] == "kept"
        assert fm["summary"] == "Added cross-asset momentum"

        loop = art_lib.parse_artifact(
            art_lib.resolve_link_target(project_root, "LOOP-400")
        )
        lf = loop.frontmatter
        assert lf["iteration_count"] == 6
        assert lf["kept_count"] == 3
        assert lf["discarded_count"] == 3
        assert lf["best_metric"] == 0.92

    def test_log_no_update_loop_flag(self, project_root: Path, monkeypatch, capsys):
        from specflow import cli
        self._setup_comp_and_loop(project_root)
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "autoresearch", "log",
            "--loop", "LOOP-400",
            "--status", "discarded",
            "--metric-value", "0.70",
            "--change-category", "params",
            "--summary", "Tuned learning rate",
            "--no-update-loop",
        ])
        assert rc == 0

        loop = art_lib.parse_artifact(
            art_lib.resolve_link_target(project_root, "LOOP-400")
        )
        lf = loop.frontmatter
        assert lf["iteration_count"] == 5  # unchanged
        assert lf["discarded_count"] == 3  # unchanged

    def test_suggest_finds_prints_draft(self, project_root: Path, monkeypatch, capsys):
        from specflow import cli
        self._setup_comp_and_loop(project_root)
        # seed some EXPTs under LOOP-400
        for i, (sid, status, mv, cat) in enumerate([
            ("EXPT-410", "kept", 0.92, "features"),
            ("EXPT-411", "kept", 0.88, "features"),
            ("EXPT-412", "discarded", 0.75, "features"),
            ("EXPT-413", "discarded", 0.60, "params"),
        ]):
            _write_artifact(
                project_root, sid, "experiment", f"Expt {i+1}",
                status=status,
                extra_fm={
                    "created": "2026-05-20",
                    "loop": "LOOP-400",
                    "metric_value": mv,
                    "change_category": cat,
                    "summary": f"Test {i+1}",
                },
            )
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "autoresearch", "suggest-finds",
            "--loop", "LOOP-400",
        ])
        assert rc == 0
        out = capsys.readouterr().out
        assert "what_worked" in out
        assert "features" in out
        assert "params" in out
        assert "LOOP-400" in out

    def test_suggest_finds_writes_draft(self, project_root: Path, monkeypatch, capsys):
        from specflow import cli
        self._setup_comp_and_loop(project_root)
        _write_artifact(
            project_root, "EXPT-420", "experiment", "Expt 5",
            status="kept",
            extra_fm={
                "created": "2026-05-20",
                "loop": "LOOP-400",
                "metric_value": 0.95,
                "change_category": "model",
                "summary": "Switched to transformer",
            },
        )
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "autoresearch", "suggest-finds",
            "--loop", "LOOP-400",
            "--write",
        ])
        assert rc == 0
        finds = [a for a in art_lib.discover_artifacts(project_root)
                 if art_lib.get_prefix_from_id(a.id) == "FIND"]
        assert len(finds) == 1
        fm = finds[0].frontmatter
        assert fm["competition"] == "COMP-400"
        assert fm["source_loop"] == "LOOP-400"
        assert fm["status"] == "draft"


# ── 13. Autoresearch CLI hardening (v1.8.1) ────────────────────────────────
# These tests exercise the real CLI path (cli.main) for autoresearch
# subcommands that were previously only tested via direct run() calls.

class TestAutoresearchCLIHardening:
    """Fill the CLI-path test gap: --set on log, error paths, plan/run/review via cli.main."""

    def _setup_comp_and_loop(self, root: Path) -> None:
        _write_artifact(
            root, "COMP-500", "competition", "CLI Hardening Comp",
            status="active",
            extra_fm={
                "created": "2026-05-20",
                "verify_command": "pytest",
                "metric_name": "accuracy",
                "metric_direction": "higher_is_better",
            },
        )
        _write_artifact(
            root, "LOOP-500", "loop", "CLI Hardening Loop",
            status="running",
            extra_fm={
                "created": "2026-05-20",
                "competition": "COMP-500",
                "mode": "explore",
                "budget": 50,
                "iteration_count": 3,
                "kept_count": 1,
                "discarded_count": 2,
                "best_metric": 0.85,
                "best_experiment": "EXPT-501",
            },
        )
        _write_artifact(
            root, "EXPT-501", "experiment", "Prior Best",
            status="kept",
            extra_fm={
                "created": "2026-05-20",
                "loop": "LOOP-500",
                "metric_value": 0.85,
                "change_category": "features",
                "summary": "Baseline",
            },
        )

    def test_log_with_set_writes_fields(self, project_root: Path, monkeypatch):
        from specflow import cli
        self._setup_comp_and_loop(project_root)
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "autoresearch", "log",
            "--loop", "LOOP-500",
            "--status", "kept",
            "--metric-value", "0.93",
            "--change-category", "model",
            "--summary", "Transformer backbone",
            "--set", "lr=0.001",
            "--set", 'parameters={"lr": 0.001, "layers": 6}',
        ])
        assert rc == 0

        expts = [a for a in art_lib.discover_artifacts(project_root)
                 if art_lib.get_prefix_from_id(a.id) == "EXPT"
                 and a.frontmatter.get("loop") == "LOOP-500"
                 and a.id != "EXPT-501"]
        assert len(expts) == 1
        fm = expts[0].frontmatter
        assert fm["lr"] == 0.001  # json.loads parses "0.001" to float
        assert fm["parameters"] == {"lr": 0.001, "layers": 6}
        assert fm["metric_value"] == 0.93

    def test_log_with_set_json_number(self, project_root: Path, monkeypatch):
        from specflow import cli
        self._setup_comp_and_loop(project_root)
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "autoresearch", "log",
            "--loop", "LOOP-500",
            "--status", "kept",
            "--metric-value", "0.90",
            "--change-category", "params",
            "--summary", "Number test",
            "--set", "batch_size=64",
        ])
        assert rc == 0

        expts = [a for a in art_lib.discover_artifacts(project_root)
                 if art_lib.get_prefix_from_id(a.id) == "EXPT"
                 and a.frontmatter.get("loop") == "LOOP-500"
                 and a.id != "EXPT-501"]
        assert len(expts) == 1
        # "64" is valid JSON → parsed to int
        assert expts[0].frontmatter["batch_size"] == 64

    def test_log_set_malformed_returns_error(self, project_root: Path, monkeypatch, capsys):
        from specflow import cli
        self._setup_comp_and_loop(project_root)
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "autoresearch", "log",
            "--loop", "LOOP-500",
            "--status", "kept",
            "--metric-value", "0.5",
            "--change-category", "params",
            "--summary", "bad set",
            "--set", "no-equals-sign",
        ])
        assert rc == 1
        out = capsys.readouterr().out
        assert "Invalid --set" in out

    def test_log_nonexistent_loop_returns_error(self, project_root: Path, monkeypatch, capsys):
        from specflow import cli
        self._setup_comp_and_loop(project_root)
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "autoresearch", "log",
            "--loop", "LOOP-999",
            "--status", "kept",
            "--metric-value", "0.5",
            "--change-category", "params",
            "--summary", "ghost loop",
        ])
        assert rc == 1
        out = capsys.readouterr().out
        assert "not found" in out

    def test_plan_via_cli(self, project_root: Path, monkeypatch, capsys):
        from specflow import cli
        self._setup_comp_and_loop(project_root)
        monkeypatch.chdir(project_root)
        rc = cli.main(["autoresearch", "plan"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "COMP-500" in out

    def test_run_via_cli(self, project_root: Path, monkeypatch, capsys):
        from specflow import cli
        self._setup_comp_and_loop(project_root)
        monkeypatch.chdir(project_root)
        rc = cli.main(["autoresearch", "run", "--competition", "COMP-500"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "8-Phase Protocol" in out

    def test_review_via_cli(self, project_root: Path, monkeypatch, capsys):
        from specflow import cli
        self._setup_comp_and_loop(project_root)
        monkeypatch.chdir(project_root)
        rc = cli.main(["autoresearch", "review", "--competition", "COMP-500"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "EXPT-501" in out
