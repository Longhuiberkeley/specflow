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

import json
import re
import subprocess
from pathlib import Path

import yaml
import pytest

from specflow.commands import autoresearch as autoresearch_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import evaluator_fingerprint as evaluator_lib
from specflow.lib import locks as locks_lib

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
    # The index is guarded by the repo-wide mutation lock (DEC-093): its
    # read-modify-write must hold it, as every production writer does.
    index_path = target_dir / "_index.yaml"
    with locks_lib.mutation_lock(root):
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
        # REQ-043: the printed protocol teaches coherent hypotheses and
        # evidence/priority, not rotation counts.
        assert "coherent hypothesis" in out
        assert "no rotation quota" in out.lower()
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


class TestLogSetReservedKeys:
    """STORY-637 (v1.14.2): --set must not be able to strip the traceability
    edge or desync parent fields that `autoresearch log` owns."""

    def test_set_links_is_rejected(self, project_root, monkeypatch, capsys):
        from specflow import cli
        monkeypatch.chdir(project_root)
        cli.main([
            "autoresearch", "plan",
            "--competition", "COMP-001", "--mode", "explore", "--budget", "50",
        ])
        rc = cli.main([
            "autoresearch", "log", "--loop", "LOOP-001",
            "--status", "kept", "--metric-value", "0.5",
            "--change-category", "features", "--summary", "s",
            "--set", "links=[]",
        ])
        assert rc == 1
        out = capsys.readouterr().out
        assert "reserved" in out

    def test_set_loop_and_competition_rejected(self, project_root, monkeypatch, capsys):
        from specflow import cli
        monkeypatch.chdir(project_root)
        cli.main([
            "autoresearch", "plan",
            "--competition", "COMP-001", "--mode", "explore", "--budget", "50",
        ])
        for reserved_key in ("loop", "competition", "status"):
            rc = cli.main([
                "autoresearch", "log", "--loop", "LOOP-001",
                "--status", "kept", "--metric-value", "0.5",
                "--change-category", "features", "--summary", "s",
                "--set", f"{reserved_key}=X",
            ])
            assert rc == 1, f"--set {reserved_key} should be rejected"

    def test_log_after_rejected_set_still_writes_edge(self, project_root, monkeypatch, capsys):
        # The guard must not corrupt state: a rejected --set leaves no partial
        # EXPT; a clean retry writes the belongs_to edge.
        from specflow import cli
        monkeypatch.chdir(project_root)
        cli.main([
            "autoresearch", "plan",
            "--competition", "COMP-001", "--mode", "explore", "--budget", "50",
        ])
        cli.main([
            "autoresearch", "log", "--loop", "LOOP-001",
            "--status", "kept", "--metric-value", "0.5",
            "--change-category", "features", "--summary", "s",
            "--set", "links=[]",
        ])
        rc = cli.main([
            "autoresearch", "log", "--loop", "LOOP-001",
            "--status", "kept", "--metric-value", "0.6",
            "--change-category", "features", "--summary", "s2",
        ])
        assert rc == 0
        expts = [a for a in art_lib.discover_artifacts(project_root)
                 if art_lib.get_prefix_from_id(a.id) == "EXPT"]
        assert len(expts) == 1  # the rejected --set created nothing
        edges = {(l.target, l.role) for l in expts[0].links}
        assert ("LOOP-001", "belongs_to") in edges


class TestLintMalformedParentFields:
    """STORY-637: a non-string parent field (hand-edit YAML corruption) must
    produce a lint warning, not a TypeError crash."""

    def test_list_valued_loop_field_warns_not_crashes(self, project_root):
        from specflow.commands.artifact_lint import _run_check
        root = project_root
        # Hand-corrupted shape: loop is a list, not an ID string.
        path = _write_artifact(
            root, "EXPT-009", "experiment", "Corrupt expt", status="kept",
            extra_fm={"created": "2026-05-15", "loop": ["LOOP-001"],
                      "metric_value": 0.5, "change_category": "features",
                      "summary": "s", "competition": "COMP-001"},
        )
        # Ensure the file parses with the list field intact.
        assert path.exists()
        result = _run_check(
            art_lib.discover_artifacts(root), root, "autoresearch-logging"
        )
        assert result["warning_count"] >= 1
        assert "malformed `loop`" in result["detail"]


# ── STORY-663: `autoresearch status` fail/warn exit codes ─────────────────

