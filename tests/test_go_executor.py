"""`specflow go` + ``lib/executor.py`` (STORY-718).

The executor had zero tests although it is on the execute skill path
(``go --dry-run`` is step 2) and its commit path runs ``git add -A``. These
tests cover the pure functions (wave computation, execution-state round-trip,
subagent context assembly), ``auto_commit_wave`` inside a throwaway ``git
init``, and the ``go --dry-run`` invariant that nothing on disk changes.
``execute_story`` is intentionally untested: the AI host does the work.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest
import yaml
from conftest import write_artifact

from specflow import cli
from specflow.commands import init as init_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import executor
from specflow.lib.waves import compute_waves, detect_cycles


def _art(art_id: str, art_type: str, status: str = "approved", body: str = "body",
         links: list[tuple[str, str]] | None = None) -> art_lib.Artifact:
    return art_lib.Artifact(
        path=Path(f"{art_id}.md"),
        frontmatter={"id": art_id, "title": f"Title {art_id}", "type": art_type, "status": status},
        body=body,
        links=[art_lib.Link(target=t, role=r) for t, r in (links or [])],
    )


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
        cwd=str(root), capture_output=True, text=True, check=False,
    )


def _snapshot(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and ".git" not in path.parts:
            out[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


# ── waves ───────────────────────────────────────────────────────────────────

class TestWaves:
    def test_independent_stories_form_one_wave(self):
        result = compute_waves([_art("STORY-001", "story"), _art("STORY-002", "story")])
        assert result["ok"]
        assert result["waves"] == [["STORY-001", "STORY-002"]]

    def test_derives_from_between_stories_orders_waves(self):
        stories = [
            _art("STORY-002", "story", links=[("STORY-001", "derives_from")]),
            _art("STORY-001", "story"),
            _art("STORY-003", "story", links=[("STORY-002", "depends_on")]),
        ]
        result = compute_waves(stories)
        assert result["ok"]
        assert result["waves"] == [["STORY-001"], ["STORY-002"], ["STORY-003"]]

    def test_shared_ddd_is_a_soft_dependency_lower_id_first(self):
        stories = [
            _art("STORY-009", "story", links=[("DDD-001", "specified_by")]),
            _art("STORY-004", "story", links=[("DDD-001", "specified_by")]),
        ]
        result = compute_waves(stories)
        assert result["ok"]
        assert result["waves"] == [["STORY-004"], ["STORY-009"]]

    def test_cycle_is_reported_not_raised(self):
        stories = [
            _art("STORY-001", "story", links=[("STORY-002", "derives_from")]),
            _art("STORY-002", "story", links=[("STORY-001", "derives_from")]),
        ]
        result = compute_waves(stories)
        assert result["ok"] is False
        assert "Circular dependency" in result["error"]
        assert set(result["cycle"]) >= {"STORY-001", "STORY-002"}

    def test_detect_cycles_is_deterministic_and_ignores_external_targets(self):
        graph = {"A": {"B"}, "B": {"C"}, "C": {"A"}, "D": {"ZZZ"}}
        first = detect_cycles(graph)
        assert first is not None and set(first) == {"A", "B", "C"}
        assert detect_cycles(graph) == first
        assert detect_cycles({"A": {"B"}, "B": set(), "C": {"MISSING"}}) is None


# ── execution state ─────────────────────────────────────────────────────────

class TestExecutionState:
    def test_round_trip_preserves_every_field_and_other_state_keys(self, tmp_path: Path):
        (tmp_path / ".specflow").mkdir()
        (tmp_path / ".specflow" / "state.yaml").write_text(
            yaml.dump({"current": "planning", "history": [{"phase": "idle"}]}), encoding="utf-8"
        )
        state = executor.ExecutionState(
            current_wave=2, total_waves=3, completed=["STORY-001"], in_progress=["STORY-002"],
            queued=["STORY-003"], failed=["STORY-004"],
        )
        executor.save_execution_state(tmp_path, state)

        loaded = executor.load_execution_state(tmp_path)
        assert loaded == state

        raw = yaml.safe_load((tmp_path / ".specflow" / "state.yaml").read_text(encoding="utf-8"))
        assert raw["current"] == "executing"
        assert raw["history"] == [{"phase": "idle"}], "unrelated state keys survive a save"
        assert raw["execution"]["wave"] == 2

    def test_load_returns_none_without_state_or_execution_block(self, tmp_path: Path):
        assert executor.load_execution_state(tmp_path) is None
        (tmp_path / ".specflow").mkdir()
        (tmp_path / ".specflow" / "state.yaml").write_text("current: idle\n", encoding="utf-8")
        assert executor.load_execution_state(tmp_path) is None
        (tmp_path / ".specflow" / "state.yaml").write_text(": not yaml [", encoding="utf-8")
        assert executor.load_execution_state(tmp_path) is None


# ── subagent context ────────────────────────────────────────────────────────

class TestSubagentContext:
    def test_includes_linked_ddd_arch_and_agents_md(self, tmp_path: Path):
        (tmp_path / "AGENTS.md").write_text("# Rules\nNo orphan work.\n", encoding="utf-8")
        story = _art("STORY-001", "story", body="Do the thing.",
                     links=[("DDD-001", "specified_by"), ("ARCH-001", "guided_by"),
                            ("REQ-001", "implements")])
        ddd = _art("DDD-001", "detailed-design", body="Design detail.")
        arch = _art("ARCH-001", "architecture", body="Architecture detail.")
        req = _art("REQ-001", "requirement", body="Requirement text.")

        ctx = executor.build_subagent_context(tmp_path, story, [story, ddd, arch, req])

        assert ctx.design_doc is ddd and ctx.arch_doc is arch
        prompt = ctx.to_prompt()
        assert "# Story: Title STORY-001" in prompt and "Do the thing." in prompt
        assert "# Design: Title DDD-001" in prompt and "Design detail." in prompt
        assert "# Architecture: Title ARCH-001" in prompt and "Architecture detail." in prompt
        assert "# Project Rules" in prompt and "No orphan work." in prompt
        assert "Requirement text." not in prompt, "only specified_by/guided_by targets are pulled in"
        assert ctx.total_chars == sum(len(x) for x in (story.body, ddd.body, arch.body, ctx.agents_md))

    def test_unresolvable_links_and_missing_agents_md_are_tolerated(self, tmp_path: Path):
        story = _art("STORY-001", "story", links=[("DDD-404", "specified_by")])
        ctx = executor.build_subagent_context(tmp_path, story, [story])
        assert ctx.design_doc is None and ctx.arch_doc is None and ctx.agents_md == ""
        assert ctx.to_prompt().startswith("# Story: Title STORY-001")

    def test_over_budget_context_trims_rules_but_never_the_story(self, tmp_path: Path):
        (tmp_path / "AGENTS.md").write_text("R" * (executor.MAX_CONTEXT_CHARS * 2), encoding="utf-8")
        story_body = "S" * 1000
        story = _art("STORY-001", "story", body=story_body)
        ctx = executor.build_subagent_context(tmp_path, story, [story])
        assert ctx.story.body == story_body
        assert 0 < len(ctx.agents_md) < executor.MAX_CONTEXT_CHARS


# ── auto-commit ─────────────────────────────────────────────────────────────

class TestAutoCommitWave:
    @pytest.fixture
    def repo(self, tmp_path: Path) -> Path:
        assert _git(tmp_path, "init", "-q").returncode == 0
        (tmp_path / "base.txt").write_text("base\n", encoding="utf-8")
        assert _git(tmp_path, "add", "-A").returncode == 0
        assert _git(tmp_path, "commit", "-q", "-m", "base").returncode == 0
        return tmp_path

    def test_commits_pending_changes_with_wave_message(self, repo: Path, monkeypatch):
        monkeypatch.setenv("GIT_AUTHOR_EMAIL", "t@example.com")
        monkeypatch.setenv("GIT_AUTHOR_NAME", "t")
        monkeypatch.setenv("GIT_COMMITTER_EMAIL", "t@example.com")
        monkeypatch.setenv("GIT_COMMITTER_NAME", "t")
        (repo / "new.py").write_text("x = 1\n", encoding="utf-8")
        (repo / "base.txt").write_text("changed\n", encoding="utf-8")

        assert executor.auto_commit_wave(repo, 1, ["STORY-001", "STORY-002"]) is True

        subject = _git(repo, "log", "-1", "--format=%s").stdout.strip()
        assert subject == "specflow: wave 1 prepared [STORY-001, STORY-002]"
        assert _git(repo, "status", "--porcelain").stdout.strip() == "", "everything was staged"
        files = _git(repo, "show", "--name-only", "--format=", "HEAD").stdout.split()
        assert sorted(files) == ["base.txt", "new.py"]

    def test_returns_false_when_nothing_to_commit(self, repo: Path):
        before = _git(repo, "rev-parse", "HEAD").stdout.strip()
        assert executor.auto_commit_wave(repo, 2, ["STORY-003"]) is False
        assert _git(repo, "rev-parse", "HEAD").stdout.strip() == before

    def test_returns_false_outside_a_git_repository(self, tmp_path: Path):
        (tmp_path / "f.txt").write_text("x", encoding="utf-8")
        assert executor.auto_commit_wave(tmp_path, 1, ["STORY-001"]) is False


# ── go --dry-run ────────────────────────────────────────────────────────────

class TestGoDryRun:
    @pytest.fixture
    def project(self, tmp_path: Path, monkeypatch) -> Path:
        root = tmp_path / "p"
        root.mkdir()
        assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
        write_artifact(root, "STORY-001", "story", "First", status="approved")
        write_artifact(root, "STORY-002", "story", "Second", status="approved",
                       links=[{"target": "STORY-001", "role": "derives_from"}])
        write_artifact(root, "STORY-003", "story", "Still a draft", status="draft")
        monkeypatch.chdir(root)
        return root

    def test_dry_run_prints_the_plan_and_changes_nothing(self, project: Path, capsys):
        before = _snapshot(project)
        assert cli.main(["go", "--dry-run"]) == 0
        out = capsys.readouterr().out
        assert "2 wave(s), 2 stories" in out
        assert "Wave 1: STORY-001" in out and "Wave 2: STORY-002" in out
        assert "STORY-003" not in out, "draft stories are not executable"
        assert _snapshot(project) == before, "dry-run must leave the project untouched"
        assert executor.load_execution_state(project) is None

    def test_dry_run_wave_filter_and_bad_wave(self, project: Path, capsys):
        assert cli.main(["go", "--dry-run", "--wave", "2"]) == 0
        out = capsys.readouterr().out
        assert "Wave 1: STORY-002" in out and "STORY-001" not in out
        assert cli.main(["go", "--dry-run", "--wave", "9"]) == 1
        assert "Wave 9 not found" in capsys.readouterr().out

    def test_no_approved_stories_exits_one(self, tmp_path: Path, monkeypatch, capsys):
        root = tmp_path / "empty"
        root.mkdir()
        assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
        monkeypatch.chdir(root)
        assert cli.main(["go", "--dry-run"]) == 1
        assert "No approved stories" in capsys.readouterr().out

    def test_run_execution_dry_run_matches_cli_plan(self, project: Path):
        result = executor.run_execution(project, dry_run=True)
        assert result == {
            "ok": True, "dry_run": True, "total_waves": 2,
            "waves": [{"wave": 1, "stories": ["STORY-001"]}, {"wave": 2, "stories": ["STORY-002"]}],
        }
