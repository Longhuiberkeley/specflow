"""AGENTS.md release process records the ledger before the release commit (STORY-749 AC3).

Also guards the SPIKE-008 ledger amendments: no artifact body may name the
nonexistent `specflow ship --evidence` command (R1-039, R1-136).
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _release_steps() -> list[str]:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    section = text.split("## Release Process", 1)[1].split("\n### ", 1)[0]
    return re.findall(r"^\d+\. .*$", section, flags=re.MULTILINE)


def test_ledger_step_precedes_commit():  # SPIKE-008 R1-062
    steps = _release_steps()
    commit = next(i for i, s in enumerate(steps) if "**Commit:**" in s)
    ledger = [s for s in steps[:commit] if "document-changes --since" in s]
    assert len(ledger) == 1, "one release step before Commit must record the ledger"
    step = ledger[0]
    assert re.search(r"baseline create v1\.x\.x --evidence", step)
    assert "phase-set complete" in step
    assert "pre-release HEAD" in step


def test_release_steps_numbered_consecutively():
    numbers = [int(s.split(".", 1)[0]) for s in _release_steps()]
    assert numbers == list(range(1, len(numbers) + 1))


def test_pypi_ban_step_present():  # SPIKE-008 R1-145
    assert any("Do NOT publish to PyPI" in s for s in _release_steps())


def test_no_artifact_names_ship_evidence_command():  # SPIKE-008 R1-039, R1-136
    offenders = []
    paths = [*(ROOT / "_specflow/specs/requirements").glob("*.md"),
             *(ROOT / "_specflow/work/stories").glob("*.md")]
    for path in paths:
        body = path.read_text(encoding="utf-8").split("\n---\n", 1)[-1]
        for line in body.splitlines():
            if "specflow ship --evidence" in line and not line.startswith(">"):
                offenders.append(path.name)
    assert offenders == []