def _git_ok(root: Path, *argv: str) -> None:
    proc = subprocess.run(
        ["git", *argv], cwd=str(root), capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, f"git {' '.join(argv)} failed: {proc.stderr}"


@pytest.fixture
def git_project_root(project_root: Path) -> Path:
    """project_root + a committed git repo. Phase 0 checks (STORY-663) make
    `status` fail outside a git repo — the loop protocol commits per
    iteration, so the pack's contract is git-backed projects."""
    _git_ok(project_root, "init")
    _git_ok(project_root, "add", ".specflow")
    _git_ok(
        project_root,
        "-c", "user.email=agent@example.com", "-c", "user.name=agent",
        "commit", "-m", "fixture init",
    )
    return project_root


def _make_healthy_loop(root: Path) -> None:
    """A running LOOP with every STORY-663 exit-code gate satisfied."""
    _make_loop(
        root, "LOOP-001", "COMP-001", status="running", mode="explore", budget=5,
        extra={
            "research_agenda": [
                {"direction": "feature mix", "status": "in_progress"},
                {"direction": "calibration", "status": "unexplored"},
            ],
            "iteration_count": 0,
            "eda_completed": True,
        },
    )


class TestStatusExitCodes:
    """STORY-663 + REQ-043: 0 = clear · 3 = warn · 1/2 = fail. The skill prompt
    rule is "if status fails, stop" — these tests pin what fails and what
    warns. REQ-043 moved the warn sources from counts to evidence gaps:
    reassessment fires on evidence-free streaks, never on a rotation quota."""

    def _status(self, root: Path, **extra) -> int:
        args = {"autoresearch_subcommand": "status", "competition": "COMP-001"}
        args.update(extra)
        return autoresearch_cmd.run(root, args)

    def test_clean_repo_healthy_loop_exits_zero(self, git_project_root, capsys):
        _make_healthy_loop(git_project_root)
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "Phase 0 preconditions" in out
        assert "Deterministic accounting" in out

    def test_not_a_git_repo_fails(self, project_root, capsys):
        # project_root (no git) — rev-parse failure is a hard fail (exit 2).
        _make_healthy_loop(project_root)
        assert self._status(project_root) == 2
        out = capsys.readouterr().out
        assert "Not a git repository" in out

    def test_dirty_tree_warns(self, git_project_root, capsys):
        _make_healthy_loop(git_project_root)
        config = git_project_root / ".specflow" / "config.yaml"
        config.write_text(config.read_text() + "# dirty\n", encoding="utf-8")
        assert self._status(git_project_root) == 3
        out = capsys.readouterr().out
        assert "uncommitted change(s) to tracked files" in out

    def test_stale_index_lock_warns(self, git_project_root, capsys):
        _make_healthy_loop(git_project_root)
        (git_project_root / ".git" / "index.lock").write_text("", encoding="utf-8")
        assert self._status(git_project_root) == 3
        out = capsys.readouterr().out
        assert "index.lock" in out

    def test_detached_head_warns(self, git_project_root, capsys):
        _make_healthy_loop(git_project_root)
        _git_ok(git_project_root, "checkout", "--detach")
        assert self._status(git_project_root) == 3
        out = capsys.readouterr().out
        assert "detached" in out

    def test_draft_loop_warns(self, git_project_root, capsys):
        _make_loop(
            git_project_root, "LOOP-001", "COMP-001", status="draft",
            mode="explore", budget=5,
            extra={"research_agenda": [
                {"direction": "a", "status": "unexplored"},
                {"direction": "b", "status": "unexplored"},
            ]},
        )
        assert self._status(git_project_root) == 3
        out = capsys.readouterr().out
        assert "still draft" in out

    def test_evidence_free_discard_streak_warns(self, git_project_root, capsys):
        # REQ-043: five legacy records with no `research_progress` and no
        # outcome labels are an evidence-free streak — a reassessment warn
        # (exit 3), never a structural kill. Unannotated records are read
        # conservatively.
        _make_healthy_loop(git_project_root)
        for i in range(5):
            _make_expt(
                git_project_root, f"EXPT-00{i + 1}", "LOOP-001",
                "discarded", 0.1, category="features",
            )
        assert self._status(git_project_root) == 3
        out = capsys.readouterr().out
        assert "consecutive non-kept experiments with no new evidence" in out
        assert "Reassess the formulation" in out

    def test_alternating_outcome_labels_still_warn(self, git_project_root, capsys):
        # REQ-043: outcome labels alone are not evidence. Alternating
        # invalid/inconclusive labels carry no distinct, anchored
        # `research_progress`, so the streak still warns (the old
        # ≥2-distinct-labels predicate is gone).
        _make_healthy_loop(git_project_root)
        outcomes = ["invalid", "inconclusive", "invalid"]
        for i, outcome in enumerate(outcomes):
            _make_expt(
                git_project_root, f"EXPT-00{i + 1}", "LOOP-001",
                "discarded", 0.1, category="features",
                extra={"hypothesis_outcome": outcome},
            )
        assert self._status(git_project_root) == 3
        out = capsys.readouterr().out
        assert "with no new evidence" in out
        assert "No evidence-free streak detected" not in out

    def test_distinct_research_progress_negative_continues(
        self, git_project_root, capsys
    ):
        # REQ-043: a scientific negative with distinct, anchored evidence and
        # a next decision is meaningful progress — the line may continue.
        _make_healthy_loop(git_project_root)
        decisions = ("revisit", "pursue", "deprioritize")
        for i, decision in enumerate(decisions):
            expt_id = f"EXPT-00{i + 1}"
            _make_expt(
                git_project_root, expt_id, "LOOP-001",
                "discarded", 0.1, category="features",
                extra={
                    "hypothesis_outcome": "not_supported",
                    "research_progress": {
                        "evidence_ref": expt_id,
                        "finding": f"negative finding {i + 1}: depth {i + 1} adds no lift",
                        "next_decision": decision,
                    },
                },
            )
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "No evidence-free streak detected" in out

    def test_old_keep_does_not_suppress_stagnant_tail(
        self, git_project_root, capsys
    ):
        # REQ-043: the accounting window is the last three attempts. A keep
        # outside that window cannot mask a later evidence-free tail.
        _make_healthy_loop(git_project_root)
        _make_expt(git_project_root, "EXPT-001", "LOOP-001", "kept", 0.9,
                   category="features")
        for i in range(2, 5):
            _make_expt(git_project_root, f"EXPT-00{i}", "LOOP-001",
                       "discarded", 0.1, category="features")
        assert self._status(git_project_root) == 3
        out = capsys.readouterr().out
        assert "consecutive 'features' experiments with no new evidence" in out
        assert "consecutive non-kept experiments with no new evidence" in out

    def test_repeated_finding_under_new_refs_does_not_count(
        self, git_project_root, capsys
    ):
        # REQ-043: re-stating an old finding under fresh evidence_refs is not
        # new evidence — novelty is checked against the whole history.
        _make_healthy_loop(git_project_root)
        _make_expt(
            git_project_root, "EXPT-001", "LOOP-001", "discarded", 0.1,
            category="features",
            extra={"research_progress": {
                "evidence_ref": "EXPT-001",
                "finding": "cutoff sweep is flat",
                "next_decision": "revisit",
            }},
        )
        for i in range(2, 5):
            _make_expt(
                git_project_root, f"EXPT-00{i}", "LOOP-001", "discarded", 0.1,
                category="features",
                extra={"research_progress": {
                    "evidence_ref": f"EXPT-00{i}",
                    "finding": "cutoff sweep is flat",
                    "next_decision": "pursue",
                }},
            )
        assert self._status(git_project_root) == 3

    def test_repeated_evidence_ref_does_not_count(self, git_project_root, capsys):
        # REQ-043: a repeated evidence_ref is not new evidence even when the
        # finding text differs, the ref is anchored to the current EXPT, and
        # the scheme is re-spelled (`commit:x` ↔ `x`).
        _make_healthy_loop(git_project_root)
        _make_expt(
            git_project_root, "EXPT-001", "LOOP-001", "discarded", 0.1,
            category="features",
            extra={
                "commit": "beef1234deadbeef",
                "research_progress": {
                    "evidence_ref": "commit:beef1234deadbeef",
                    "finding": "first look is flat",
                    "next_decision": "revisit",
                },
            },
        )
        for i in range(2, 5):
            ref = "beef1234deadbeef" if i % 2 == 0 else "commit:beef1234deadbeef"
            _make_expt(
                git_project_root, f"EXPT-00{i}", "LOOP-001", "discarded", 0.1,
                category="features",
                extra={
                    "commit": "beef1234deadbeef",
                    "research_progress": {
                        "evidence_ref": ref,
                        "finding": f"distinct claim {i}",
                        "next_decision": "pursue",
                    },
                },
            )
        assert self._status(git_project_root) == 3

    def test_malformed_or_untied_progress_is_conservative(
        self, git_project_root, capsys
    ):
        # REQ-043: absent, malformed, partial, and untied records are read as
        # no evidence (existence check is conservative, never optimistic).
        _make_healthy_loop(git_project_root)
        _make_expt(
            git_project_root, "EXPT-001", "LOOP-001", "discarded", 0.1,
            category="features",
            extra={"research_progress": "EXPT-001 was great"},  # not a mapping
        )
        _make_expt(
            git_project_root, "EXPT-002", "LOOP-001", "discarded", 0.1,
            category="features",
            extra={"research_progress": {
                "evidence_ref": "EXPT-002", "finding": "partial record",
            }},  # missing next_decision
        )
        _make_expt(
            git_project_root, "EXPT-003", "LOOP-001", "discarded", 0.1,
            category="features",
            extra={"research_progress": {
                "evidence_ref": "EXPT-001",  # anchored to another record
                "finding": "untied reference",
                "next_decision": "pursue",
            }},
        )
        assert self._status(git_project_root) == 3

    def test_repeat_keeps_without_improvement_do_not_count(
        self, git_project_root, capsys
    ):
        # REQ-043: keep status alone counts only with a measured delta or a
        # new best primary metric. Three keeps at the incumbent best are
        # repeat keeps, not progress.
        _make_healthy_loop(git_project_root)
        _make_expt(git_project_root, "EXPT-001", "LOOP-001", "kept", 0.5,
                   category="features")
        for i in range(2, 5):
            _make_expt(git_project_root, f"EXPT-00{i}", "LOOP-001", "kept",
                       0.5, category="features")
        assert self._status(git_project_root) == 3
        out = capsys.readouterr().out
        assert "consecutive 'features' experiments with no new evidence" in out

    def test_repeat_keeps_lower_is_better_do_not_count(
        self, git_project_root, capsys
    ):
        # REQ-043: the improvement sign follows COMP.metric_direction; equal
        # values are not improvement for lower_is_better either.
        _make_healthy_loop(git_project_root)
        _make_comp(git_project_root, direction="lower_is_better")
        _make_expt(git_project_root, "EXPT-001", "LOOP-001", "kept", 0.4,
                   category="features")
        for i in range(2, 5):
            _make_expt(git_project_root, f"EXPT-00{i}", "LOOP-001", "kept",
                       0.4, category="features")
        assert self._status(git_project_root) == 3

    def test_recent_improving_keep_counts(self, git_project_root, capsys):
        # REQ-043: an improvement inside the recent window is progress, even
        # when the tail's later keeps repeat it.
        _make_healthy_loop(git_project_root)
        _make_expt(git_project_root, "EXPT-001", "LOOP-001", "kept", 0.5,
                   category="features")
        _make_expt(git_project_root, "EXPT-002", "LOOP-001", "kept", 0.6,
                   category="features")
        for i in (3, 4):
            _make_expt(git_project_root, f"EXPT-00{i}", "LOOP-001", "kept",
                       0.6, category="features")
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "No evidence-free streak detected" in out

    def test_repeated_positive_delta_does_not_override_unchanged_metric(
        self, git_project_root, capsys
    ):
        # REQ-043: when a comparable primary metric exists, it decides — a
        # repeated positive delta on unchanged keeps must not suppress
        # reassessment indefinitely.
        _make_healthy_loop(git_project_root)
        _make_expt(git_project_root, "EXPT-001", "LOOP-001", "kept", 0.6,
                   category="features")
        for i in (2, 3, 4):
            _make_expt(
                git_project_root, f"EXPT-00{i}", "LOOP-001", "kept", 0.6,
                category="features", extra={"delta": 1},
            )
        assert self._status(git_project_root) == 3
        out = capsys.readouterr().out
        assert "consecutive 'features' experiments with no new evidence" in out

    def test_finite_delta_is_fallback_when_metric_absent(
        self, git_project_root, capsys
    ):
        # REQ-043: a finite, correctly signed delta is accepted when no
        # comparable primary metric exists on the EXPT (and the accepted
        # EXPT must sit inside the recent window).
        _make_healthy_loop(git_project_root)
        _make_expt(git_project_root, "EXPT-001", "LOOP-001", "kept", 0.5,
                   category="features")
        _make_expt(git_project_root, "EXPT-002", "LOOP-001", "kept", None,
                   category="features", extra={"delta": 0.05})
        for i in (3, 4):
            _make_expt(git_project_root, f"EXPT-00{i}", "LOOP-001", "kept",
                       None, category="features")
        assert self._status(git_project_root) == 0

    def test_nonfinite_metric_or_delta_does_not_count(
        self, git_project_root, capsys
    ):
        # REQ-043: NaN/Infinity are not measured numbers — as a metric they
        # fall back to delta, and as a delta they never count (NaN also
        # compared False for lower_is_better before this fix).
        _make_healthy_loop(git_project_root)
        _make_expt(
            git_project_root, "EXPT-001", "LOOP-001", "kept", float("nan"),
            category="features", extra={"delta": float("nan")},
        )
        _make_expt(
            git_project_root, "EXPT-002", "LOOP-001", "kept", float("inf"),
            category="features", extra={"delta": float("inf")},
        )
        _make_expt(
            git_project_root, "EXPT-003", "LOOP-001", "kept", None,
            category="features", extra={"delta": float("-inf")},
        )
        assert self._status(git_project_root) == 3

    def test_nonfinite_delta_lower_is_better_does_not_count(
        self, git_project_root, capsys
    ):
        # Regression: NaN delta previously satisfied the lower_is_better
        # "improved" comparison and counted as progress.
        _make_healthy_loop(git_project_root)
        _make_comp(git_project_root, direction="lower_is_better")
        for i in range(1, 4):
            _make_expt(
                git_project_root, f"EXPT-00{i}", "LOOP-001", "kept", None,
                category="features", extra={"delta": float("nan")},
            )
        assert self._status(git_project_root) == 3

    def test_evidence_free_category_run_warns(self, git_project_root, capsys):
        # 3+ same-category legacy EXPTs with no annotations: evidence-free,
        # conservative warning.
        _make_healthy_loop(git_project_root)
        for i in range(3):
            _make_expt(git_project_root, f"EXPT-00{i + 1}", "LOOP-001",
                       "discarded", 0.1, category="features")
        assert self._status(git_project_root) == 3
        out = capsys.readouterr().out
        assert "consecutive 'features' experiments with no new evidence" in out

    def test_two_direction_agenda_has_no_minimum_quota(
        self, git_project_root, capsys
    ):
        # REQ-043: decomposition is a hypothesis, not a direction count — a
        # 2-direction agenda passes at full budget.
        _make_loop(
            git_project_root, "LOOP-001", "COMP-001", status="running",
            mode="explore", budget=50,
            extra={
                "research_agenda": [
                    {"direction": "feature mix", "status": "in_progress"},
                    {"direction": "calibration", "status": "unexplored"},
                ],
                "eda_completed": True,
                "iteration_count": 0,
            },
        )
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "2 recorded direction(s)" in out

    def test_missing_research_agenda_warns(self, git_project_root, capsys):
        # The check is presence, not a quota — a missing Phase 0.7 record
        # still warns at full budget.
        _make_loop(git_project_root, "LOOP-001", "COMP-001", status="running",
                   mode="explore", budget=50, extra={"iteration_count": 0})
        assert self._status(git_project_root) == 3
        out = capsys.readouterr().out
        assert "No research agenda recorded" in out

    def test_structural_beats_warn(self, git_project_root, capsys):
        # Multiple running LOOPs (structural fail) + missing agenda (warn):
        # fail dominates → exit 2.
        _make_loop(git_project_root, "LOOP-001", "COMP-001", status="running",
                   mode="explore", budget=50)
        _make_loop(git_project_root, "LOOP-002", "COMP-001", status="running",
                   mode="exploit", budget=50)
        assert self._status(git_project_root) == 2
        out = capsys.readouterr().out
        assert "Multiple running LOOPs" in out

    def test_global_cap_keeps_loop_structural_visible_behind_phase0_warns(
        self, git_project_root, monkeypatch, capsys
    ):
        # STORY-675/DEC-088: the top-3 cap ranks the whole payload, not each
        # section. Three Phase 0 warns previously zeroed the LOOP cap and hid
        # the higher-ranked structural signals (multiple running LOOPs,
        # budget exhausted) behind a mislabeled "+N lower-ranked" line.
        _make_healthy_loop(git_project_root)
        phase_signals = [
            {"state": "warn", "name": f"phase-{i}",
             "message": f"phase warn {i}", "pointer": ""}
            for i in range(3)
        ]
        loop_signals = [
            {"state": "structural", "name": "concurrency",
             "message": "Multiple running LOOPs: LOOP-001, LOOP-002",
             "pointer": "Abort all but one running LOOP before continuing."},
            {"state": "warn", "name": "budget",
             "message": "Budget exhausted (5/5)", "pointer": ""},
        ]
        monkeypatch.setattr(
            autoresearch_cmd, "_phase0_git_signals", lambda *_args: phase_signals
        )
        monkeypatch.setattr(
            autoresearch_cmd, "_assess_loop",
            lambda *_args: loop_signals,
        )

        assert self._status(git_project_root) == 2
        out = capsys.readouterr().out
        assert "Multiple running LOOPs" in out
        # Global top-3 = the structural + the two earliest warns; the other two
        # actionable signals are omitted once with the payload-level count.
        assert "+2 lower-ranked actionable signal(s) omitted" in out

    def test_idle_comp_clean_git_exits_zero(self, git_project_root, capsys):
        # No active LOOP: closure-readiness + Phase 0 only; clean → 0.
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "no active LOOP" in out

    def test_prioritized_direction_without_progress_is_advisory(
        self, git_project_root, capsys
    ):
        # REQ-043: a priority decision should carry its progress note. Missing
        # progress is an advisory (exit stays 0), not a warn/block.
        _make_loop(
            git_project_root, "LOOP-001", "COMP-001", status="running",
            mode="explore", budget=50,
            extra={
                "research_agenda": [
                    {"direction": "feature mix", "status": "in_progress",
                     "priority": "pursue"},
                    {"direction": "calibration", "status": "unexplored"},
                ],
                "eda_completed": True,
                "iteration_count": 0,
            },
        )
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "prioritized direction(s) without a progress note" in out
        assert "Phase 0 preconditions" in out


class TestLogResearchProgress:
    """REQ-043: `autoresearch log --research-progress` is the validated producer
    for the EXPT progress note that `autoresearch status` reads over its recent
    window."""

    def _plan(self, project_root: Path, monkeypatch) -> int:
        from specflow import cli
        monkeypatch.chdir(project_root)
        return cli.main([
            "autoresearch", "plan", "--competition", "COMP-001",
            "--mode", "explore", "--budget", "50",
        ])

    def test_log_research_progress_round_trips(self, project_root, monkeypatch, capsys):
        from specflow import cli
        assert self._plan(project_root, monkeypatch) == 0
        note = {
            "evidence_ref": "commit:a1b2c3d",
            "finding": "cutoff above 0.6 degrades recall",
            "next_decision": "revisit",
        }
        rc = cli.main([
            "autoresearch", "log", "--loop", "LOOP-001",
            "--status", "discarded", "--metric-value", "0.71",
            "--change-category", "params", "--summary", "cutoff sweep",
            "--research-progress", json.dumps(note),
        ])
        assert rc == 0
        expt = _parse(project_root, "EXPT-001")
        assert expt.frontmatter["research_progress"] == note

    def test_log_research_progress_malformed_rejected(
        self, project_root, monkeypatch, capsys
    ):
        from specflow import cli
        assert self._plan(project_root, monkeypatch) == 0
        rc = cli.main([
            "autoresearch", "log", "--loop", "LOOP-001",
            "--status", "discarded", "--metric-value", "0.71",
            "--change-category", "params", "--summary", "cutoff sweep",
            "--research-progress", '{"evidence_ref": "EXPT-001"}',
        ])
        assert rc == 1
        out = capsys.readouterr().out
        assert "Invalid --research-progress" in out
        assert "missing non-empty string field 'finding'" in out
        expts = [
            a for a in art_lib.discover_artifacts(project_root)
            if art_lib.get_prefix_from_id(a.id) == "EXPT"
        ]
        assert expts == [], "malformed progress must create nothing"

    def test_log_research_progress_not_json_rejected(
        self, project_root, monkeypatch, capsys
    ):
        from specflow import cli
        assert self._plan(project_root, monkeypatch) == 0
        rc = cli.main([
            "autoresearch", "log", "--loop", "LOOP-001",
            "--status", "kept", "--metric-value", "0.72",
            "--change-category", "features", "--summary", "s",
            "--research-progress", "not-json",
        ])
        assert rc == 1
        assert "Invalid --research-progress" in capsys.readouterr().out

    def test_set_research_progress_is_reserved(self, project_root, monkeypatch, capsys):
        from specflow import cli
        assert self._plan(project_root, monkeypatch) == 0
        rc = cli.main([
            "autoresearch", "log", "--loop", "LOOP-001",
            "--status", "kept", "--metric-value", "0.72",
            "--change-category", "features", "--summary", "s",
            "--set", 'research_progress={"evidence_ref": "EXPT-001"}',
        ])
        assert rc == 1
        assert "reserved" in capsys.readouterr().out


class TestEvidenceAnchoring:
    """Narrow regression pins for `_evidence_ref_is_anchored` false anchors
    (REQ-043): prefix collisions, empty/one-char commit matches, and the
    tautological path self-mention inside `research_progress`."""

    def _expt(self, art_id: str = "EXPT-001", fm_extra: dict | None = None,
              body: str = "") -> art_lib.Artifact:
        fm = {
            "id": art_id, "type": "experiment", "status": "discarded",
            "loop": "LOOP-001", "metric_value": 0.1,
            "change_category": "features", "summary": "x",
            "research_progress": {
                "evidence_ref": "placeholder",
                "finding": "f",
                "next_decision": "pursue",
            },
        }
        if fm_extra:
            fm.update(fm_extra)
        return art_lib.Artifact(
            path=Path(f"{art_id}.md"), frontmatter=fm, body=body, links=[],
        )

    def test_exact_id_and_fragment_only(self, tmp_path: Path):
        anchored = autoresearch_cmd._evidence_ref_is_anchored
        art = self._expt("EXPT-001")
        assert anchored(art, "EXPT-001", tmp_path) is True
        assert anchored(art, "EXPT-001#verify-log", tmp_path) is True
        # Prefix collision: a longer, different EXPT id is not this EXPT.
        assert anchored(art, "EXPT-0010", tmp_path) is False
        assert anchored(art, "see EXPT-001", tmp_path) is False

    def test_commit_anchor_requires_exact_or_hex_abbreviation(self, tmp_path: Path):
        anchored = autoresearch_cmd._evidence_ref_is_anchored
        art = self._expt("EXPT-002", fm_extra={"commit": "abcdef1234567890"})
        assert anchored(art, "abcdef1234567890", tmp_path) is True
        assert anchored(art, "commit:abcdef1234567890", tmp_path) is True
        assert anchored(art, "commit:abcdef1", tmp_path) is True  # 7-hex prefix
        assert anchored(art, "commit:abcdef", tmp_path) is False  # 6 chars
        assert anchored(art, "commit:a", tmp_path) is False       # 1 char
        assert anchored(art, "commit:", tmp_path) is False        # empty body
        assert anchored(art, "commit:zzzzzzzz", tmp_path) is False  # non-hex

    def test_path_anchor_cannot_self_certify(self, tmp_path: Path):
        anchored = autoresearch_cmd._evidence_ref_is_anchored
        target = tmp_path / "logs" / "run.json"
        target.parent.mkdir()
        target.write_text("{}", encoding="utf-8")
        # The ref lives inside `research_progress` itself; it is not logged
        # elsewhere on the record, so the record mention is tautological.
        art = self._expt("EXPT-003")
        art.frontmatter["research_progress"]["evidence_ref"] = "logs/run.json"
        assert anchored(art, "logs/run.json", tmp_path) is False
        # Logged in a real output field and present on disk: anchored.
        art = self._expt("EXPT-003", fm_extra={"checks": ["logs/run.json"]})
        assert anchored(art, "logs/run.json", tmp_path) is True
        # Logged but missing on disk: not anchored.
        assert anchored(art, "logs/missing.json", tmp_path) is False

    def test_scheme_respelling_is_the_same_ref(self):
        normalised_ref = autoresearch_cmd._normalised_ref
        assert normalised_ref("commit:abc123") == normalised_ref("abc123")
        assert normalised_ref("path:logs/run.json") == normalised_ref("logs/run.json")
        assert normalised_ref("ABC123") == normalised_ref("abc123")


class TestAutoresearchFrontier:
    def test_full_ledger_covers_lineage_noise_width_agenda_and_revisit(
        self, project_root, capsys, monkeypatch,
    ):
        from specflow import cli

        _make_loop(
            project_root, "LOOP-001", "COMP-001", status="completed",
            extra={"research_agenda": [
                {"direction": "feature family alpha", "status": "in_progress",
                 "category": "features", "strategy_family": "linear"},
                {"direction": "new neighborhoods", "status": "unexplored"},
            ]},
        )
        art_lib.update_artifact(
            project_root, "COMP-001", noise_characterization={"sigma": 0.05}
        )
        for expt_id, metric in (("EXPT-001", 1.0), ("EXPT-002", 1.01), ("EXPT-003", 1.02)):
            _make_expt(
                project_root, expt_id, "LOOP-001", "kept", metric,
                category="features",
                extra={"lineage": "linear-feature-chain", "iteration": int(expt_id[-3:]),
                       "strategy_family": "linear", "research_question": "feature family alpha"},
            )
        _make_expt(
            project_root, "EXPT-004", "LOOP-001", "discarded", 0.8,
            category="model", extra={"strategy_family": "tree", "iteration": 4},
        )
        _make_expt(
            project_root, "EXPT-005", "LOOP-001", "discarded", 0.7,
            category="params", extra={"strategy_family": "svm", "iteration": 5},
        )

        monkeypatch.chdir(project_root)
        rc = cli.main([
            "autoresearch", "frontier", "--comp", "COMP-001", "--json",
        ])
        assert rc == 0
        ledger = json.loads(capsys.readouterr().out)
        assert ledger["competition"]["id"] == "COMP-001"
        assert ledger["noise"]["sigma"] == 0.05
        chain = next(row for row in ledger["lineages"] if row["lineage"] == "linear-feature-chain")
        assert chain["depth"] == 3
        assert chain["within_noise_streak"] == 2
        assert chain["depth_exhausted"] is True
        assert ledger["width"]["strategy_family_count"] == 3
        assert ledger["width"]["agenda_coverage"] == {"covered": 1, "total": 2, "ratio": 0.5}
        assert [entry["direction"] for entry in ledger["width"]["unexplored_neighborhoods"]] == [
            "new neighborhoods"
        ]
        assert {state["code"] for state in ledger["states"]} >= {
            "depth_exhausted", "breadth_without_depth",
        }
        assert {item["move"] for item in ledger["move_menu"]} == {
            "switch formulation", "restart with memory", "landscape re-survey",
        }
        assert {item["experiment"] for item in ledger["revisit_candidates"]} == {
            "EXPT-004", "EXPT-005",
        }
        schema = yaml.safe_load(
            (PACKS_DIR / "autoresearch" / "schemas" / "experiment.yaml").read_text()
        )
        assert {"lineage", "strategy_family"} <= set(schema["optional_fields"])

    def test_missing_lineage_is_singleton_and_missing_noise_states_caveat(self, project_root):
        _make_loop(project_root, "LOOP-001", "COMP-001", status="completed",
                   extra={"research_agenda": []})
        _make_expt(project_root, "EXPT-001", "LOOP-001", "discarded", 0.2,
                   extra={"strategy_family": "one-off"})
        ledger = autoresearch_cmd._frontier_ledger(
            project_root, _parse(project_root, "COMP-001")
        )
        assert ledger["lineages"] == [{
            "lineage": "singleton:EXPT-001", "explicit_lineage": False,
            "depth": 1, "attempts": ["EXPT-001"],
            "strategy_families": ["features::one-off"], "measured_gains": [],
            "within_noise_streak": 0, "depth_exhausted": False,
        }]
        assert ledger["noise"]["sigma"] is None
        assert "raw gains" in ledger["noise"]["caveat"]
        assert ledger["width"]["agenda_coverage"] == {"covered": 0, "total": 0, "ratio": 0.0}
        assert any(state["code"] == "empty_agenda" for state in ledger["states"])

    def test_frontier_default_view_shows_top_signals_and_full_ledger_pointer(
        self, project_root, capsys,
    ):
        _make_loop(project_root, "LOOP-001", "COMP-001", status="completed")
        comp_dir = project_root / "_specflow" / "specs" / "competitions"
        rc = autoresearch_cmd.run(project_root, {
            "autoresearch_subcommand": "frontier", "comp": str(comp_dir),
        })
        assert rc == 0
        out = capsys.readouterr().out
        assert "Top frontier signals" in out
        assert "Advisory move menu" in out
        assert "Full ledger: specflow autoresearch frontier --comp COMP-001 --json" in out

    def test_anchored_analysis_no_op_does_not_consume_evidence_window(
        self, git_project_root, capsys,
    ):
        _make_healthy_loop(git_project_root)
        for expt_id in ("EXPT-001", "EXPT-002"):
            _make_expt(git_project_root, expt_id, "LOOP-001", "discarded", 0.1,
                       category="features")
        _make_expt(
            git_project_root, "EXPT-003", "LOOP-001", "no_op", 0.1,
            category="analysis",
            extra={"research_progress": {
                "evidence_ref": "EXPT-003", "finding": "OOF residual slice saved",
                "next_decision": "pursue",
            }},
        )
        _make_expt(git_project_root, "EXPT-004", "LOOP-001", "discarded", 0.1,
                   category="features")
        rc = autoresearch_cmd.run(git_project_root, {
            "autoresearch_subcommand": "status", "competition": "COMP-001",
        })
        assert rc == 3
        out = capsys.readouterr().out
        assert "consecutive 'features' experiments with no new evidence" in out
        assert "consecutive non-kept experiments with no new evidence" in out

    def test_module_has_no_iteration_count_keyed_rotation_rule(self):
        import ast
        import re

        source = Path(autoresearch_cmd.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.If, ast.While)):
                continue
            condition = ast.unparse(node.test)
            if "iteration_count" not in condition:
                continue
            consequence = ast.unparse(node)
            assert not re.search(
                r"\b(?:rotate|rotation|switch_category|force_category|rotation_quota)\w*\b",
                consequence,
                flags=re.IGNORECASE,
            )

    def test_status_eda_is_not_applicable_without_domain_lenses(self, project_root):
        _make_loop(project_root, "LOOP-001", "COMP-001", status="running")
        signals = autoresearch_cmd._assess_loop(
            project_root, _parse(project_root, "COMP-001"), _parse(project_root, "LOOP-001")
        )
        eda = next(signal for signal in signals if signal["name"] == "eda")
        assert eda["state"] == "not-applicable"
        assert "unspecified" in eda["message"]
        assert not any(signal["name"] == "agenda-revision" for signal in signals)

    def test_status_offers_agenda_revision_command_after_applicable_eda(
        self, project_root, capsys,
    ):
        art_lib.update_artifact(project_root, "COMP-001", domain="tabular_ml")
        _make_loop(
            project_root, "LOOP-001", "COMP-001", status="running",
            extra={"eda_completed": True, "eda_summary": "Fold integrity and imbalance reviewed"},
        )
        rc = autoresearch_cmd.run(project_root, {
            "autoresearch_subcommand": "status", "competition": "COMP-001",
        })
        assert rc == 2  # project_root is intentionally not a git repository
        out = capsys.readouterr().out
        assert "EDA is recorded for tabular_ml" in out
        assert "agenda-revision" in out
        assert "specflow update LOOP-001 --set research_agenda='[...]'" in out

    def test_analysis_no_op_log_accepts_and_renders_anchored_progress(
        self, project_root, monkeypatch, capsys,
    ):
        from specflow import cli

        _make_loop(project_root, "LOOP-001", "COMP-001", status="running")
        monkeypatch.chdir(project_root)
        progress = {
            "evidence_ref": "EXPT-001",
            "finding": "OOF residuals cluster in sparse-feature rows",
            "next_decision": "pursue",
        }
        rc = cli.main([
            "autoresearch", "log", "--loop", "LOOP-001",
            "--status", "no_op", "--change-category", "analysis",
            "--summary", "sliced OOF residuals by feature availability",
            "--research-progress", json.dumps(progress),
        ])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Created EXPT-001" in out
        expt = _parse(project_root, "EXPT-001")
        assert expt.status == "no_op"
        assert expt.frontmatter["change_category"] == "analysis"
        assert expt.frontmatter["research_progress"] == progress

    def test_plan_inherit_seeds_directions_open_entries_and_latest_brief(
        self, project_root, monkeypatch, capsys,
    ):
        from specflow import cli

        _make_loop(
            project_root, "LOOP-001", "COMP-001", status="completed",
            mode="exploit", budget=25,
            extra={
                "unexplored_directions": [
                    "test sparse-feature interactions",
                    {"direction": "check subgroup calibration", "rationale": "OOF gap"},
                ],
                "research_agenda": [
                    {"direction": "revise thresholding", "status": "in_progress",
                     "expected_impact": "medium", "rationale": "prior residual pattern"},
                    {"direction": "closed direction", "status": "exhausted"},
                ],
                "condensation_brief_10": "Older brief: compare feature groups",
                "condensation_brief_20": "Latest brief: inspect regime-specific errors",
            },
        )
        monkeypatch.chdir(project_root)
        rc = cli.main(["autoresearch", "plan", "--inherit", "LOOP-001"])
        assert rc == 0
        assert "research_agenda: 4 seeded direction(s)" in capsys.readouterr().out
        followup = _parse(project_root, "LOOP-002")
        assert followup.status == "draft"
        assert followup.frontmatter["mode"] == "exploit"
        assert followup.frontmatter["budget"] == 25
        agenda = followup.frontmatter["research_agenda"]
        directions = {entry["direction"] for entry in agenda}
        assert "test sparse-feature interactions" in directions
        assert "check subgroup calibration" in directions
        assert "revise thresholding" in directions
        brief_seed = next(entry for entry in agenda if "Latest brief:" in entry["direction"])
        assert "latest condensation brief" in brief_seed["rationale"].lower()
        assert "Latest brief: inspect regime-specific errors" in brief_seed["rationale"]
        assert "Older brief" not in brief_seed["rationale"]
        assert all(entry.get("rationale", "").strip() for entry in agenda)
        assert not any(entry["direction"] == "closed direction" for entry in agenda)

    def test_plan_inherit_preserves_existing_draft_agenda_when_source_has_no_memory(
        self, project_root, monkeypatch, capsys,
    ):
        # A completed source with no durable memory seeds [] — that must never
        # wipe the auto-selected draft LOOP's authored agenda. The outcome is
        # loud, not silent.
        from specflow import cli

        _make_loop(project_root, "LOOP-001", "COMP-001", status="completed",
                   mode="explore", budget=25)
        _make_loop(
            project_root, "LOOP-002", "COMP-001", status="draft",
            mode="explore", budget=25,
            extra={"research_agenda": [
                {"direction": "author's own direction", "status": "unexplored"},
            ]},
        )
        monkeypatch.chdir(project_root)
        rc = cli.main(["autoresearch", "plan", "--inherit", "LOOP-001"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "not clobbered" in out
        followup = _parse(project_root, "LOOP-002")
        agenda = followup.frontmatter["research_agenda"]
        assert [entry["direction"] for entry in agenda] == ["author's own direction"]

    def test_plan_inherit_merges_new_seeds_and_dedupes_against_existing_agenda(
        self, project_root, monkeypatch, capsys,
    ):
        # Merge-never-replace applies to the agenda the way it already applies
        # to links: new inherited directions append, duplicates are dropped,
        # existing entries keep their own metadata.
        from specflow import cli

        _make_loop(
            project_root, "LOOP-001", "COMP-001", status="completed",
            mode="explore", budget=25,
            extra={"unexplored_directions": [
                "fresh inherited direction", "brand new direction",
            ]},
        )
        _make_loop(
            project_root, "LOOP-002", "COMP-001", status="draft",
            mode="explore", budget=25,
            extra={"research_agenda": [
                {"direction": "author's own direction", "status": "unexplored"},
                {"direction": "fresh inherited direction", "status": "unexplored"},
            ]},
        )
        monkeypatch.chdir(project_root)
        rc = cli.main(["autoresearch", "plan", "--inherit", "LOOP-001"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "merged 1 inherited seed(s)" in out
        followup = _parse(project_root, "LOOP-002")
        directions = [
            entry["direction"] for entry in followup.frontmatter["research_agenda"]
        ]
        assert directions == [
            "author's own direction", "fresh inherited direction",
            "brand new direction",
        ]

    def test_review_requires_condensation_brief_for_completed_loop(self, project_root, capsys):
        _make_loop(project_root, "LOOP-001", "COMP-001", status="completed")
        _make_loop(
            project_root, "LOOP-002", "COMP-001", status="completed",
            extra={"condensation_brief_20": "Keep regime-specific diagnostic"},
        )
        assert _parse(project_root, "LOOP-001").status == "completed"
        assert autoresearch_cmd._latest_condensation_brief(_parse(project_root, "LOOP-001")) is None
        assert autoresearch_cmd._latest_condensation_brief(_parse(project_root, "LOOP-002"))
        rc = autoresearch_cmd.run(project_root, {
            "autoresearch_subcommand": "review", "competition": "COMP-001",
        })
        assert rc == 0  # the requirement is advisory, not a measurement gate
        out = capsys.readouterr().out
        assert out.count("without a condensation brief") == 1
        assert "required at LOOP completion" in out
        assert "specflow update LOOP-001 --set condensation_briefs='[...]'" in out

    def test_status_ranks_caps_actionable_signals_and_points_to_frontier(
        self, git_project_root, monkeypatch, capsys,
    ):
        _make_healthy_loop(git_project_root)
        signals = [
            {"state": "advisory", "name": f"advisory-{i}", "message": f"advice {i}", "pointer": ""}
            for i in range(5)
        ]
        signals.extend([
            {"state": "warn", "name": "warning", "message": "warn", "pointer": ""},
            {"state": "structural", "name": "critical", "message": "critical", "pointer": ""},
        ])
        monkeypatch.setattr(autoresearch_cmd, "_assess_loop", lambda *_args: signals)
        rc = autoresearch_cmd.run(git_project_root, {
            "autoresearch_subcommand": "status", "competition": "COMP-001",
        })
        assert rc == 2
        out = capsys.readouterr().out
        accounting = out.split("Deterministic accounting:", 1)[1]
        assert accounting.index("critical:") < accounting.index("warning:") < accounting.index("advisory-0:")
        assert "advisory-1:" not in accounting
        assert "advisory-2:" not in accounting
        assert "+4 lower-ranked actionable signal(s) omitted" in accounting
        assert "Full frontier ledger: specflow autoresearch frontier --comp COMP-001 --json" in accounting

    def test_status_no_longer_uses_iteration_count_checkpoint_for_condensation(self):
        source = Path(autoresearch_cmd.__file__).read_text(encoding="utf-8")
        assert "iteration_count % 10" not in source
        assert "iteration_count and iteration_count %" not in source


# ── STORY-676 (REQ-047): evaluator fingerprint and drift routing ────────────


def _create_comp_cli(root: Path, title: str, verify_command: str) -> str:
    """Create a COMP through the real CLI; return its ID."""
    from specflow import cli
    rc = cli.main([
        "create", "--type", "competition", "--title", title,
        "--status", "active", "--skip-dedup-check",
        "--body", "Evaluator fingerprint fixture",
        "--set", f"verify_command={verify_command}",
        "--set", "metric_name=accuracy",
        "--set", "metric_direction=higher_is_better",
    ])
    assert rc == 0
    comps = [
        a for a in art_lib.discover_artifacts(root)
        if art_lib.get_prefix_from_id(a.id) == "COMP" and a.title == title
    ]
    assert len(comps) == 1
    return comps[0].id


class TestEvaluatorFingerprintSetup:
    """AC1: COMP.evaluator_fingerprint (verify command plus evaluation-script
    hashes) is recorded at setup and changes when an eval-script hash changes."""

    def test_create_records_fingerprint_at_setup(self, project_root, monkeypatch, capsys):
        (project_root / "scripts").mkdir()
        (project_root / "scripts" / "eval.py").write_text("print(0.5)\n")
        monkeypatch.chdir(project_root)
        comp_id = _create_comp_cli(
            project_root, "Setup fingerprint comp", "python scripts/eval.py"
        )
        out = capsys.readouterr().out
        comp = _parse(project_root, comp_id)
        fp = comp.frontmatter.get("evaluator_fingerprint")
        expected = evaluator_lib.compute_evaluator_fingerprint(
            project_root, "python scripts/eval.py"
        )
        assert fp == expected
        assert fp.startswith("sha256:")
        assert f"Evaluator fingerprint: {fp}" in out
        # The setup checklist surfaces the recorded identity.
        rc = autoresearch_cmd.run(
            project_root, {"autoresearch_subcommand": "plan", "competition": comp_id}
        )
        assert rc == 0
        assert f"Eval fp:       {fp}" in capsys.readouterr().out

    def test_fingerprint_changes_when_eval_script_hash_changes(
        self, project_root, monkeypatch,
    ):
        scripts = project_root / "scripts"
        scripts.mkdir()
        eval_py = scripts / "eval.py"
        eval_py.write_text("print(0.5)\n")
        fp1 = evaluator_lib.compute_evaluator_fingerprint(
            project_root, "python scripts/eval.py"
        )

        # Pure filesystem hashing: identical content keeps the fingerprint
        # even when rewritten.
        eval_py.write_text("print(0.5)\n")
        assert (
            evaluator_lib.compute_evaluator_fingerprint(
                project_root, "python scripts/eval.py"
            )
            == fp1
        )

        # A changed evaluation-script hash changes the fingerprint.
        eval_py.write_text("print(0.9)\n")
        fp2 = evaluator_lib.compute_evaluator_fingerprint(
            project_root, "python scripts/eval.py"
        )
        assert fp2 != fp1

        # Files the verify command does not run are not part of the evaluator.
        (project_root / "unrelated.py").write_text("print('unused')\n")
        assert (
            evaluator_lib.compute_evaluator_fingerprint(
                project_root, "python scripts/eval.py"
            )
            == fp2
        )

        # The verify command itself is covered too.
        assert (
            evaluator_lib.compute_evaluator_fingerprint(
                project_root, "python scripts/eval.py --seed 1"
            )
            != fp2
        )

        # The recorded setup value tracks the change across setups.
        monkeypatch.chdir(project_root)
        comp1 = _create_comp_cli(project_root, "First exam", "python scripts/eval.py")
        assert _parse(project_root, comp1).frontmatter["evaluator_fingerprint"] == fp2
        eval_py.write_text("print(0.7)\n")
        fp3 = evaluator_lib.compute_evaluator_fingerprint(
            project_root, "python scripts/eval.py"
        )
        assert fp3 != fp2
        comp2 = _create_comp_cli(project_root, "Second exam", "python scripts/eval.py")
        assert _parse(project_root, comp2).frontmatter["evaluator_fingerprint"] == fp3

    def test_log_stamps_expt_under_current_fingerprint(
        self, project_root, monkeypatch,
    ):
        from specflow import cli
        (project_root / "scripts").mkdir()
        (project_root / "scripts" / "eval.py").write_text("print(0.5)\n")
        monkeypatch.chdir(project_root)
        comp_id = _create_comp_cli(project_root, "Stamp comp", "python scripts/eval.py")
        assert cli.main([
            "autoresearch", "plan", "--competition", comp_id,
            "--mode", "explore", "--budget", "10",
        ]) == 0
        rc = cli.main([
            "autoresearch", "log", "--loop", "LOOP-001",
            "--status", "kept", "--metric-value", "0.6",
            "--change-category", "features", "--summary", "unchanged harness",
        ])
        assert rc == 0
        expt = _parse(project_root, "EXPT-001")
        assert expt.frontmatter["evaluator_fingerprint"] == (
            _parse(project_root, comp_id).frontmatter["evaluator_fingerprint"]
        )
        # Unchanged harness → nothing to flag.
        from specflow.commands.artifact_lint import _run_check
        result = _run_check(
            art_lib.discover_artifacts(project_root), project_root, "fingerprint-drift"
        )
        assert result["warning_count"] == 0
        assert result["blocking_count"] == 0

    def test_log_rejects_set_evaluator_fingerprint(self, project_root, monkeypatch, capsys):
        from specflow import cli
        _make_loop(project_root, "LOOP-001", "COMP-001", status="running")
        monkeypatch.chdir(project_root)
        rc = cli.main([
            "autoresearch", "log", "--loop", "LOOP-001",
            "--status", "kept", "--metric-value", "0.5",
            "--change-category", "features", "--summary", "s",
            "--set", "evaluator_fingerprint=sha256:000000000000",
        ])
        assert rc == 1
        assert "reserved" in capsys.readouterr().out

    def test_update_set_cannot_rewrite_frozen_fingerprint(
        self, project_root, monkeypatch, capsys,
    ):
        # The generic frontmatter editor must not launder evaluator drift in
        # one command: the frozen setup stamp (autoresearch.py reserves the key
        # on `log`) is equally reserved on `update --set` — for the COMP and
        # for the EXPT harness stamp.
        from specflow import cli
        (project_root / "scripts").mkdir()
        (project_root / "scripts" / "eval.py").write_text("print(0.5)\n")
        monkeypatch.chdir(project_root)
        comp_id = _create_comp_cli(
            project_root, "Frozen fingerprint comp", "python scripts/eval.py"
        )
        before = _parse(project_root, comp_id).frontmatter["evaluator_fingerprint"]
        rc = cli.main([
            "update", comp_id,
            "--set", "evaluator_fingerprint=sha256:deadbeef0000",
        ])
        assert rc == 1
        out = capsys.readouterr().out
        assert "reserved" in out
        assert "successor COMP" in out
        assert _parse(project_root, comp_id).frontmatter["evaluator_fingerprint"] == before


class TestFingerprintDriftLint:
    """AC2/AC3: fingerprint-drift lint check — once per COMP, successor-COMP
    routing, never per-EXPT, never retroactive for pre-fingerprint EXPTs."""

    def _lint(self, root: Path) -> dict:
        from specflow.commands.artifact_lint import _run_check
        return _run_check(art_lib.discover_artifacts(root), root, "fingerprint-drift")

    def _setup_fingerprinted_comp(self, root: Path, title: str,
                                  verify_command: str) -> str:
        from specflow import cli
        comp_id = _create_comp_cli(root, title, verify_command)
        assert cli.main([
            "autoresearch", "plan", "--competition", comp_id,
            "--mode", "explore", "--budget", "10",
        ]) == 0
        return comp_id

    def test_check_is_registered(self):
        from specflow.commands import artifact_lint
        assert "fingerprint-drift" in artifact_lint.CHECK_NAMES

    def test_flags_once_per_comp_with_successor_routing(
        self, project_root, monkeypatch,
    ):
        from specflow import cli
        (project_root / "scripts").mkdir()
        eval_py = project_root / "scripts" / "eval.py"
        eval_py.write_text("print(0.5)\n")
        monkeypatch.chdir(project_root)
        comp_id = self._setup_fingerprinted_comp(
            project_root, "Drift comp", "python scripts/eval.py"
        )
        # The harness drifts after setup; EXPTs are logged under it.
        eval_py.write_text("print(0.9)\n")
        for summary in ("first drifted run", "second drifted run"):
            assert cli.main([
                "autoresearch", "log", "--loop", "LOOP-001",
                "--status", "kept", "--metric-value", "0.6",
                "--change-category", "features", "--summary", summary,
            ]) == 0

        result = self._lint(project_root)
        assert result["blocking_count"] == 0  # advisory only (DEC-088)
        assert result["warning_count"] == 1  # ONCE per COMP, never per EXPT
        detail = result["detail"]
        assert detail.count("⚠") == 1  # exactly one finding
        assert comp_id in detail
        assert "successor" in detail
        assert "derives_from" in detail
        assert "EXPT-001" in detail and "EXPT-002" in detail
        assert "rolling-evaluation.md" in detail

    def test_flags_once_per_comp_across_multiple_comps(self, project_root, monkeypatch):
        from specflow import cli
        scripts = project_root / "scripts"
        scripts.mkdir()
        (scripts / "eval_a.py").write_text("print(0.5)\n")
        (scripts / "eval_b.py").write_text("print(0.5)\n")
        monkeypatch.chdir(project_root)
        comp_a = self._setup_fingerprinted_comp(
            project_root, "Drift comp A", "python scripts/eval_a.py"
        )
        comp_b = self._setup_fingerprinted_comp(
            project_root, "Drift comp B", "python scripts/eval_b.py"
        )
        (scripts / "eval_a.py").write_text("print(0.9)\n")
        (scripts / "eval_b.py").write_text("print(0.9)\n")
        assert cli.main([
            "autoresearch", "log", "--loop", "LOOP-001",
            "--status", "kept", "--metric-value", "0.6",
            "--change-category", "features", "--summary", "drifted a",
        ]) == 0
        assert cli.main([
            "autoresearch", "log", "--loop", "LOOP-002",
            "--status", "kept", "--metric-value", "0.4",
            "--change-category", "features", "--summary", "drifted b",
        ]) == 0

        result = self._lint(project_root)
        assert result["blocking_count"] == 0
        assert result["warning_count"] == 2  # one finding per drifted COMP
        detail = result["detail"]
        assert detail.count("⚠") == 2
        assert comp_a in detail and comp_b in detail

    def test_never_retroactive_for_pre_fingerprint_expts(
        self, project_root, monkeypatch,
    ):
        (project_root / "scripts").mkdir()
        eval_py = project_root / "scripts" / "eval.py"
        eval_py.write_text("print(0.5)\n")
        monkeypatch.chdir(project_root)
        self._setup_fingerprinted_comp(
            project_root, "Historical comp", "python scripts/eval.py"
        )
        # Harness drifts on disk, but the historical EXPT predates fingerprint
        # stamps — nothing may fire retroactively (AC3).
        eval_py.write_text("print(0.9)\n")
        _make_expt(project_root, "EXPT-009", "LOOP-001", "kept", 0.5)

        # Likewise a stamped EXPT under a COMP that predates recorded setup
        # fingerprints has no identity to drift from.
        _make_loop(project_root, "LOOP-002", "COMP-001", status="running")
        _make_expt(
            project_root, "EXPT-010", "LOOP-002", "kept", 0.5,
            extra={"evaluator_fingerprint": "sha256:deadbeef0000"},
        )

        result = self._lint(project_root)
        assert result["warning_count"] == 0
        assert result["blocking_count"] == 0


# ── STORY-677 (REQ-047): jump flags, guard metrics, external scores ────────


class _IntegrityStatusMixin:
    """Shared plumbing: a healthy running LOOP on COMP-001 + status runs."""

    def _status(self, root: Path) -> int:
        return autoresearch_cmd.run(
            root, {"autoresearch_subcommand": "status", "competition": "COMP-001"}
        )

    def _setup(self, root: Path, sigma: float = 0.01, **noise_extra) -> None:
        _make_healthy_loop(root)
        noise = {"sigma": sigma, **noise_extra}
        art_lib.update_artifact(root, "COMP-001", noise_characterization=noise)


class TestJumpAdvisory(_IntegrityStatusMixin):
    """AC1: the mechanism-explanation advisory fires only ABOVE k x noise sigma."""

    def test_jump_above_threshold_fires_mechanism_advisory(
        self, git_project_root, capsys
    ):
        # Δ0.05 = 5x sigma 0.01, above the default k=3x threshold.
        self._setup(git_project_root)
        _make_expt(git_project_root, "EXPT-001", "LOOP-001", "kept", 0.50)
        _make_expt(git_project_root, "EXPT-002", "LOOP-001", "kept", 0.55)
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "mechanism explanation required" in out
        assert "jump: EXPT-002" in out
        assert "5.0x noise sigma" in out

    def test_jump_below_threshold_stays_silent(self, git_project_root, capsys):
        # Δ0.02 = 2x sigma 0.01 — at or below k=3x: no advisory at all.
        self._setup(git_project_root)
        _make_expt(git_project_root, "EXPT-001", "LOOP-001", "kept", 0.50)
        _make_expt(git_project_root, "EXPT-002", "LOOP-001", "kept", 0.52)
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "mechanism explanation required" not in out
        assert "jump: " not in out

    def test_jump_k_is_denominated_by_noise_sigma(self, git_project_root, capsys):
        # k x noise sigma: the same Δ0.05 flags at k=1 and stays silent at k=10.
        self._setup(git_project_root, jump_k=10.0)
        _make_expt(git_project_root, "EXPT-001", "LOOP-001", "kept", 0.50)
        _make_expt(git_project_root, "EXPT-002", "LOOP-001", "kept", 0.55)
        assert self._status(git_project_root) == 0
        assert "mechanism explanation required" not in capsys.readouterr().out

        root = git_project_root
        art_lib.update_artifact(
            root, "COMP-001", noise_characterization={"sigma": 0.01, "jump_k": 1.0}
        )
        assert self._status(root) == 0
        assert "mechanism explanation required" in capsys.readouterr().out

    def test_no_noise_floor_never_flags(self, git_project_root, capsys):
        # No probe sigma to denominate against → never a jump flag; the block
        # says so while it renders other integrity records.
        _make_healthy_loop(git_project_root)
        _make_expt(
            git_project_root, "EXPT-001", "LOOP-001", "kept", 0.50,
            extra={"guard_metrics": {"max_drawdown": 0.10}},
        )
        _make_expt(
            git_project_root, "EXPT-002", "LOOP-001", "kept", 0.90,
            extra={"guard_metrics": {"max_drawdown": 0.11}},
        )
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "mechanism explanation required" not in out
        assert "guard-regression warning" not in out
        assert "Noise sigma unavailable" in out

    def test_jump_flag_is_advisory_only(self, git_project_root, capsys):
        # DEC-088: measurement advises, never gates — a flagged jump leaves
        # the status exit code clear.
        self._setup(git_project_root)
        _make_expt(git_project_root, "EXPT-001", "LOOP-001", "kept", 0.50)
        _make_expt(git_project_root, "EXPT-002", "LOOP-001", "kept", 0.95)
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "Research integrity (advisory):" in out
        assert "mechanism explanation required" in out


class TestGuardRegressionWarning(_IntegrityStatusMixin):
    """AC2: a primary gain with a beyond-noise guard regression warns."""

    def test_primary_gain_with_beyond_noise_guard_regression_warns(
        self, git_project_root, capsys
    ):
        self._setup(git_project_root)
        _make_expt(
            git_project_root, "EXPT-001", "LOOP-001", "kept", 0.50,
            extra={"guard_metrics": {"max_drawdown": 0.10}},
        )
        _make_expt(
            git_project_root, "EXPT-002", "LOOP-001", "kept", 0.51,
            extra={"guard_metrics": {"max_drawdown": 0.15}},
        )
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "guard-regression warning" in out
        assert "max_drawdown" in out
        assert "EXPT-002" in out

    def test_guard_regression_within_noise_stays_silent(
        self, git_project_root, capsys
    ):
        # +0.005 regression is within 1x sigma 0.01 — not "beyond noise".
        self._setup(git_project_root)
        _make_expt(
            git_project_root, "EXPT-001", "LOOP-001", "kept", 0.50,
            extra={"guard_metrics": {"max_drawdown": 0.10}},
        )
        _make_expt(
            git_project_root, "EXPT-002", "LOOP-001", "kept", 0.51,
            extra={"guard_metrics": {"max_drawdown": 0.105}},
        )
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "guard-regression warning" not in out

    def test_guard_improvement_never_warns(self, git_project_root, capsys):
        self._setup(git_project_root)
        _make_expt(
            git_project_root, "EXPT-001", "LOOP-001", "kept", 0.50,
            extra={"guard_metrics": {"max_drawdown": 0.10}},
        )
        _make_expt(
            git_project_root, "EXPT-002", "LOOP-001", "kept", 0.51,
            extra={"guard_metrics": {"max_drawdown": 0.05}},
        )
        assert self._status(git_project_root) == 0
        assert "guard-regression warning" not in capsys.readouterr().out

    def test_higher_is_better_guard_direction(self, git_project_root, capsys):
        # Explicit direction flips the adverse side: win_rate dropping is the
        # regression for a higher_is_better guard.
        self._setup(git_project_root)
        _make_expt(
            git_project_root, "EXPT-001", "LOOP-001", "kept", 0.50,
            extra={"guard_metrics": {"win_rate": {"value": 0.60,
                                                  "direction": "higher_is_better"}}},
        )
        _make_expt(
            git_project_root, "EXPT-002", "LOOP-001", "kept", 0.51,
            extra={"guard_metrics": {"win_rate": {"value": 0.50,
                                                  "direction": "higher_is_better"}}},
        )
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "guard-regression warning" in out
        assert "win_rate" in out

    def test_no_warning_without_a_primary_gain(self, git_project_root, capsys):
        # The guard warning only guards gains: a falling primary metric with a
        # guard move is not a gain-guard coincidence.
        self._setup(git_project_root)
        _make_expt(
            git_project_root, "EXPT-001", "LOOP-001", "kept", 0.50,
            extra={"guard_metrics": {"max_drawdown": 0.10}},
        )
        _make_expt(
            git_project_root, "EXPT-002", "LOOP-001", "discarded", 0.45,
            extra={"guard_metrics": {"max_drawdown": 0.15}},
        )
        assert self._status(git_project_root) in (0, 3)
        assert "guard-regression warning" not in capsys.readouterr().out

    def test_guard_regression_warning_is_advisory_only(
        self, git_project_root, capsys
    ):
        # DEC-088: the warning never gates — status still exits clear.
        self._setup(git_project_root)
        _make_expt(
            git_project_root, "EXPT-001", "LOOP-001", "kept", 0.50,
            extra={"guard_metrics": {"max_drawdown": 0.10}},
        )
        _make_expt(
            git_project_root, "EXPT-002", "LOOP-001", "kept", 0.51,
            extra={"guard_metrics": {"max_drawdown": 0.15}},
        )
        assert self._status(git_project_root) == 0
        assert "guard-regression warning" in capsys.readouterr().out


class TestExternalScoreRelation(_IntegrityStatusMixin):
    """AC3: CV-external relation with demotion; offline fallback otherwise."""

    def _seed_external_chain(self, root: Path) -> None:
        _make_expt(
            root, "EXPT-001", "LOOP-001", "kept", 0.50,
            extra={"external_score": {"value": 0.71, "source": "holdout-2026"}},
        )
        # CV rises while the external score falls → inconsistent → demoted.
        _make_expt(
            root, "EXPT-002", "LOOP-001", "kept", 0.55,
            extra={"external_score": {"value": 0.69, "source": "holdout-2026"}},
        )
        # CV and external rise together → consistent.
        _make_expt(
            root, "EXPT-003", "LOOP-001", "kept", 0.60,
            extra={"external_score": {"value": 0.75, "source": "holdout-2026"}},
        )

    def test_relation_renders_and_demotes_inconsistent_gains(
        self, git_project_root, capsys
    ):
        self._setup(git_project_root)
        art_lib.update_artifact(
            git_project_root, "COMP-001", external_leaderboard="holdout-2026"
        )
        self._seed_external_chain(git_project_root)
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "CV-external relation" in out
        assert "holdout-2026" in out
        lines = out.splitlines()
        expt2 = next(line for line in lines if "EXPT-002" in line and "cv=" in line)
        assert "demoted" in expt2
        expt3 = next(line for line in lines if "EXPT-003" in line and "cv=" in line)
        assert "demoted" not in expt3
        assert "consistent" in expt3

    def test_external_scores_without_leaderboard_fall_back_offline(
        self, git_project_root, capsys
    ):
        # No COMP.external_leaderboard → offline fallback: guards plus
        # trial-count-deflated metrics, never the CV-external relation.
        self._setup(git_project_root)
        _make_expt(
            git_project_root, "EXPT-001", "LOOP-001", "kept", 0.50,
            extra={
                "external_score": 0.71,
                "guard_metrics": {"max_drawdown": 0.10},
            },
        )
        _make_expt(
            git_project_root, "EXPT-002", "LOOP-001", "kept", 0.55,
            extra={
                "external_score": 0.69,
                "guard_metrics": {"max_drawdown": 0.15},
            },
        )
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "offline fallback" in out
        assert "trial-count-deflated metrics" in out
        assert "guard max_drawdown" in out
        assert "CV-external relation" not in out
        assert "demoted" not in out

    def test_bare_number_external_score_accepted(self, git_project_root, capsys):
        self._setup(git_project_root)
        art_lib.update_artifact(
            git_project_root, "COMP-001", external_leaderboard="kaggle-lb"
        )
        _make_expt(
            git_project_root, "EXPT-001", "LOOP-001", "kept", 0.50,
            extra={"external_score": 0.71},
        )
        _make_expt(
            git_project_root, "EXPT-002", "LOOP-001", "kept", 0.55,
            extra={"external_score": 0.69},
        )
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "CV-external relation" in out
        assert "external=0.69" in out

    def test_no_leaderboard_without_integrity_records_renders_nothing(
        self, git_project_root, capsys
    ):
        # Default loops (no guard/external records) keep the status output
        # free of integrity noise.
        self._setup(git_project_root)
        _make_expt(git_project_root, "EXPT-001", "LOOP-001", "kept", 0.50)
        _make_expt(git_project_root, "EXPT-002", "LOOP-001", "kept", 0.51)
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "Research integrity" not in out
        assert "offline fallback" not in out


class TestQuantMetricBundleSetup:
    """AC4: a single-metric quant COMP is rejected at setup in favor of the
    metric bundle with a fixed horizon (competition-setup-protocol.md)."""

    def _create_quant(self, root: Path, monkeypatch, title: str, extra: list[str]):
        from specflow import cli
        monkeypatch.chdir(root)
        return cli.main([
            "create", "--type", "competition", "--title", title,
            "--status", "active", "--skip-dedup-check", "--body", "quant fixture",
            "--set", "verify_command=echo 0.5",
            "--set", "metric_name=sharpe",
            "--set", "metric_direction=higher_is_better",
            "--set", "domain=quant",
            *extra,
        ])

    def test_quant_single_metric_comp_rejected(self, project_root, monkeypatch, capsys):
        rc = self._create_quant(project_root, monkeypatch, "Single-metric quant", [])
        assert rc == 1
        out = capsys.readouterr().out
        assert "metric bundle" in out
        assert "rejected" in out
        assert "evaluation_horizon" in out

    def test_quant_bundle_with_fixed_horizon_accepted(
        self, project_root, monkeypatch, capsys
    ):
        rc = self._create_quant(project_root, monkeypatch, "Bundled quant", [
            "--set", 'metric_bundle=["sharpe", "max_drawdown", "total_trades"]',
            "--set", "evaluation_horizon=2019-2024 walk-forward",
        ])
        assert rc == 0
        comps = [
            a for a in art_lib.discover_artifacts(project_root)
            if art_lib.get_prefix_from_id(a.id) == "COMP" and a.title == "Bundled quant"
        ]
        assert len(comps) == 1
        fm = comps[0].frontmatter
        assert fm["metric_bundle"] == ["sharpe", "max_drawdown", "total_trades"]
        assert fm["evaluation_horizon"] == "2019-2024 walk-forward"

    def test_quant_single_name_bundle_rejected(self, project_root, monkeypatch, capsys):
        rc = self._create_quant(project_root, monkeypatch, "One-metric bundle", [
            "--set", 'metric_bundle=["sharpe"]',
            "--set", "evaluation_horizon=2019-2024",
        ])
        assert rc == 1
        assert "rejected" in capsys.readouterr().out

    def test_quant_bundle_without_horizon_rejected(self, project_root, monkeypatch, capsys):
        rc = self._create_quant(project_root, monkeypatch, "No-horizon bundle", [
            "--set", 'metric_bundle=["sharpe", "max_drawdown"]',
        ])
        assert rc == 1
        assert "evaluation_horizon" in capsys.readouterr().out

    def test_non_quant_single_metric_comp_still_allowed(
        self, project_root, monkeypatch
    ):
        monkeypatch.chdir(project_root)
        from specflow import cli
        rc = cli.main([
            "create", "--type", "competition", "--title", "Tabular comp",
            "--status", "active", "--skip-dedup-check", "--body", "b",
            "--set", "verify_command=echo 0.5",
            "--set", "metric_name=roc_auc",
            "--set", "metric_direction=higher_is_better",
            "--set", "domain=tabular_ml",
        ])
        assert rc == 0

    def test_plan_reports_quant_bundle_requirement(
        self, project_root, monkeypatch, capsys
    ):
        rc = self._create_quant(project_root, monkeypatch, "Planned quant", [
            "--set", 'metric_bundle=["sharpe", "max_drawdown", "total_trades"]',
            "--set", "evaluation_horizon=2019-2024 walk-forward",
        ])
        assert rc == 0
        comps = [
            a for a in art_lib.discover_artifacts(project_root)
            if art_lib.get_prefix_from_id(a.id) == "COMP" and a.title == "Planned quant"
        ]
        comp_id = comps[0].id
        assert autoresearch_cmd.run(
            project_root, {"autoresearch_subcommand": "plan", "competition": comp_id}
        ) == 0
        out = capsys.readouterr().out
        assert "Metric bundle: sharpe, max_drawdown, total_trades" in out
        assert "2019-2024 walk-forward" in out

    def test_plan_rejects_single_metric_quant_comp(self, project_root, capsys):
        # A quant COMP that predates the setup gate still gets the rejection
        # surfaced on the setup checklist.
        _write_artifact(
            project_root, "COMP-011", "competition", "Legacy quant",
            status="active",
            extra_fm={
                "created": "2026-05-15", "verify_command": "echo 0.5",
                "metric_name": "sharpe", "metric_direction": "higher_is_better",
                "domain": "quant",
            },
        )
        assert autoresearch_cmd.run(
            project_root, {"autoresearch_subcommand": "plan", "competition": "COMP-011"}
        ) == 0
        out = capsys.readouterr().out
        assert "single-metric COMP is rejected" in out
        assert "evaluation_horizon" in out


# ── STORY-694 (REQ-043, REQ-056): no fabricated metrics, no count-based ─────
# kill drafts, null-safe sorting; STORY-693 AC2: frontier --competition.


def _expt_file_text(root: Path, expt_id: str) -> str:
    return art_lib.resolve_link_target(root, expt_id).read_text(encoding="utf-8")


class TestLogNeverFabricatesMetric:
    """AC1: `log` refuses a metric-less keep and records null — never 0.0 —
    for crashed, discarded and no_op runs logged without a metric."""

    def _log(self, root: Path, *extra: str) -> int:
        from specflow import cli
        return cli.main([
            "autoresearch", "log", "--loop", "LOOP-001",
            "--change-category", "features", "--summary", "s", *extra,
        ])

    def test_kept_without_metric_value_is_refused(
        self, project_root, monkeypatch, capsys
    ):
        _make_loop(project_root, "LOOP-001", "COMP-001", status="running",
                   extra={"iteration_count": 0, "kept_count": 0})
        monkeypatch.chdir(project_root)
        assert self._log(project_root, "--status", "kept") == 1
        out = capsys.readouterr().out
        assert "--metric-value" in out
        assert "kept" in out
        expts = [a for a in art_lib.discover_artifacts(project_root)
                 if art_lib.get_prefix_from_id(a.id) == "EXPT"]
        assert expts == []  # nothing created
        lf = _parse(project_root, "LOOP-001").frontmatter
        assert lf["iteration_count"] == 0 and lf["kept_count"] == 0

    def test_kept_with_non_finite_metric_is_refused(
        self, project_root, monkeypatch, capsys
    ):
        _make_loop(project_root, "LOOP-001", "COMP-001", status="running")
        monkeypatch.chdir(project_root)
        assert self._log(project_root, "--status", "kept",
                         "--metric-value", "nan") == 1
        assert "--metric-value" in capsys.readouterr().out

    @pytest.mark.parametrize("status", ["crashed", "discarded", "no_op"])
    def test_metricless_non_keep_writes_yaml_null(
        self, project_root, monkeypatch, capsys, status
    ):
        _make_loop(project_root, "LOOP-001", "COMP-001", status="running")
        monkeypatch.chdir(project_root)
        assert self._log(project_root, "--status", status) == 0
        text = _expt_file_text(project_root, "EXPT-001")
        assert "metric_value: null" in text
        fm = _parse(project_root, "EXPT-001").frontmatter
        # The required key is present (schema-valid) but carries no score.
        assert "metric_value" in fm and fm["metric_value"] is None
        from specflow.lib import lint as lint_lib
        schema = yaml.safe_load(
            (project_root / ".specflow" / "schema" / "experiment.yaml")
            .read_text(encoding="utf-8")
        )
        issues = lint_lib.validate_artifact_schema(_parse(project_root, "EXPT-001"), schema)
        assert not any("metric_value" in i["message"] for i in issues)

    def test_non_keep_with_metric_keeps_the_measured_value(
        self, project_root, monkeypatch, capsys
    ):
        _make_loop(project_root, "LOOP-001", "COMP-001", status="running")
        monkeypatch.chdir(project_root)
        assert self._log(project_root, "--status", "discarded",
                         "--metric-value", "0.41") == 0
        assert _parse(project_root, "EXPT-001").frontmatter["metric_value"] == 0.41


class TestCrashedExptsExcludedFromIntegrity(_IntegrityStatusMixin):
    """AC2: crashed EXPTs never feed jump flags or guard-regression warnings —
    neither a new null-metric crash nor a legacy crash carrying a fabricated
    0.0."""

    @pytest.mark.parametrize("crash_metric", [None, 0.0])
    def test_crash_between_keeps_raises_no_jump(
        self, git_project_root, capsys, crash_metric
    ):
        self._setup(git_project_root)
        _make_expt(git_project_root, "EXPT-001", "LOOP-001", "kept", 0.50)
        _make_expt(git_project_root, "EXPT-002", "LOOP-001", "crashed",
                   crash_metric, extra={"failure_analysis": "OOM"})
        _make_expt(git_project_root, "EXPT-003", "LOOP-001", "kept", 0.51)
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "jump: " not in out
        assert "mechanism explanation required" not in out

    @pytest.mark.parametrize("crash_metric", [None, 0.0])
    def test_crash_never_manufactures_a_guarded_gain(
        self, git_project_root, capsys, crash_metric
    ):
        self._setup(git_project_root)
        _make_expt(git_project_root, "EXPT-001", "LOOP-001", "kept", 0.50,
                   extra={"guard_metrics": {"max_drawdown": 0.10}})
        _make_expt(git_project_root, "EXPT-002", "LOOP-001", "crashed",
                   crash_metric, extra={"failure_analysis": "OOM"})
        # No primary gain over EXPT-001 — the guard move must not warn.
        _make_expt(git_project_root, "EXPT-003", "LOOP-001", "kept", 0.50,
                   extra={"guard_metrics": {"max_drawdown": 0.15}})
        assert self._status(git_project_root) == 0
        assert "guard-regression warning" not in capsys.readouterr().out

    def test_crashed_guard_is_never_a_regression_baseline(
        self, git_project_root, capsys
    ):
        # STORY-694 AC2 fix pass: the guard baseline is the latest MEASURED
        # prior; a crashed run's guard reading must not mask the regression.
        self._setup(git_project_root)
        _make_expt(git_project_root, "EXPT-001", "LOOP-001", "kept", 0.50,
                   extra={"guard_metrics": {"max_drawdown": 0.10}})
        _make_expt(git_project_root, "EXPT-002", "LOOP-001", "crashed", None,
                   extra={"failure_analysis": "OOM",
                          "guard_metrics": {"max_drawdown": 0.30}})
        _make_expt(git_project_root, "EXPT-003", "LOOP-001", "kept", 0.51,
                   extra={"guard_metrics": {"max_drawdown": 0.30}})
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "guard-regression warning: EXPT-003" in out

    def test_crashed_guard_is_never_the_latest_value(
        self, git_project_root, capsys
    ):
        self._setup(git_project_root)
        _make_expt(git_project_root, "EXPT-001", "LOOP-001", "kept", 0.50,
                   extra={"guard_metrics": {"max_drawdown": 0.10}})
        _make_expt(git_project_root, "EXPT-002", "LOOP-001", "crashed", None,
                   extra={"failure_analysis": "OOM",
                          "guard_metrics": {"max_drawdown": 0.90}})
        assert self._status(git_project_root) == 0
        out = capsys.readouterr().out
        assert "latest " in out and "EXPT-001" in out
        assert "0.9 " not in out and "EXPT-002" not in out.split("offline fallback")[-1]

    def test_measured_expts_excludes_crashed_and_null(self, project_root):
        _make_loop(project_root, "LOOP-001", "COMP-001", status="running")
        _make_expt(project_root, "EXPT-001", "LOOP-001", "kept", 0.5)
        _make_expt(project_root, "EXPT-002", "LOOP-001", "crashed", 0.0)
        _make_expt(project_root, "EXPT-003", "LOOP-001", "discarded", None)
        _make_expt(project_root, "EXPT-004", "LOOP-001", "no_op", 0.3)
        expts = [_parse(project_root, f"EXPT-00{i}") for i in range(1, 5)]
        measured = autoresearch_cmd._measured_expts(expts)
        assert [e.id for e in measured] == ["EXPT-001"]


class TestSuggestFindsNeutralAccounting:
    """AC3 (REQ-043): suggest-finds drafts outcome accounting from
    hypothesis_outcome and failure_analysis — confidence defaults low and no
    avoid/exploit directive is derived from counts."""

    def _seed(self, root: Path) -> None:
        _make_loop(root, "LOOP-001", "COMP-001", status="completed")
        _make_expt(root, "EXPT-001", "LOOP-001", "kept", 0.60,
                   extra={"hypothesis_outcome": "supported"})
        _make_expt(root, "EXPT-002", "LOOP-001", "kept", 0.62,
                   extra={"hypothesis_outcome": "supported"})
        _make_expt(root, "EXPT-003", "LOOP-001", "discarded", 0.40,
                   category="params",
                   extra={"hypothesis_outcome": "not_supported",
                          "failure_analysis": "lr above 1e-2 diverges"})
        _make_expt(root, "EXPT-004", "LOOP-001", "crashed", None,
                   category="params",
                   extra={"hypothesis_outcome": "invalid",
                          "failure_analysis": "harness OOM at fold 3"})
        _make_expt(root, "EXPT-005", "LOOP-001", "discarded", 0.41,
                   category="params")
        _make_expt(root, "EXPT-006", "LOOP-001", "discarded", 0.42,
                   category="params")

    def _suggest(self, root: Path, **extra) -> int:
        args = {"autoresearch_subcommand": "suggest-finds", "loop": "LOOP-001"}
        args.update(extra)
        return autoresearch_cmd.run(root, args)

    def test_draft_has_no_count_based_directive(self, project_root, capsys):
        self._seed(project_root)
        assert self._suggest(project_root) == 0
        out = capsys.readouterr().out
        lowered = out.lower()
        assert "avoid" not in lowered
        assert "exploit" not in lowered
        assert "explore:" not in lowered
        assert "radically different" not in lowered

    def test_draft_draws_from_outcomes_and_failure_analysis(
        self, project_root, capsys
    ):
        self._seed(project_root)
        assert self._suggest(project_root) == 0
        out = capsys.readouterr().out
        assert "supported=2" in out
        assert "not_supported=1" in out
        assert "invalid=1" in out
        assert "unrecorded=2" in out
        assert "lr above 1e-2 diverges" in out
        assert "harness OOM at fold 3" in out
        # Unrecorded outcomes are named so the investigator can record them.
        assert "EXPT-005" in out and "EXPT-006" in out

    def test_confidence_defaults_low_regardless_of_count(
        self, project_root, capsys
    ):
        # Six EXPTs used to bump confidence to medium by count alone.
        self._seed(project_root)
        assert self._suggest(project_root, write=True) == 0
        find = _parse(project_root, "FIND-001")
        assert find.frontmatter["confidence"] == "low"
        for field in ("what_worked", "what_failed", "next_steps"):
            text = str(find.frontmatter.get(field) or "").lower()
            assert "avoid" not in text and "exploit" not in text


class TestNullSafeMetricSorting:
    """AC4: review, leaderboard (flat + grouped) and suggest-finds sort kept
    EXPTs through the numeric helper — a null or non-numeric metric never
    crashes and always sorts last, in either metric direction."""

    def _seed(self, root: Path) -> None:
        _make_loop(root, "LOOP-001", "COMP-001", status="completed")
        _make_expt(root, "EXPT-001", "LOOP-001", "kept", None,
                   extra={"model_origin": "gbm"})
        _make_expt(root, "EXPT-002", "LOOP-001", "kept", 0.70,
                   extra={"model_origin": "gbm"})
        _make_expt(root, "EXPT-003", "LOOP-001", "kept", "n/a",
                   extra={"model_origin": "gbm"})
        _make_expt(root, "EXPT-004", "LOOP-001", "kept", 0.80,
                   extra={"model_origin": "gbm"})

    def _order(self, out: str) -> list[str]:
        # Titles repeat the ID ("Experiment EXPT-002") — keep first sighting.
        return list(dict.fromkeys(re.findall(r"EXPT-00\d", out)))

    @pytest.mark.parametrize("direction", ["higher_is_better", "lower_is_better"])
    def test_review_sorts_null_last(self, project_root, capsys, direction):
        art_lib.update_artifact(project_root, "COMP-001", metric_direction=direction)
        self._seed(project_root)
        assert autoresearch_cmd.run(project_root, {
            "autoresearch_subcommand": "review", "competition": "COMP-001",
            "top": 5,
        }) == 0
        out = capsys.readouterr().out
        top = out.split("Top 5 Kept Experiments:")[1]
        order = self._order(top)
        measured = ["EXPT-004", "EXPT-002"]
        if direction == "lower_is_better":
            measured.reverse()
        assert order[:2] == measured
        assert set(order[2:4]) == {"EXPT-001", "EXPT-003"}

    @pytest.mark.parametrize("group_by", [None, "model_origin"])
    @pytest.mark.parametrize("direction", ["higher_is_better", "lower_is_better"])
    def test_leaderboard_sorts_null_last(
        self, project_root, capsys, direction, group_by
    ):
        art_lib.update_artifact(project_root, "COMP-001", metric_direction=direction)
        self._seed(project_root)
        args = {"autoresearch_subcommand": "leaderboard",
                "competition": "COMP-001", "top": 10}
        if group_by:
            args["group_by"] = group_by
        assert autoresearch_cmd.run(project_root, args) == 0
        order = self._order(capsys.readouterr().out)
        measured = ["EXPT-004", "EXPT-002"]
        if direction == "lower_is_better":
            measured.reverse()
        assert order[:2] == measured
        assert set(order[2:4]) == {"EXPT-001", "EXPT-003"}

    @pytest.mark.parametrize("direction", ["higher_is_better", "lower_is_better"])
    def test_suggest_finds_best_ignores_null(self, project_root, capsys, direction):
        art_lib.update_artifact(project_root, "COMP-001", metric_direction=direction)
        self._seed(project_root)
        assert autoresearch_cmd.run(project_root, {
            "autoresearch_subcommand": "suggest-finds", "loop": "LOOP-001",
        }) == 0
        out = capsys.readouterr().out
        best = "0.8" if direction == "higher_is_better" else "0.7"
        assert f"best={best}" in out


class TestFrontierCompetitionAlias:
    """STORY-693 AC2: `frontier --competition` is an alias of `--comp`."""

    def test_competition_alias_parses_and_resolves(
        self, project_root, monkeypatch, capsys
    ):
        from specflow import cli
        _make_loop(project_root, "LOOP-001", "COMP-001", status="running")
        _make_expt(project_root, "EXPT-001", "LOOP-001", "kept", 0.5)
        monkeypatch.chdir(project_root)
        assert cli.main([
            "autoresearch", "frontier", "--competition", "COMP-001", "--json",
        ]) == 0
        via_alias = json.loads(capsys.readouterr().out)
        assert cli.main([
            "autoresearch", "frontier", "--comp", "COMP-001", "--json",
        ]) == 0
        assert json.loads(capsys.readouterr().out) == via_alias
