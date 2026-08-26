"""STORY-ADDCLI-0e15: specflow autoresearch plan/run/review/leaderboard CLI.

Per-AC evidence for the four verbs, plus the concurrent-LOOP gate moved here
from STORY-SMALLFIX-621b AC1 (the gate belongs where the LOOP lifecycle is
created/started).

AC mapping:
  AC1 plan  → TestPlanCreateUpdate
  AC2 run   → TestRunProtocol
  AC3 review → TestReview
  AC4 leaderboard → TestLeaderboard
  SMALLFIX-621b AC1 (gate) → TestConcurrentLoopGate

These tests scaffold tmp_path projects only; they never touch this repo's
ledger. They exercise the real CLI parser path (cli.main) where useful.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
import pytest

from specflow.commands import autoresearch as autoresearch_cmd
from specflow.lib import artifacts as art_lib

PACKS_DIR = Path(__file__).parent.parent / "src" / "specflow" / "packs"

_BASE_SPEC_TYPES = [
    ("requirement", "REQ"), ("architecture", "ARCH"), ("detailed-design", "DDD"),
    ("unit-test", "UT"), ("integration-test", "IT"), ("qualification-test", "QT"),
    ("story", "STORY"), ("spike", "SPIKE"), ("decision", "DEC"), ("defect", "DEF"),
]
_BASE_STATUS_FLOW = {
    "draft": [], "approved": ["draft"], "implemented": ["approved"],
    "verified": ["implemented"],
}
_RESEARCH_SCHEMAS = ("competition", "loop", "experiment", "finding")


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

    # Keep the directory index in sync so subsequent create_artifact() calls
    # (via the CLI under test) assign the correct next ID instead of colliding
    # with scaffolding-written artifacts.
    index_path = target_dir / "_index.yaml"
    index_data = art_lib._read_index(index_path)
    index_data.setdefault("artifacts", {})[artifact_id] = {
        "id": artifact_id, "title": title, "status": status,
        "tags": [], "fingerprint": fm.get("fingerprint", ""), "children": [],
    }
    num = int(re.search(r"(\d+)$", artifact_id).group(1)) if re.search(r"(\d+)$", artifact_id) else 0
    if num and num >= index_data.get("next_id", 1):
        index_data["next_id"] = num + 1
    art_lib._write_index(index_path, index_data)

    return file_path


def _make_comp(root: Path, comp_id: str = "COMP-001", title: str = "Test Comp",
               direction: str = "higher_is_better", metric: str = "accuracy") -> Path:
    return _write_artifact(
        root, comp_id, "competition", title, status="active",
        extra_fm={
            "created": "2026-05-15",
            "verify_command": "echo 0.5",
            "metric_name": metric,
            "metric_direction": direction,
        },
    )


def _make_loop(root: Path, loop_id: str, comp_id: str, status: str = "draft",
               mode: str = "explore", budget: int = 50, extra: dict | None = None) -> Path:
    fm = {
        "created": "2026-05-15",
        "competition": comp_id,
        "mode": mode,
        "budget": budget,
    }
    if extra:
        fm.update(extra)
    return _write_artifact(
        root, loop_id, "loop", f"Loop {loop_id}", status=status,
        links=[{"target": comp_id, "role": "operates_on"}],
        extra_fm=fm,
    )


def _make_expt(root: Path, expt_id: str, loop_id: str, status: str, metric_value: float,
               category: str = "features", extra: dict | None = None) -> Path:
    fm = {
        "created": "2026-05-15",
        "loop": loop_id,
        "metric_value": metric_value,
        "change_category": category,
        "summary": f"Experiment {expt_id}",
    }
    if extra:
        fm.update(extra)
    return _write_artifact(
        root, expt_id, "experiment", f"Experiment {expt_id}", status=status,
        links=[{"target": loop_id, "role": "belongs_to"}],
        extra_fm=fm,
    )


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Temp project with base + autoresearch schemas and a single COMP."""
    root = tmp_path / "project"
    root.mkdir()
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)

    for art_type, _prefix in _BASE_SPEC_TYPES:
        (schema_dir / f"{art_type}.yaml").write_text(
            yaml.dump({"type": art_type, "prefix": _prefix,
                       "allowed_status": dict(_BASE_STATUS_FLOW)}),
            encoding="utf-8",
        )
    for schema_name in _RESEARCH_SCHEMAS:
        src = PACKS_DIR / "autoresearch" / "schemas" / f"{schema_name}.yaml"
        (schema_dir / f"{schema_name}.yaml").write_text(
            src.read_text(encoding="utf-8"), encoding="utf-8"
        )

    config = {
        "project": {"name": "test-project", "created": "2026-01-01"},
        "impact_analysis": {"auto_flag": True, "auto_resolve": False, "remind_after": "7d"},
        "artifact_types": (
            [t for t, _ in _BASE_SPEC_TYPES] + list(_RESEARCH_SCHEMAS)
        ),
        "active_packs": ["autoresearch"],
    }
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "idle", "history": []}), encoding="utf-8"
    )

    for subdir in [
        "_specflow/specs/competitions", "_specflow/specs/loops",
        "_specflow/specs/experiments", "_specflow/specs/findings",
    ]:
        (root / subdir).mkdir(parents=True, exist_ok=True)

    art_lib._load_active_packs(root)
    _make_comp(root)
    yield root

    for art_type in _RESEARCH_SCHEMAS:
        art_lib.TYPE_TO_PREFIX.pop(art_type, None)
        art_lib.TYPE_TO_DIR.pop(art_type, None)
        prefix = {"competition": "COMP", "loop": "LOOP",
                  "experiment": "EXPT", "finding": "FIND"}[art_type]
        art_lib.PREFIX_TO_TYPE.pop(prefix, None)


