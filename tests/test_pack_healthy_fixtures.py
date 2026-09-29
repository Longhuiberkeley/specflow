"""STORY-695 AC3: healthy-fixture tests for the documented pack sequences.

Each test drives a pack's documented command sequence through the real CLI in
a temporary project and asserts the deterministic signals a healthy project
must give: zero warnings from `artifact-lint`, a quiet `brief --next`, and (for
autoresearch) a clear `autoresearch status`. A cry-wolf signal on a healthy
fixture is a bug in the signal or in the documented sequence.

Adoption: the worked example in specflow-adopt/SKILL.md, executed verbatim.
Ops: deploy, observe, breach, recover, resolve (specflow-ops/SKILL.md).
Autoresearch: COMP, plan, LOOP setup, start, log (specflow-autoresearch/SKILL.md).
Core: init, discover, plan, execute per the core skills (STORY-695 AC3 core case).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

PACKS_DIR = Path(__file__).parent.parent / "src" / "specflow" / "packs"
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def sf(root: Path, *args: str) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [sys.executable, "-m", "specflow", *args], cwd=str(root),
        capture_output=True, text=True, stdin=subprocess.DEVNULL, check=False,
    )
    proc.stdout = _ANSI.sub("", proc.stdout)
    proc.stderr = _ANSI.sub("", proc.stderr)
    return proc


def git(root: Path, *args: str) -> None:
    proc = subprocess.run(
        ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
        cwd=str(root), capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr


def commit_all(root: Path, msg: str = "checkpoint") -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "--allow-empty", "-m", msg)


def flagged_lines(text: str) -> list[str]:
    """Lines carrying a warning or failure marker."""
    return [ln for ln in text.splitlines() if "⚠" in ln or "✗" in ln]


def assert_healthy(root: Path, *, allow_brief_lines: int = 1) -> None:
    lint = sf(root, "artifact-lint")
    assert lint.returncode == 0, lint.stdout
    assert flagged_lines(lint.stdout) == [], lint.stdout
    brief = sf(root, "brief", "--next")
    assert brief.returncode == 0, brief.stdout
    assert flagged_lines(brief.stdout) == [], brief.stdout
    lines = [ln for ln in brief.stdout.splitlines() if ln.strip()]
    # One core recommendation line; any pack/outcome note would be a second line.
    assert len(lines) <= allow_brief_lines, brief.stdout


def new_project(tmp_path: Path, preset: str, name: str) -> Path:
    root = tmp_path / name
    root.mkdir()
    git(root, "init", "-q")
    proc = sf(root, "init", "--preset", preset, "--platform", "claude-code", "--no-ci")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return root


def run_adopt_worked_example(root: Path) -> list[subprocess.CompletedProcess]:
    """Run the fenced worked example from specflow-adopt/SKILL.md through bash
    with a `specflow` shell function, one top-level command at a time."""
    skill = (PACKS_DIR / "adoption" / "skills" / "specflow-adopt" / "SKILL.md").read_text(encoding="utf-8")
    (block,) = [b for b in re.findall(r"```(?:bash|sh)?\n(.*?)```", skill, flags=re.S) if "--type architecture" in b]
    shim = f'specflow() {{ "{sys.executable}" -m specflow "$@"; }}\n'
    out = []
    for part in (p for p in re.split(r"(?m)^(?=specflow )", block) if p.strip()):
        out.append(subprocess.run(["bash", "-c", shim + part], cwd=str(root), capture_output=True,
                                  text=True, stdin=subprocess.DEVNULL, check=False))
    return out


# ── adoption ────────────────────────────────────────────────────────────────

def test_adoption_sequence_is_healthy(tmp_path: Path):
    root = new_project(tmp_path, "adoption", "adopt")
    (root / "src" / "payments").mkdir(parents=True)
    (root / "src" / "payments" / "capture.py").write_text("def capture():\n    return 1\n")
    (root / "tests").mkdir()
    (root / "tests" / "test_payments.py").write_text("def test_capture():\n    assert True\n")

    assert all(p.returncode == 0 for p in run_adopt_worked_example(root))
    # Documented Phase 6 step, taken after a real challenge lens ran.
    assert sf(root, "update", "ARCH-001", "--thinking-techniques", "premortem").returncode == 0

    assert_healthy(root)
    status = sf(root, "adopt", "status")
    assert status.returncode == 0, status.stdout
    assert flagged_lines(status.stdout) == [], status.stdout
    # The project-wide sweep is a final-pass tool; with everything linked it is a no-op.
    orphan = sf(root, "detect", "orphan-code")
    assert orphan.returncode == 0
    assert "--adopt" not in orphan.stdout


# ── ops ─────────────────────────────────────────────────────────────────────

def test_ops_sequence_is_healthy(tmp_path: Path):
    root = new_project(tmp_path, "ops", "ops")
    steps = [
        ("create", "--type", "run", "--title", "svc - prod", "--status", "deployed",
         "--set", "environment=prod", "--set", "deployed_ref=v1.0.0",
         "--set", "deployed_at=2026-09-01", "--skip-dedup-check"),
        ("update", "RUN-001", "--status", "live"),
        ("create", "--type", "monitor", "--title", "RUN-001 obs 2026-09-02", "--status", "logged",
         "--set", "run=RUN-001", "--set", "observed_at=2026-09-02",
         "--set", "summary=p99 latency within threshold",
         "--set", 'metrics={"p99_ms": 120}', "--set", "health=ok",
         "--links", "RUN-001:belongs_to", "--skip-dedup-check"),
    ]
    for step in steps:
        proc = sf(root, *step)
        assert proc.returncode == 0, f"{step[:3]} -> {proc.stdout}"
    assert_healthy(root)

    # Pause / resume / retire (Flow C) stay quiet too.
    assert sf(root, "update", "RUN-001", "--status", "paused").returncode == 0
    assert sf(root, "update", "RUN-001", "--status", "live").returncode == 0
    assert sf(root, "update", "RUN-001", "--status", "retired", "--set", "retired_at=2026-09-10").returncode == 0
    assert_healthy(root)


# ── autoresearch ────────────────────────────────────────────────────────────

def test_autoresearch_sequence_is_healthy(tmp_path: Path):
    root = new_project(tmp_path, "autoresearch", "ar")
    (root / "verify.py").write_text("print(0.80)\n")
    commit_all(root, "init")

    def run(*args: str, ok: int = 0) -> subprocess.CompletedProcess:
        proc = sf(root, *args)
        assert proc.returncode == ok, f"{args[:4]} -> rc={proc.returncode}\n{proc.stdout}{proc.stderr}"
        return proc

    run("create", "--type", "competition", "--title", "Screener", "--status", "active",
        "--set", "verify_command=python verify.py", "--set", "metric_name=AUC",
        "--set", "metric_direction=higher_is_better", "--set", 'goals=["reach AUC 0.85"]')
    # Documented noise probe: three verify runs recorded on the COMP.
    run("update", "COMP-001", "--set", 'noise_characterization={"samples":[0.81,0.82,0.80]}')
    # Step 3 leads with plan.
    run("autoresearch", "plan", "--competition", "COMP-001", "--mode", "explore", "--budget", "5")
    run("update", "LOOP-001", "--set", "goal=Pursue goal 1: reach AUC 0.85",
        "--set", 'active_research_questions=["Do tenure features lift AUC?"]',
        "--set", 'research_agenda=[{"direction": "feature mix", "status": "unexplored", '
                 '"expected_impact": "high", "rationale": "tenure is untested"}]',
        "--set", "eda_completed=true")
    run("autoresearch", "plan", "--competition", "COMP-001", "--loop", "LOOP-001", "--create", "--start")
    commit_all(root, "setup")

    run("autoresearch", "log", "--loop", "LOOP-001", "--status", "kept", "--metric-value", "0.83",
        "--change-category", "features", "--summary", "add tenure features",
        "--set", "hypothesis=tenure lifts AUC by at least 0.01",
        "--set", "hypothesis_outcome=supported", "--set", "iteration=1")
    commit_all(root, "experiment(features): add tenure")

    status = sf(root, "autoresearch", "status")
    assert status.returncode == 0, status.stdout
    assert flagged_lines(status.stdout) == [], status.stdout
    frontier = sf(root, "autoresearch", "frontier", "--competition", "COMP-001")
    assert frontier.returncode == 0, frontier.stdout
    assert_healthy(root, allow_brief_lines=2)


# ── core lifecycle ──────────────────────────────────────────────────────────

_AC = (
    "## Acceptance Criteria\n"
    "1. Given a valid token, when the user calls login, then a session is returned.\n"
    "2. Given an expired token, when the user calls login, then error 401 is returned.\n"
    "3. Given a missing token, when the user calls login, then error 400 is returned.\n"
)

def run_core_lifecycle(tmp_path: Path) -> Path:
    """init → discover (REQ, approved by the user) → plan (ARCH + STORY,
    approved) → execute (implemented + output_files + cascade + V-model tests),
    following the core skills' documented commands."""
    root = tmp_path / "core"
    root.mkdir()
    git(root, "init", "-q")
    init = sf(root, "init", "--platform", "claude-code", "--no-ci")
    assert init.returncode == 0, init.stdout + init.stderr

    def run(*args: str) -> subprocess.CompletedProcess:
        proc = sf(root, *args)
        assert proc.returncode == 0, f"{args[:3]} -> rc={proc.returncode}\n{proc.stdout}{proc.stderr}"
        return proc

    # Discover: REQ with G/W/T criteria, challenged, then the user's approval.
    run("create", "--type", "requirement", "--title", "Users log in with a token",
        "--priority", "high", "--nfr-category", "functional",
        "--body", "The system SHALL authenticate users by token.\n\n" + _AC, "--skip-dedup-check")
    run("update", "REQ-001", "--thinking-techniques", "premortem")
    run("update", "REQ-001", "--status", "approved")
    # Plan: ARCH derived from the REQ, STORY implementing it (SPIDR-tagged),
    # stress-tested, approved by the user, phase recorded.
    run("create", "--type", "architecture", "--title", "Auth service",
        "--links", '[{"target":"REQ-001","role":"derives_from"}]',
        "--body", "## Responsibility\nToken authentication.\n\n## Interface\nlogin(token) -> session\n\n" + _AC,
        "--skip-dedup-check")
    run("create", "--type", "story", "--title", "Log in with a token", "--tags", "spidr-path",
        "--links", '[{"target":"REQ-001","role":"implements"},{"target":"ARCH-001","role":"guided_by"}]',
        "--body", "As a user I want to log in with a token.\n\n" + _AC, "--skip-dedup-check")
    run("update", "ARCH-001", "--thinking-techniques", "premortem,dependency_shock")
    run("update", "ARCH-001", "--status", "approved")
    run("update", "STORY-001", "--status", "approved")
    run("phase-set", "planning", "--reason", "ARCH-001 and STORY-001 approved")
    # Execute: code + test, the step-5 status sequence, then V-model pairs.
    run("phase-set", "executing", "--reason", "wave 1: STORY-001")
    (root / "src").mkdir()
    (root / "src" / "auth.py").write_text("def login(token):\n    return token\n")
    (root / "tests").mkdir()
    (root / "tests" / "test_auth.py").write_text("def test_login():\n    assert True\n")
    run("update", "STORY-001", "--thinking-techniques", "worst_case_user,composition")
    run("update", "STORY-001", "--status", "implemented")
    run("update", "STORY-001", "--output-files", "src/auth.py,tests/test_auth.py")
    run("cascade-status", "STORY-001")
    for test_type, spec in (("unit-test", None), ("integration-test", "ARCH-001"),
                            ("qualification-test", "REQ-001")):
        links = [{"target": "STORY-001", "role": "verified_by"}]
        if spec:
            links.append({"target": spec, "role": "verified_by"})
        run("create", "--type", test_type, "--title", f"{test_type} for token login",
            "--links", json.dumps(links),
            "--set", "verify_command=python -m pytest tests/test_auth.py -q",
            "--set", 'output_files=["tests/test_auth.py"]',
            "--body", "## Test Cases\n1. **login returns the token**\n   - Expected: session returned\n",
            "--skip-dedup-check")
    commit_all(root, "implement STORY-001")
    return root


def test_core_lifecycle_is_healthy(tmp_path: Path):
    root = run_core_lifecycle(tmp_path)
    lint = sf(root, "artifact-lint")
    assert lint.returncode == 0, lint.stdout
    # STORY-695 AC3 / REQ-056 AC7: zero artifact-lint warnings, no filtering.
    assert flagged_lines(lint.stdout) == [], lint.stdout
    brief = sf(root, "brief", "--next")
    assert brief.returncode == 0, brief.stdout
    assert flagged_lines(brief.stdout) == [], brief.stdout
    lines = [ln for ln in brief.stdout.splitlines() if ln.strip()]
    assert len(lines) == 1 and "/specflow-ship" in lines[0], brief.stdout


def test_core_lifecycle_spidr_is_quiet(tmp_path: Path):
    # STORY-695: was a strict xfail while spidr-coverage warned on lean changes.
    assert_healthy(run_core_lifecycle(tmp_path))
