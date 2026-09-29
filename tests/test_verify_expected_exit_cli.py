"""STORY-699 integration — record a real verify run via the CLI, then read it.

End-to-end over the real ``specflow`` entry point (``cli.main``): a contract
declaring ``verify_exit_code: 2`` whose command exits 2 is RECORDED by
``specflow verify`` and then judged PASSING by every reader (brief, evidence,
risk tier, project audit); a contract with no declared code whose command
exits 1 is judged FAILING by every reader. Also drives ``specflow
artifact-lint --type dead-oracle`` and ``specflow project-audit`` to prove the
dead-oracle finding is accounting-only at the CLI boundary.
"""

from __future__ import annotations

import contextlib
import io
import shlex
import sys
from pathlib import Path

import pytest
import yaml

from specflow import cli
from specflow.commands import brief as brief_cmd
from specflow.commands import project_audit as audit_cmd
from specflow.lib import artifacts as art_lib
from specflow.lib import evidence as evidence_lib
from specflow.lib import risk as risk_lib


@pytest.fixture(autouse=True)
def _restore_type_registry():
    snaps = [(m, dict(m)) for m in (art_lib.TYPE_TO_DIR, art_lib.TYPE_TO_PREFIX,
                                     art_lib.PREFIX_TO_TYPE, art_lib.TYPE_ALIASES)]
    yield
    for live, snap in snaps:
        live.clear()
        live.update(snap)


_PY = shlex.quote(sys.executable)

_TYPES = [
    ("unit-test", "UT", "specs/unit-tests"),
    ("story", "STORY", "work/stories"),
]
_FLOW = {"draft": [], "approved": ["draft"], "implemented": ["approved"],
         "verified": ["implemented"]}


def _project(tmp: Path) -> Path:
    root = tmp / "project"
    schema_dir = root / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (root / ".specflow" / "standards").mkdir(parents=True, exist_ok=True)
    for art_type, prefix, rel in _TYPES:
        schema = {
            "type": art_type, "prefix": prefix, "directory": f"_specflow/{rel}",
            "allowed_status": dict(_FLOW),
            "allowed_link_roles": ["verified_by", "implements"],
            "optional_fields": ["verify_command", "verify_exit_code"],
        }
        (schema_dir / f"{art_type}.yaml").write_text(yaml.dump(schema), encoding="utf-8")
    config = {"project": {"name": "vx-test", "created": "2026-01-01"},
              "artifact_types": [t for t, _, _ in _TYPES], "active_packs": []}
    (root / ".specflow" / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")
    (root / ".specflow" / "state.yaml").write_text(
        yaml.dump({"current": "idle", "history": []}), encoding="utf-8")
    (root / "tests").mkdir()
    (root / "exit_with.py").write_text(
        "import sys\nsys.exit(int(sys.argv[1]))\n", encoding="utf-8")
    return root


def _mk(root: Path, art_type: str, art_id: str, *, links=None, **extra) -> None:
    rel = {t: r for t, _, r in _TYPES}[art_type]
    path = root / "_specflow" / rel / f"{art_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = {"id": art_id, "title": art_id, "type": art_type, "status": "implemented",
          "tags": [], "suspect": False, "links": links or [], "created": "2026-01-01"}
    fm.update(extra)
    path.write_text(f"---\n{yaml.dump(fm, sort_keys=False)}---\n\nBody.\n", encoding="utf-8")


def _cli(*argv: str) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cli.main(list(argv))
    return code, buf.getvalue()


def _readers(arts: list[art_lib.Artifact], test_id: str, story_id: str) -> dict[str, bool]:
    """Each reader's verdict for ``test_id``: True = counted as passing."""
    brief_out = brief_cmd._next_skill_recommendation("executing", arts, [], [])
    ev_row = next(ln for ln in evidence_lib._test_results_section(arts)
                  if ln.startswith(f"| {test_id} "))
    risk_ev = risk_lib.verification_evidence([story_id], arts)
    lens = audit_cmd._verification_lens(arts)
    return {
        "brief": test_id not in brief_out,
        "evidence": "see audit" not in ev_row and "verify_run exit=" in ev_row,
        "risk": risk_ev.startswith("ran ("),
        "audit": not any(f["severity"] == "warn" and test_id in f["message"]
                         for f in lens),
    }


def test_declared_nonzero_exit_recorded_then_passes_everywhere(tmp_path, monkeypatch):
    root = _project(tmp_path)
    _mk(root, "story", "STORY-001")
    _mk(root, "unit-test", "UT-001",
        links=[{"target": "STORY-001", "role": "verified_by"}],
        verify_command=f"{_PY} exit_with.py 2", verify_exit_code=2)
    monkeypatch.chdir(root)

    code, out = _cli("verify", "UT-001")
    assert code == 0, out
    arts = art_lib.discover_artifacts(root)
    ut = next(a for a in arts if a.id == "UT-001")
    assert str(ut.frontmatter.get("verify_run_exit_code")) == "2"
    assert _readers(arts, "UT-001", "STORY-001") == {
        "brief": True, "evidence": True, "risk": True, "audit": True}


def test_undeclared_failing_exit_recorded_then_fails_everywhere(tmp_path, monkeypatch):
    root = _project(tmp_path)
    _mk(root, "story", "STORY-001")
    _mk(root, "unit-test", "UT-001",
        links=[{"target": "STORY-001", "role": "verified_by"}],
        verify_command=f"{_PY} exit_with.py 1")
    monkeypatch.chdir(root)

    code, out = _cli("verify", "UT-001")
    assert code == 0, out  # recorded, never gated
    arts = art_lib.discover_artifacts(root)
    assert _readers(arts, "UT-001", "STORY-001") == {
        "brief": False, "evidence": False, "risk": False, "audit": False}


def test_dead_oracle_cli_warns_and_audit_stays_green(tmp_path, monkeypatch):
    root = _project(tmp_path)
    _mk(root, "unit-test", "UT-001",
        verify_command="uv run pytest tests/test_gone.py::test_x -q")
    monkeypatch.chdir(root)

    code, out = _cli("artifact-lint", "--type", "dead-oracle")
    assert code == 0, out
    assert "UT-001" in out and "tests/test_gone.py" in out and "dead oracle" in out

    code, out = _cli("project-audit", "--dry-run")
    assert code == 0, out
