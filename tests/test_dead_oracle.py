"""STORY-699 / REQ-058 AC2 — dead-oracle accounting finding.

A ``verify_command`` whose tokens name a repository path that does not exist
can never verify anything: the recorded run either errors or (worse, for a
pytest invocation over a directory) passes over nothing. ``artifact-lint``'s
dedicated ``dead-oracle`` check surfaces that as an ACCOUNTING warning:

- a token that looks like a repo path (``tests/test_x.py``, ``scripts/e.sh``,
  a pytest node id ``tests/test_x.py::TestA::test_b``) and does not exist →
  one warning naming the artifact and the token;
- flags, placeholders (``{strategy}``), absolute paths, quoted expressions,
  URLs and bare words are never treated as paths (no cry-wolf);
- warning-only with no strict toggle, and project-audit NEVER escalates it to
  exit 2 (it is a dedicated check, the role-target isolation pattern); full
  artifact-lint runs never escalate it to blocking either (DEF-017);
- pytest node ids resolve to their file for the evaluator fingerprint too.

QT-011 was the live instance (it cited the absent ``tests/test_ears_quality.py``);
DEF-005 records that drift and its repoint.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from specflow.commands import artifact_lint as lint_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import evaluator_fingerprint as ef

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _restore_type_registry():
    dirs = dict(art_lib.TYPE_TO_DIR)
    prefixes = dict(art_lib.TYPE_TO_PREFIX)
    reverse = dict(art_lib.PREFIX_TO_TYPE)
    aliases = dict(art_lib.TYPE_ALIASES)
    yield
    for live, snap in ((art_lib.TYPE_TO_DIR, dirs), (art_lib.TYPE_TO_PREFIX, prefixes),
                       (art_lib.PREFIX_TO_TYPE, reverse), (art_lib.TYPE_ALIASES, aliases)):
        live.clear()
        live.update(snap)


_TYPES = [
    ("requirement", "REQ", "specs/requirements"),
    ("unit-test", "UT", "specs/unit-tests"),
    ("qualification-test", "QT", "specs/qualification-tests"),
    ("story", "STORY", "work/stories"),
]
_FLOW = {"draft": [], "approved": ["draft"], "implemented": ["approved"],
         "verified": ["implemented"], "deprecated": ["draft", "approved", "implemented"]}


def _project(tmp: Path) -> Path:
    root = tmp / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    for art_type, prefix, rel in _TYPES:
        schema = {
            "type": art_type, "prefix": prefix, "directory": f"_specflow/{rel}",
            "allowed_status": dict(_FLOW),
            "allowed_link_roles": ["verified_by", "implements", "derives_from"],
            "optional_fields": ["verify_command", "verify_exit_code"],
        }
        (schema_dir / f"{art_type}.yaml").write_text(yaml.dump(schema), encoding="utf-8")
    config = {"project": {"name": "do-test", "created": "2026-01-01"},
              "artifact_types": [t for t, _, _ in _TYPES], "active_packs": []}
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "idle", "history": []}), encoding="utf-8")
    tests_dir = root / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_real.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "scripts" / "eval.sh").write_text("echo ok\n", encoding="utf-8")
    return root


def _mk(root: Path, art_type: str, art_id: str, *, status: str = "implemented",
        verify_command: str | None = None, links: list | None = None,
        body: str = "Body.") -> None:
    rel = {t: r for t, _, r in _TYPES}[art_type]
    path = root / "_specflow" / rel / f"{art_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = {"id": art_id, "title": art_id, "type": art_type, "status": status,
          "tags": [], "suspect": False, "links": links or [], "created": "2026-01-01"}
    if verify_command is not None:
        fm["verify_command"] = verify_command
    path.write_text(f"---\n{yaml.dump(fm, sort_keys=False)}---\n\n{body}\n", encoding="utf-8")


def _check(root: Path) -> dict:
    return lint_cmd._run_check(art_lib.discover_artifacts(root), root, "dead-oracle")


# ── path-token resolution (lib) ───────────────────────────────────


class TestPathTokens:
    def test_missing_file_is_reported(self, tmp_path):
        root = _project(tmp_path)
        assert ef.missing_repo_paths(root, "uv run pytest tests/test_gone.py -q") == [
            "tests/test_gone.py"]

    def test_existing_file_and_node_id_are_fine(self, tmp_path):
        root = _project(tmp_path)
        cmd = "uv run pytest tests/test_real.py::test_a tests/test_real.py -q"
        assert ef.missing_repo_paths(root, cmd) == []

    def test_node_id_of_missing_file_reports_the_file(self, tmp_path):
        root = _project(tmp_path)
        cmd = "uv run pytest tests/test_gone.py::TestX::test_y[p-1] -q"
        assert ef.missing_repo_paths(root, cmd) == ["tests/test_gone.py"]

    @pytest.mark.parametrize("cmd", [
        "uv run pytest -q",
        "uv run pytest -k 'not slow and a/b' -q",
        "python -c \"import sys; print('x/y')\"",
        "bash scripts/eval.sh {strategy}",
        "cat /etc/hosts",
        "curl https://example.com/a/b.py",
        "uv run pytest tests/ -q",
        "uv run pytest --cov=src/gone tests/test_real.py",
        "make test > out/log.txt 2>&1",
        "echo $HOME/x.py",
        "uv run python -m specflow.cli artifact-lint",
        "node dist/app.js",  # top-level dir absent: not recognisably a repo path
    ])
    def test_non_paths_never_cry_wolf(self, tmp_path, cmd):
        root = _project(tmp_path)
        assert ef.missing_repo_paths(root, cmd) == []

    def test_bare_script_name_with_source_suffix_is_a_path(self, tmp_path):
        root = _project(tmp_path)
        assert ef.missing_repo_paths(root, "python eval_gone.py") == ["eval_gone.py"]

    def test_duplicates_collapse(self, tmp_path):
        root = _project(tmp_path)
        cmd = "pytest tests/test_gone.py::a tests/test_gone.py::b"
        assert ef.missing_repo_paths(root, cmd) == ["tests/test_gone.py"]


class TestEvaluatorFingerprintNodeIds:
    def test_node_id_resolves_to_its_file(self, tmp_path):
        root = _project(tmp_path)
        paths = ef.evaluation_script_paths(root, "uv run pytest tests/test_real.py::test_a -q")
        assert paths == ["tests/test_real.py"]

    def test_node_id_fingerprint_tracks_file_content(self, tmp_path):
        root = _project(tmp_path)
        cmd = "uv run pytest tests/test_real.py::test_a -q"
        before = ef.compute_evaluator_fingerprint(root, cmd)
        (root / "tests" / "test_real.py").write_text(
            "def test_a():\n    assert 1\n", encoding="utf-8")
        assert ef.compute_evaluator_fingerprint(root, cmd) != before


# ── the artifact-lint check ───────────────────────────────────────


class TestDeadOracleCheck:
    def test_registered(self):
        assert "dead-oracle" in lint_cmd.CHECK_NAMES

    def test_dead_oracle_warns(self, tmp_path):
        root = _project(tmp_path)
        _mk(root, "qualification-test", "QT-011",
            verify_command="uv run pytest tests/test_ears_quality.py -q")
        result = _check(root)
        assert result["warning_count"] == 1
        assert result["blocking_count"] == 0
        assert "QT-011" in result["detail"]
        assert "tests/test_ears_quality.py" in result["detail"]

    def test_live_oracle_is_clean(self, tmp_path):
        root = _project(tmp_path)
        _mk(root, "unit-test", "UT-001",
            verify_command="uv run pytest tests/test_real.py::test_a -q")
        _mk(root, "story", "STORY-001", verify_command="bash scripts/eval.sh")
        result = _check(root)
        assert result["warning_count"] == 0
        assert result["blocking_count"] == 0

    def test_no_contracts_is_quiet(self, tmp_path):
        root = _project(tmp_path)
        _mk(root, "unit-test", "UT-001")
        result = _check(root)
        assert result["warning_count"] == 0

    def test_deprecated_artifacts_are_skipped(self, tmp_path):
        root = _project(tmp_path)
        _mk(root, "unit-test", "UT-001", status="deprecated",
            verify_command="uv run pytest tests/test_gone.py -q")
        assert _check(root)["warning_count"] == 0

    def test_one_warning_per_artifact_path_pair(self, tmp_path):
        root = _project(tmp_path)
        _mk(root, "unit-test", "UT-001",
            verify_command="uv run pytest tests/test_gone.py tests/test_gone2.py -q")
        _mk(root, "unit-test", "UT-002",
            verify_command="uv run pytest tests/test_gone.py -q")
        assert _check(root)["warning_count"] == 3

    def test_project_audit_never_escalates_dead_oracle(self, tmp_path):
        """Accounting, not policing: a dead oracle is a review signal. It lives
        in a dedicated check that project-audit's consistency lens never folds
        in, so the release gate cannot flip red on it."""
        from specflow.commands import project_audit as pa

        root = _project(tmp_path)
        _mk(root, "unit-test", "UT-001",
            verify_command="uv run pytest tests/test_gone.py -q")
        assert _check(root)["warning_count"] == 1
        assert pa.run(root, {"dry_run": True}) == 0

    def test_artifact_lint_exit_stays_zero_on_dead_oracle(self, tmp_path):
        root = _project(tmp_path)
        _mk(root, "unit-test", "UT-001",
            verify_command="uv run pytest tests/test_gone.py -q")
        assert lint_cmd.run(root, {"type": "dead-oracle"}) == 0

    def test_full_lint_runs_never_escalate_dead_oracle(self, tmp_path, capsys):
        """STORY-663 escalation turns a warning seen in 3 consecutive FULL runs
        into a blocker. A dead oracle is accounting, so it is exempt like
        bp-application and fingerprint-drift: full runs keep exiting 0."""
        root = _project(tmp_path)
        # A project clean but for the dead oracle, so any exit 1 is escalation.
        _mk(root, "requirement", "REQ-001", status="draft",
            body="## Acceptance Criteria\n1. The system shall lock the account "
                 "after five failed logins.")
        _mk(root, "qualification-test", "QT-001",
            verify_command="uv run pytest tests/test_gone.py -q",
            links=[{"target": "REQ-001", "role": "verified_by"}])
        codes = []
        for _ in range(4):
            codes.append(lint_cmd.run(root, {}))
            out = capsys.readouterr().out
            assert "[dead-oracle]" not in out, out
        assert codes == [0, 0, 0, 0]


def test_dogfood_repo_has_no_dead_oracle():
    """The live instance (QT-011 citing tests/test_ears_quality.py) is repointed
    and every verify_command in this repo names paths that exist."""
    result = lint_cmd._run_check(art_lib.discover_artifacts(REPO_ROOT), REPO_ROOT,
                                 "dead-oracle")
    assert result["warning_count"] == 0, result["detail"]


def test_qt011_cites_an_existing_test():
    """DEF-012: QT-011 carries a verify_command naming a test file that exists,
    and its body no longer cites the absent tests/test_ears_quality.py."""
    qt = next(a for a in art_lib.discover_artifacts(REPO_ROOT) if a.id == "QT-011")
    cmd = qt.frontmatter.get("verify_command")
    assert cmd, "QT-011 declares no verify_command"
    named = ef.evaluation_script_paths(REPO_ROOT, cmd)
    assert named, cmd
    assert ef.missing_repo_paths(REPO_ROOT, cmd) == []
    assert "tests/test_ears_quality.py" not in qt.body
