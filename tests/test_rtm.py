"""Tests for `specflow rtm` — bidirectional requirements-traceability matrix.

Builds a small fixture project with a full REQ -> ARCH -> DDD -> UT chain plus
a QT and STORY on the REQ, an IT on the ARCH, an orphan test, and a second REQ
with no decomposition at all (a gap row).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specflow.commands import rtm as rtm_cmd


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    base = root / "_specflow"

    _write(
        base / "specs/requirements/REQ-001.md",
        """---
id: REQ-001
title: Fully covered requirement
type: requirement
status: approved
created: '2026-01-01'
links:
- target: ARCH-001
  role: refined_by
---
Body.
""",
    )

    _write(
        base / "specs/requirements/REQ-002.md",
        """---
id: REQ-002
title: Uncovered requirement (gap row)
type: requirement
status: draft
created: '2026-01-01'
---
Body.
""",
    )

    _write(
        base / "specs/architecture/ARCH-001.md",
        """---
id: ARCH-001
title: Core Architecture
type: architecture
status: approved
created: '2026-01-01'
links:
- target: REQ-001
  role: derives_from
---
Body.
""",
    )

    _write(
        base / "specs/detailed-design/DDD-001.md",
        """---
id: DDD-001
title: Detailed Design
type: detailed-design
status: approved
created: '2026-01-01'
links:
- target: ARCH-001
  role: derives_from
---
Body.
""",
    )

    _write(
        base / "work/stories/STORY-001.md",
        """---
id: STORY-001
title: Implement the thing
type: story
status: approved
created: '2026-01-01'
links:
- target: REQ-001
  role: implements
---
Body.
""",
    )

    _write(
        base / "specs/qualification-tests/QT-001.md",
        """---
id: QT-001
title: QT for REQ-001
type: qualification-test
status: approved
created: '2026-01-01'
links:
- target: REQ-001
  role: verified_by
---
Body.
""",
    )

    _write(
        base / "specs/integration-tests/IT-001.md",
        """---
id: IT-001
title: IT for ARCH-001
type: integration-test
status: approved
created: '2026-01-01'
links:
- target: ARCH-001
  role: verified_by
---
Body.
""",
    )

    _write(
        base / "specs/unit-tests/UT-001.md",
        """---
id: UT-001
title: UT for DDD-001
type: unit-test
status: approved
created: '2026-01-01'
links:
- target: DDD-001
  role: verified_by
---
Body.
""",
    )

    _write(
        base / "specs/unit-tests/UT-002.md",
        """---
id: UT-002
title: Orphan unit test
type: unit-test
status: draft
created: '2026-01-01'
---
Body.
""",
    )

    return root


def test_basic_matrix_full_chain(project_root: Path, capsys):
    rc = rtm_cmd.run(project_root, {"format": "table"})
    assert rc == 0
    out = capsys.readouterr().out
    assert "REQ-001" in out
    assert "ARCH-001" in out
    assert "STORY-001" in out
    # All four test tiers reach REQ-001's row via the chain.
    assert "QT-001" in out
    assert "IT-001" in out
    assert "UT-001" in out
    # REQ-002 has nothing and should show a gap.
    assert "REQ-002" in out


def test_gap_row_flags_missing_columns(project_root: Path):
    rows_all = _rows(project_root, {"format": "table"})
    req2 = _find_row(rows_all, "REQ-002")
    assert req2 is not None
    assert "ARCH" in req2["gaps"]
    assert "STORY" in req2["gaps"]
    assert "tests" in req2["gaps"]

    req1 = _find_row(rows_all, "REQ-001")
    assert req1 is not None
    assert req1["gaps"] == []


def test_gaps_filter_only_shows_gap_rows(project_root: Path, capsys):
    rc = rtm_cmd.run(project_root, {"format": "table", "gaps": True})
    assert rc == 0
    out = capsys.readouterr().out
    assert "REQ-002" in out
    assert "REQ-001" not in out


def test_req_filter(project_root: Path, capsys):
    rc = rtm_cmd.run(project_root, {"format": "table", "req": "REQ-001"})
    assert rc == 0
    out = capsys.readouterr().out
    assert "REQ-001" in out
    assert "REQ-002" not in out


def test_orphan_tests_footer(project_root: Path, capsys):
    rc = rtm_cmd.run(project_root, {"format": "table"})
    assert rc == 0
    out = capsys.readouterr().out
    assert "Orphan tests" in out
    assert "UT-002" in out


def test_csv_format_smoke(project_root: Path, capsys):
    rc = rtm_cmd.run(project_root, {"format": "csv"})
    assert rc == 0
    out = capsys.readouterr().out
    assert "req,status,arch,story,tests,gap" in out
    assert "REQ-001" in out
    assert "orphan_tests," in out


def test_markdown_format_smoke(project_root: Path, capsys):
    rc = rtm_cmd.run(project_root, {"format": "markdown"})
    assert rc == 0
    out = capsys.readouterr().out
    assert "| REQ | Status | ARCH | STORY | Tests | Gap |" in out
    assert "REQ-001" in out


def test_unknown_req_filter_exits_zero(project_root: Path, capsys):
    rc = rtm_cmd.run(project_root, {"format": "table", "req": "REQ-999"})
    assert rc == 0


# ── helpers that reach into the module's row builder for structural assertions ──

def _rows(root: Path, args: dict):
    from specflow.lib import artifacts as art_lib

    artifacts = art_lib.discover_artifacts(root)
    reqs = sorted((a for a in artifacts if a.type == "requirement"), key=lambda a: a.id)
    return [rtm_cmd._row_for_req(r, artifacts) for r in reqs]


def _find_row(rows, req_id: str):
    for r in rows:
        if r["req"].id == req_id:
            return r
    return None