def _parse(root: Path, art_id: str) -> art_lib.Artifact:
    return art_lib.parse_artifact(art_lib.resolve_link_target(root, art_id))


# ── AC1: plan creates / updates a LOOP ─────────────────────────────────────


class TestPlanCreateUpdate:
    """AC1: `specflow autoresearch plan` creates or updates a LOOP artifact
    with mode, budget, and knowledge_input."""

    def test_plan_creates_loop_with_mode_budget_knowledge(self, project_root, monkeypatch, capsys):
        from specflow import cli
        monkeypatch.chdir(project_root)
        # Seed a confirmed FIND to load as knowledge_input.
        _write_artifact(
            project_root, "FIND-001", "finding", "Prior insight",
            status="confirmed",
            extra_fm={"created": "2026-05-15", "summary": "features win",
                      "confidence": "high", "competition": "COMP-001"},
        )

        rc = cli.main([
            "autoresearch", "plan",
            "--competition", "COMP-001",
            "--mode", "explore",
            "--budget", "50",
            "--knowledge-input", "FIND-001",
        ])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Planned" in out or "Started" in out

        loops = [a for a in art_lib.discover_artifacts(project_root)
                 if art_lib.get_prefix_from_id(a.id) == "LOOP"]
        assert len(loops) == 1
        fm = loops[0].frontmatter
        assert fm["mode"] == "explore"
        assert fm["budget"] == 50
        assert fm["competition"] == "COMP-001"
        assert fm["knowledge_input"] == ["FIND-001"]
        assert fm["status"] == "draft"  # default, not started

    def test_plan_create_running_with_start(self, project_root, monkeypatch, capsys):
        from specflow import cli
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "autoresearch", "plan",
            "--competition", "COMP-001",
            "--mode", "exploit", "--budget", "10", "--start",
        ])
        assert rc == 0
        loop = _parse(project_root, "LOOP-001")
        assert loop.frontmatter["status"] == "running"
        assert loop.frontmatter["mode"] == "exploit"

    def test_plan_updates_existing_draft_loop(self, project_root, monkeypatch, capsys):
        from specflow import cli
        _make_loop(project_root, "LOOP-001", "COMP-001", status="draft",
                   mode="explore", budget=5)
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "autoresearch", "plan",
            "--competition", "COMP-001",
            "--mode", "exploit", "--budget", "75",
            "--knowledge-input", "FIND-002",
        ])
        assert rc == 0
        loop = _parse(project_root, "LOOP-001")
        # Same LOOP, updated fields.
        assert loop.frontmatter["budget"] == 75
        assert loop.frontmatter["mode"] == "exploit"
        assert loop.frontmatter["knowledge_input"] == ["FIND-002"]
        # No second LOOP created.
        loops = [a for a in art_lib.discover_artifacts(project_root)
                 if art_lib.get_prefix_from_id(a.id) == "LOOP"]
        assert len(loops) == 1

    def test_plan_info_fallback_without_mode_budget(self, project_root, capsys):
        # Backwards-compat: plan with no create params stays the info checklist.
        _make_loop(project_root, "LOOP-001", "COMP-001", status="running",
                   mode="explore", budget=50, extra={"iteration_count": 3})
        rc = autoresearch_cmd.run(project_root, {"autoresearch_subcommand": "plan"})
        assert rc == 0
        out = capsys.readouterr().out
        assert "Autoresearch Plan" in out
        assert "Running LOOP detected" in out

    def test_plan_create_requires_mode_and_budget(self, project_root, monkeypatch, capsys):
        from specflow import cli
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "autoresearch", "plan",
            "--competition", "COMP-001", "--create",
        ])
        assert rc == 1
        out = capsys.readouterr().out
        assert "requires --mode and --budget" in out
        # Nothing created.
        loops = [a for a in art_lib.discover_artifacts(project_root)
                 if art_lib.get_prefix_from_id(a.id) == "LOOP"]
        assert loops == []


