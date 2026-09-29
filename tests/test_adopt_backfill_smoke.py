"""STORY-691: the adoption pack's documented backfill commands run as written.

The ARCH/IT worked example in specflow-adopt/SKILL.md is executed verbatim
(extracted from the fenced block) through the real CLI in a temporary project.
Also pins: --sanctioned on every backfill create, needs-decision preserving
the backfilled tag, retro-link scoping, no --adopt tip inside an adoption run,
and no legacy D-20 references.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PACKS_DIR = Path(__file__).parent.parent / "src" / "specflow" / "packs"
ADOPT_DIR = PACKS_DIR / "adoption" / "skills" / "specflow-adopt"
SKILL = ADOPT_DIR / "SKILL.md"

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def sf(root: Path, *args: str) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [sys.executable, "-m", "specflow", *args],
        cwd=str(root), capture_output=True, text=True, stdin=subprocess.DEVNULL,
        check=False,
    )
    proc.stdout = _ANSI.sub("", proc.stdout)
    proc.stderr = _ANSI.sub("", proc.stderr)
    return proc


def _fenced_blocks(text: str, needle: str) -> list[str]:
    return [b for b in re.findall(r"```(?:bash|sh)?\n(.*?)```", text, flags=re.S) if needle in b]


def run_worked_example(root: Path) -> list[subprocess.CompletedProcess]:
    """Execute the SKILL.md worked example through a real bash with a `specflow`
    shell function, so quoting/heredocs behave exactly as a reader would run them.
    Each `specflow ...` command is run separately so its exit code is visible."""
    (block,) = _fenced_blocks(SKILL.read_text(encoding="utf-8"), "--type architecture")
    shim = f'specflow() {{ "{sys.executable}" -m specflow "$@"; }}\n'
    # Split on lines that start a new top-level `specflow` command.
    parts = re.split(r"(?m)^(?=specflow )", block)
    results = []
    for part in (p for p in parts if p.strip()):
        proc = subprocess.run(
            ["bash", "-c", shim + part], cwd=str(root), capture_output=True, text=True,
            stdin=subprocess.DEVNULL, check=False,
        )
        proc.stdout = _ANSI.sub("", proc.stdout)
        results.append(proc)
    return results


@pytest.fixture(scope="module")
def adoption_template(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("adopt-template")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    (root / "src" / "payments").mkdir(parents=True)
    (root / "src" / "payments" / "capture.py").write_text("def capture():\n    return 1\n")
    (root / "src" / "legacy").mkdir()
    (root / "src" / "legacy" / "old.py").write_text("x = 1\n")
    (root / "tests").mkdir()
    (root / "tests" / "test_payments.py").write_text("def test_capture():\n    assert True\n")
    proc = sf(root, "init", "--preset", "adoption", "--platform", "claude-code", "--no-ci")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return root


@pytest.fixture
def adopt_project(adoption_template: Path, tmp_path: Path) -> Path:
    dest = tmp_path / "proj"
    shutil.copytree(adoption_template, dest)
    return dest


def _warning_lines(lint_out: str) -> list[str]:
    return [ln for ln in lint_out.splitlines() if "⚠" in ln or "✗" in ln]


class TestDocumentedBackfillRuns:
    def test_worked_example_runs_with_zero_lint_warnings(self, adopt_project: Path):
        results = run_worked_example(adopt_project)
        assert len(results) == 2
        for proc in results:
            assert proc.returncode == 0, proc.stdout + proc.stderr
        # The documented "challenge" step (Phase 6): recorded after a real lens.
        proc = sf(adopt_project, "update", "ARCH-001", "--thinking-techniques", "premortem")
        assert proc.returncode == 0, proc.stdout
        lint = sf(adopt_project, "artifact-lint")
        assert lint.returncode == 0, lint.stdout
        assert _warning_lines(lint.stdout) == [], lint.stdout

    def test_every_backfill_create_carries_sanctioned(self):
        text = SKILL.read_text(encoding="utf-8")
        # Every documented `specflow create ... --status <past draft>` chunk
        # (fenced blocks and table rows) must carry --sanctioned.
        chunks = re.split(r"(?=specflow create)", text)[1:]
        checked = 0
        for chunk in chunks:
            head = re.split(r"\n\n|\n```|\|\n", chunk)[0]
            if "--status" in head and "--status draft" not in head:
                checked += 1
                assert "--sanctioned" in head, head
        assert checked >= 2
        for ln in text.splitlines():
            if ln.startswith("|") and "--status" in ln and "create" in ln:
                assert "--sanctioned" in ln, ln

    def test_create_without_sanctioned_is_the_failure_being_fixed(self, adopt_project: Path):
        # Guard: the gate the docs must satisfy really exists.
        proc = sf(adopt_project, "create", "--type", "architecture", "--title", "X",
                  "--status", "implemented", "--tags", "backfilled")
        assert proc.returncode == 1
        assert "--sanctioned" in proc.stdout


class TestNeedsDecisionKeepsBackfilled:
    def test_documented_tags_command_preserves_backfilled_and_is_listable(self, adopt_project: Path):
        assert all(p.returncode == 0 for p in run_worked_example(adopt_project))
        ref = (ADOPT_DIR / "references" / "conflict-resolution-protocol.md").read_text(encoding="utf-8")
        assert "--tags backfilled,needs-decision" in ref
        assert sf(adopt_project, "update", "ARCH-001", "--tags", "backfilled,needs-decision").returncode == 0
        listed = sf(adopt_project, "list", "--tags", "needs-decision")
        assert "ARCH-001" in listed.stdout
        assert "specflow list --tags needs-decision" in SKILL.read_text(encoding="utf-8")
        brief = sf(adopt_project, "brief")
        assert "Adoption" in brief.stdout  # still tracked as adoption


class TestRetroLinkScoping:
    def test_skill_documents_project_wide_final_pass_and_update_output_files(self):
        text = SKILL.read_text(encoding="utf-8")
        assert "project-wide" in text
        assert "final pass" in text.lower() or "final-pass" in text.lower()
        assert "update ARCH-NNN --output-files" in text
        assert "Never use `--adopt`" in text

    def test_update_output_files_is_a_real_flag(self, adopt_project: Path):
        assert all(p.returncode == 0 for p in run_worked_example(adopt_project))
        proc = sf(adopt_project, "update", "ARCH-001", "--output-files",
                  "src/payments/**/*.py,src/legacy/**/*.py")
        assert proc.returncode == 0, proc.stdout


class TestDetectTipInsideAdoptionRun:
    def test_no_adopt_tip_once_backfilled_artifacts_exist(self, adopt_project: Path):
        assert all(p.returncode == 0 for p in run_worked_example(adopt_project))
        proc = sf(adopt_project, "detect", "orphan-code")
        assert "src/legacy/old.py" in proc.stdout  # still an orphan
        assert "--adopt" not in proc.stdout
        assert "update" in proc.stdout and "--output-files" in proc.stdout

    def test_no_adopt_tip_when_adoption_pack_active(self, adopt_project: Path):
        # Pack active but nothing backfilled yet: still no STORY-minting tip.
        proc = sf(adopt_project, "detect", "orphan-code")
        assert "--adopt" not in proc.stdout

    def test_adopt_tip_kept_outside_adoption(self, tmp_path: Path):
        root = tmp_path / "plain"
        root.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        (root / "src").mkdir()
        (root / "src" / "a.py").write_text("x = 1\n")
        assert sf(root, "init", "--platform", "claude-code", "--no-ci").returncode == 0
        proc = sf(root, "detect", "orphan-code")
        assert "--adopt" in proc.stdout


class TestNoLegacyD20:
    def test_no_d20_references_in_adoption_pack(self):
        offenders = [
            str(p.relative_to(PACKS_DIR))
            for p in (PACKS_DIR / "adoption").rglob("*")
            if p.is_file() and p.suffix in {".md", ".yaml"} and "D-20" in p.read_text(encoding="utf-8")
        ]
        assert offenders == []
        assert "DEC-057" in SKILL.read_text(encoding="utf-8")
