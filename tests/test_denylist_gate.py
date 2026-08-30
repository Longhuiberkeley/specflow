"""Privacy denylist gate guard (STORY-647, REQ-038, DDD-029).

Imports the single-source gate script (scripts/denylist_gate.py) so the
pattern lives in exactly one place; these tests pin its behavior:

  1. The tracked tree is clean (the CI gate can never silently rot).
  2. Leak tokens are detected; anchored numerics don't over-match.
  3. Enumerated allowlist entries and bytecode artifacts are skipped.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "denylist_gate.py"
_spec = importlib.util.spec_from_file_location("denylist_gate", _SCRIPT)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


def test_tracked_tree_is_clean():
    """The DDD-029 scope over the repo returns zero denylist hits."""
    assert gate.scan() == []


def test_detects_leak_tokens(tmp_path: Path):
    f = tmp_path / "notes.md"
    f.write_text("trained on cs2 data with a trailing stop at 0.020\n")
    hits = gate.scan_files([f], tmp_path)
    assert len(hits) == 1
    assert hits[0][0].name == "notes.md"
    assert hits[0][1] == 1


def test_anchored_numbers_do_not_overmatch(tmp_path: Path):
    f = tmp_path / "fine.md"
    f.write_text("values 0.0207 and 10.0219 stay quiet; lowercase eth too\n")
    assert gate.scan_files([f], tmp_path) == []


def test_allowlisted_exact_paths_skipped(tmp_path: Path):
    """Exact-path allowlist (ARCH-029): the sanctioned checklist is skipped,
    but a same-named file in ANY other directory is still scanned — a suffix
    trick must not bypass the gate."""
    allowed = tmp_path / "src/specflow/packs/autoresearch/skills/specflow-autoresearch/references/domain-research-checklists.md"
    allowed.parent.mkdir(parents=True)
    allowed.write_text("Kalman filter family vocabulary\n")
    assert gate.scan_files([allowed], tmp_path) == []

    decoy = tmp_path / "docs" / "domain-research-checklists.md"
    decoy.parent.mkdir()
    decoy.write_text("Kalman filter family vocabulary\n")
    hits = gate.scan_files([decoy], tmp_path)
    assert len(hits) == 1 and hits[0][0] == Path("docs/domain-research-checklists.md")


def test_bytecode_skipped(tmp_path: Path):
    pyc = tmp_path / "__pycache__" / "mod.cpython-311.pyc"
    pyc.parent.mkdir()
    pyc.write_bytes(b"/Volumes/ExternalDrive/leaked/absolute/path")
    assert gate.scan_files([pyc], tmp_path) == []


def test_ci_wiring_pinned():
    """The headline feature: the gate MUST stay wired into CI — deleting
    either invocation from the workflow fails this test (reviewer finding:
    nothing asserted the YAML)."""
    wf = (
        Path(__file__).resolve().parents[1]
        / ".github" / "workflows" / "specflow.yml"
    ).read_text(encoding="utf-8")
    assert wf.count("python3 scripts/denylist_gate.py") == 2, (
        "specflow.yml must invoke the denylist gate in BOTH the PR/push job "
        "and the release-authoritative tag job"
    )
    assert "privacy-denylist-gate" in wf
