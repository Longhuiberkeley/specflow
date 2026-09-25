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