# ── AC2: run executes the loop protocol against a COMP ─────────────────────


class TestRunProtocol:
    """AC2: `specflow autoresearch run` executes the autonomous loop protocol
    against a COMP."""

    def test_run_prints_protocol_for_running_loop(self, project_root, capsys):
        _make_loop(project_root, "LOOP-001", "COMP-001", status="running",
                   mode="explore", budget=50, extra={"iteration_count": 2})
        rc = autoresearch_cmd.run(project_root, {
            "autoresearch_subcommand": "run", "competition": "COMP-001",
        })
        assert rc == 0
        out = capsys.readouterr().out
        assert "8-Phase Protocol" in out
        assert "Phase 5: Verify" in out
        assert "Phase 7: Log" in out
        # Running LOOP was not re-started.
        assert "draft → running" not in out

    def test_run_starts_draft_loop(self, project_root, capsys):
        _make_loop(project_root, "LOOP-001", "COMP-001", status="draft",
                   mode="explore", budget=50)
        rc = autoresearch_cmd.run(project_root, {
            "autoresearch_subcommand": "run", "competition": "COMP-001",
        })
        assert rc == 0
        out = capsys.readouterr().out
        assert "draft → running" in out
        assert _parse(project_root, "LOOP-001").frontmatter["status"] == "running"

    def test_run_no_start_keeps_draft(self, project_root, capsys):
        _make_loop(project_root, "LOOP-001", "COMP-001", status="draft",
                   mode="explore", budget=50)
        rc = autoresearch_cmd.run(project_root, {
            "autoresearch_subcommand": "run", "competition": "COMP-001",
            "no_start": True,
        })
        assert rc == 0
        assert _parse(project_root, "LOOP-001").frontmatter["status"] == "draft"


# ── AC3: review displays FINDs and EXPTs with status summaries ─────────────


class TestReview:
    """AC3: `specflow autoresearch review` displays FINDs and EXPTs for a given
    COMP with status summaries."""

    def test_review_shows_findings_and_expts(self, project_root, capsys):
        _make_loop(project_root, "LOOP-001", "COMP-001", status="running",
                   mode="explore", budget=50,
                   extra={"iteration_count": 2, "kept_count": 1})
        _make_expt(project_root, "EXPT-001", "LOOP-001", "kept", 0.92)
        _make_expt(project_root, "EXPT-002", "LOOP-001", "kept", 0.55)
        _write_artifact(
            project_root, "FIND-001", "finding", "Features matter",
            status="confirmed",
            extra_fm={"created": "2026-05-15", "summary": "features beat params",
                      "confidence": "high", "competition": "COMP-001",
                      "source_loop": "LOOP-001"},
        )

        rc = autoresearch_cmd.run(project_root, {
            "autoresearch_subcommand": "review", "competition": "COMP-001", "top": 5,
        })
        assert rc == 0
        out = capsys.readouterr().out
        # FINDs surfaced.
        assert "Findings" in out
        assert "FIND-001" in out
        assert "confirmed" in out
        # EXPTs surfaced with status summaries.
        assert "EXPT-001" in out
        assert "EXPT-002" in out
        # LOOP status summary present.
        assert "iter=2/50" in out


# ── AC4: leaderboard ranks EXPTs by metric value with grouping ─────────────


class TestLeaderboard:
    """AC4: `specflow autoresearch leaderboard` ranks EXPTs by metric value with
    grouping support."""

    def test_leaderboard_ranks_higher_is_better(self, project_root, capsys):
        _make_loop(project_root, "LOOP-001", "COMP-001", status="running",
                   mode="explore", budget=50)
        _make_expt(project_root, "EXPT-001", "LOOP-001", "kept", 0.70)
        _make_expt(project_root, "EXPT-002", "LOOP-001", "kept", 0.95)
        _make_expt(project_root, "EXPT-003", "LOOP-001", "kept", 0.80)
        rc = autoresearch_cmd.run(project_root, {
            "autoresearch_subcommand": "leaderboard", "competition": "COMP-001",
        })
        assert rc == 0
        out = capsys.readouterr().out
        assert out.index("EXPT-002") < out.index("EXPT-003") < out.index("EXPT-001")

    def test_leaderboard_ranks_lower_is_better(self, project_root, capsys):
        # Override the default COMP with a lower-is-better one.
        _write_artifact(
            project_root, "COMP-002", "competition", "Loss Comp", status="active",
            extra_fm={"created": "2026-05-15", "verify_command": "echo 0.5",
                      "metric_name": "loss", "metric_direction": "lower_is_better"},
        )
        _make_loop(project_root, "LOOP-002", "COMP-002", status="running",
                   mode="explore", budget=50)
        _make_expt(project_root, "EXPT-010", "LOOP-002", "kept", 0.30)
        _make_expt(project_root, "EXPT-011", "LOOP-002", "kept", 0.10)
        _make_expt(project_root, "EXPT-012", "LOOP-002", "kept", 0.20)
        rc = autoresearch_cmd.run(project_root, {
            "autoresearch_subcommand": "leaderboard", "competition": "COMP-002",
        })
        assert rc == 0
        out = capsys.readouterr().out
        # Lower is better: 0.10 < 0.20 < 0.30
        assert out.index("EXPT-011") < out.index("EXPT-012") < out.index("EXPT-010")

    def test_leaderboard_group_by_change_category(self, project_root, capsys):
        _make_loop(project_root, "LOOP-001", "COMP-001", status="running",
                   mode="explore", budget=50)
        _make_expt(project_root, "EXPT-001", "LOOP-001", "kept", 0.91, category="features")
        _make_expt(project_root, "EXPT-002", "LOOP-001", "kept", 0.80, category="params")
        rc = autoresearch_cmd.run(project_root, {
            "autoresearch_subcommand": "leaderboard", "competition": "COMP-001",
            "group_by": "change_category",
        })
        assert rc == 0
        out = capsys.readouterr().out
        assert "features:" in out
        assert "params:" in out


# ── STORY-SMALLFIX-621b AC1: concurrent-LOOP gate ──────────────────────────


class TestConcurrentLoopGate:
    """The concurrent-LOOP gate refuses to start a second LOOP on the same COMP
    while one is active. Accounting-friendly: it reports state, never corrupts."""

    def test_plan_refuses_second_running_loop(self, project_root, monkeypatch, capsys):
        from specflow import cli
        _make_loop(project_root, "LOOP-001", "COMP-001", status="running",
                   mode="explore", budget=50)
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "autoresearch", "plan",
            "--competition", "COMP-001",
            "--mode", "exploit", "--budget", "10", "--start",
        ])
        assert rc == 2  # gate refusal
        out = capsys.readouterr().out
        assert "Concurrent-LOOP gate" in out
        assert "LOOP-001" in out
        # No second LOOP was created.
        loops = [a for a in art_lib.discover_artifacts(project_root)
                 if art_lib.get_prefix_from_id(a.id) == "LOOP"]
        assert len(loops) == 1

    def test_plan_allows_draft_while_another_runs(self, project_root, monkeypatch, capsys):
        from specflow import cli
        _make_loop(project_root, "LOOP-001", "COMP-001", status="running",
                   mode="explore", budget=50)
        monkeypatch.chdir(project_root)
        # Drafting the NEXT loop while one runs is fine — only starting is gated.
        rc = cli.main([
            "autoresearch", "plan",
            "--competition", "COMP-001",
            "--mode", "exploit", "--budget", "10",  # default status=draft
        ])
        assert rc == 0
        loops = [a for a in art_lib.discover_artifacts(project_root)
                 if art_lib.get_prefix_from_id(a.id) == "LOOP"]
        assert len(loops) == 2
        statuses = sorted(l.frontmatter["status"] for l in loops)
        assert statuses == ["draft", "running"]

    def test_run_refuses_to_start_second_loop(self, project_root, capsys):
        # One LOOP already running; a second draft LOOP exists. Running the draft
        # must be refused by the gate.
        _make_loop(project_root, "LOOP-001", "COMP-001", status="running",
                   mode="explore", budget=50)
        _make_loop(project_root, "LOOP-002", "COMP-001", status="draft",
                   mode="exploit", budget=10)
        rc = autoresearch_cmd.run(project_root, {
            "autoresearch_subcommand": "run",
            "competition": "COMP-001", "loop": "LOOP-002",
        })
        assert rc == 2
        out = capsys.readouterr().out
        assert "Concurrent-LOOP gate" in out
        assert "LOOP-001" in out
        # The draft LOOP was NOT started; the running one was NOT corrupted.
        assert _parse(project_root, "LOOP-002").frontmatter["status"] == "draft"
        assert _parse(project_root, "LOOP-001").frontmatter["status"] == "running"

    def test_run_starts_draft_when_no_other_running(self, project_root, capsys):
        _make_loop(project_root, "LOOP-001", "COMP-001", status="draft",
                   mode="explore", budget=50)
        rc = autoresearch_cmd.run(project_root, {
            "autoresearch_subcommand": "run", "competition": "COMP-001",
        })
        assert rc == 0
        assert _parse(project_root, "LOOP-001").frontmatter["status"] == "running"


# ── STORY-636: CLI writes traceable link edges ─────────────────────────────

class TestCliWritesTraceEdges:
    """The real CLI paths (plan / log / suggest-finds --write) must write the
    link edges `specflow trace` traverses — frontmatter parent fields alone
    are invisible to the trace graph. Older tests pre-seeded links in
    fixtures, masking this; these tests create everything through the CLI."""

    def test_plan_creates_loop_with_operates_on_edge(self, project_root, monkeypatch, capsys):
        from specflow import cli
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "autoresearch", "plan",
            "--competition", "COMP-001",
            "--mode", "explore", "--budget", "50",
        ])
        assert rc == 0
        loop = _parse(project_root, "LOOP-001")
        edges = {(l.target, l.role) for l in loop.links}
        assert ("COMP-001", "operates_on") in edges

    def test_plan_repairs_legacy_loop_missing_edge(self, project_root, capsys):
        # Legacy shape: frontmatter competition, no link edge (pre-STORY-636 CLI).
        root = project_root
        _write_artifact(
            root, "LOOP-009", "loop", "Legacy loop", status="draft",
            extra_fm={"created": "2026-05-15", "competition": "COMP-001",
                      "mode": "explore", "budget": 50},
        )
        rc = autoresearch_cmd.run(root, {
            "autoresearch_subcommand": "plan", "competition": "COMP-001",
            "mode": "explore", "budget": 60,
        })
        assert rc == 0
        loop = _parse(root, "LOOP-009")
        edges = {(l.target, l.role) for l in loop.links}
        assert ("COMP-001", "operates_on") in edges

    def test_plan_update_preserves_unrelated_links(self, project_root, capsys):
        root = project_root
        _write_artifact(
            root, "LOOP-009", "loop", "Loop with extras", status="draft",
            links=[{"target": "COMP-001", "role": "operates_on"},
                   {"target": "FIND-001", "role": "guided_by"}],
            extra_fm={"created": "2026-05-15", "competition": "COMP-001",
                      "mode": "explore", "budget": 50},
        )
        _write_artifact(
            root, "FIND-001", "finding", "Prior insight", status="confirmed",
            extra_fm={"created": "2026-05-15", "summary": "s",
                      "confidence": "high", "competition": "COMP-001"},
        )
        rc = autoresearch_cmd.run(root, {
            "autoresearch_subcommand": "plan", "competition": "COMP-001",
            "mode": "exploit", "budget": 40,
        })
        assert rc == 0
        loop = _parse(root, "LOOP-009")
        edges = {(l.target, l.role) for l in loop.links}
        assert ("COMP-001", "operates_on") in edges  # not duplicated
        assert ("FIND-001", "guided_by") in edges  # unrelated link survives
        assert len([e for e in edges if e == ("COMP-001", "operates_on")]) == 1

    def test_log_creates_expt_with_belongs_to_edge(self, project_root, monkeypatch, capsys):
        from specflow import cli
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "autoresearch", "plan",
            "--competition", "COMP-001",
            "--mode", "explore", "--budget", "50",
        ])
        assert rc == 0
        rc = cli.main([
            "autoresearch", "log",
            "--loop", "LOOP-001",
            "--status", "kept",
            "--metric-value", "0.62",
            "--change-category", "features",
            "--summary", "added cross-asset features",
        ])
        assert rc == 0
        expt = _parse(project_root, "EXPT-001")
        edges = {(l.target, l.role) for l in expt.links}
        assert ("LOOP-001", "belongs_to") in edges

    def test_suggest_finds_write_creates_find_with_both_edges(self, project_root, capsys):
        root = project_root
        rc = autoresearch_cmd.run(root, {
            "autoresearch_subcommand": "plan", "competition": "COMP-001",
            "mode": "explore", "budget": 50,
        })
        assert rc == 0
        rc = autoresearch_cmd.run(root, {
            "autoresearch_subcommand": "log", "loop": "LOOP-001",
            "status": "kept", "metric_value": 0.6,
            "change_category": "features", "summary": "s",
        })
        assert rc == 0
        rc = autoresearch_cmd.run(root, {
            "autoresearch_subcommand": "suggest-finds",
            "loop": "LOOP-001", "write": True,
        })
        assert rc == 0
        find = _parse(root, "FIND-001")
        edges = {(l.target, l.role) for l in find.links}
        assert ("COMP-001", "belongs_to") in edges
        assert ("LOOP-001", "condenses") in edges

    def test_trace_renders_full_hierarchy_from_cli_created_artifacts(self, project_root, capsys):
        """End-to-end: artifacts created purely via the CLI appear in
        `specflow trace` — the production defect STORY-636 fixed."""
        root = project_root
        rc = autoresearch_cmd.run(root, {
            "autoresearch_subcommand": "plan", "competition": "COMP-001",
            "mode": "explore", "budget": 50,
        })
        assert rc == 0
        rc = autoresearch_cmd.run(root, {
            "autoresearch_subcommand": "log", "loop": "LOOP-001",
            "status": "kept", "metric_value": 0.6,
            "change_category": "features", "summary": "s",
        })
        assert rc == 0
        rc = autoresearch_cmd.run(root, {
            "autoresearch_subcommand": "suggest-finds",
            "loop": "LOOP-001", "write": True,
        })
        assert rc == 0

        id_index = art_lib.build_id_index(art_lib.discover_artifacts(root))
        # EXPT traces upstream to LOOP (and, multi-hop, to COMP).
        chain = art_lib.trace_chain("EXPT-001", id_index, direction="upstream")
        upstream_ids = {n["id"] for n in chain["upstream"]}
        assert "LOOP-001" in upstream_ids
        assert "COMP-001" in upstream_ids
        # FIND traces upstream to both its COMP and LOOP.
        chain = art_lib.trace_chain("FIND-001", id_index, direction="upstream")
        upstream_ids = {n["id"] for n in chain["upstream"]}
        assert {"COMP-001", "LOOP-001"} <= upstream_ids
        # COMP's direct downstream: LOOP (operates_on) and FIND (belongs_to).
        # EXPT hangs off LOOP, not COMP — downstream is direct incoming links.
        chain = art_lib.trace_chain("COMP-001", id_index, direction="downstream")
        downstream_ids = {n["id"] for n in chain["downstream"]}
        assert {"LOOP-001", "FIND-001"} <= downstream_ids
        # EXPT is direct downstream of LOOP.
        chain = art_lib.trace_chain("LOOP-001", id_index, direction="downstream")
        downstream_ids = {n["id"] for n in chain["downstream"]}
        assert "EXPT-001" in downstream_ids

    def test_lint_flags_legacy_missing_link_edges(self, project_root):
        from specflow.commands.artifact_lint import _run_check
        root = project_root
        _write_artifact(
            root, "LOOP-009", "loop", "Legacy loop", status="draft",
            extra_fm={"created": "2026-05-15", "competition": "COMP-001",
                      "mode": "explore", "budget": 50},
        )
        result = _run_check(
            art_lib.discover_artifacts(root), root, "autoresearch-logging"
        )
        assert result["warning_count"] >= 1
        assert "operates_on" in result["detail"]
        assert "--add-link COMP-001:operates_on" in result["detail"]
