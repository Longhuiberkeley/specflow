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


def test_story_derives_from_fills_story_column(project_root: Path):
    # A4: a STORY reaching a REQ via derives_from (the legacy-story pattern)
    # fills the STORY column exactly like `implements` — it is not a gap.
    from specflow.lib import artifacts as art_lib

    req = art_lib.Artifact(
        path=Path("REQ-009.md"),
        frontmatter={"id": "REQ-009", "title": "Legacy req", "type": "requirement", "status": "approved"},
        body="Body.", links=[],
    )
    story = art_lib.Artifact(
        path=Path("STORY-009.md"),
        frontmatter={"id": "STORY-009", "title": "Legacy story", "type": "story", "status": "approved"},
        body="Body.",
        links=[art_lib.Link(target="REQ-009", role="derives_from")],
    )
    row = rtm_cmd._row_for_req(req, [req, story])
    assert [s.id for s in row["stories"]] == ["STORY-009"]
    assert "STORY" not in row["gaps"]


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


# ── --gaps hides terminal REQs (STORY-716 AC4, F-034) ────────────────────────

_TERMINAL_REQ = """---
id: REQ-003
title: Retired requirement
type: requirement
status: deprecated
created: '2026-01-01'
---
Body.
"""


def test_gaps_hides_terminal_reqs_with_footer(project_root: Path, capsys):
    _write(project_root / "_specflow/specs/requirements/REQ-003.md", _TERMINAL_REQ)
    rc = rtm_cmd.run(project_root, {"format": "table", "gaps": True})
    out = capsys.readouterr().out
    assert rc == 0
    assert "REQ-002" in out, "a live gap row still shows"
    assert "REQ-003" not in out
    assert "1 terminal REQ(s) hidden; --include-terminal to show" in out


def test_gaps_include_terminal_shows_them_without_footer(project_root: Path, capsys):
    _write(project_root / "_specflow/specs/requirements/REQ-003.md", _TERMINAL_REQ)
    rtm_cmd.run(project_root, {"format": "table", "gaps": True, "include_terminal": True})
    out = capsys.readouterr().out
    assert "REQ-003 (deprecated)" in out
    assert "terminal REQ(s) hidden" not in out


def test_gaps_csv_has_no_footer(project_root: Path, capsys):
    _write(project_root / "_specflow/specs/requirements/REQ-003.md", _TERMINAL_REQ)
    rtm_cmd.run(project_root, {"format": "csv", "gaps": True})
    out = capsys.readouterr().out
    assert "REQ-003" not in out
    assert "terminal REQ(s) hidden" not in out
    assert out.splitlines()[0] == "req,status,arch,story,tests,gap"


def test_full_matrix_still_lists_terminal_reqs(project_root: Path, capsys):
    _write(project_root / "_specflow/specs/requirements/REQ-003.md", _TERMINAL_REQ)
    rtm_cmd.run(project_root, {"format": "table"})
    out = capsys.readouterr().out
    assert "REQ-003 (deprecated)" in out
    assert "terminal REQ(s) hidden" not in out


# ── canonical parent-held refinement (F-009 engine half) ─────────────────────

def _canonical_chain(root: Path) -> None:
    """REQ-010 refined_by ARCH-010 refined_by DDD-010 — links held by the parent only."""
    base = root / "_specflow"
    _write(base / "specs/requirements/REQ-010.md", """---
id: REQ-010
title: Canonical-shape requirement
type: requirement
status: approved
created: '2026-01-01'
links:
- target: ARCH-010
  role: refined_by
---
Body.
""")
    _write(base / "specs/architecture/ARCH-010.md", """---
id: ARCH-010
title: Canonical-shape architecture
type: architecture
status: approved
created: '2026-01-01'
links:
- target: DDD-010
  role: refined_by
---
Body.
""")
    _write(base / "specs/detailed-design/DDD-010.md", """---
id: DDD-010
title: Canonical-shape design
type: detailed-design
status: approved
created: '2026-01-01'
---
Body.
""")
    _write(base / "specs/integration-tests/IT-010.md", """---
id: IT-010
title: IT for ARCH-010
type: integration-test
status: approved
created: '2026-01-01'
links:
- target: ARCH-010
  role: verified_by
---
Body.
""")
    _write(base / "specs/unit-tests/UT-010.md", """---
id: UT-010
title: UT for DDD-010
type: unit-test
status: approved
created: '2026-01-01'
links:
- target: DDD-010
  role: verified_by
---
Body.
""")


def test_parent_held_refined_by_fills_arch_and_tests(project_root: Path):
    _canonical_chain(project_root)
    row = _find_row(_rows(project_root, {}), "REQ-010")
    assert [a.id for a in row["archs"]] == ["ARCH-010"]
    assert sorted(t.id for t in row["tests"]) == ["IT-010", "UT-010"]
    assert row["gaps"] == ["STORY"]


def test_child_held_legacy_shape_still_resolves(project_root: Path):
    # The fixture's REQ-001 is refined both ways; ARCH-001 must appear once.
    row = _find_row(_rows(project_root, {}), "REQ-001")
    assert [a.id for a in row["archs"]] == ["ARCH-001"]


def test_compute_chain_depth_follows_parent_held_refinement(project_root: Path):
    from specflow.lib import artifacts as art_lib

    _canonical_chain(project_root)
    artifacts = art_lib.discover_artifacts(project_root)
    path = art_lib.compute_chain_depth("REQ-010", art_lib.build_id_index(artifacts))
    assert path[:3] == ["REQ-010", "ARCH-010", "DDD-010"]
    assert path[-1] == "UT-010"


def test_compute_chain_depth_ignores_legacy_child_held_refined_by(project_root: Path):
    """A legacy ``DDD refined_by ARCH`` (child-held, pointing up) must not be
    followed as if it were a parent-held refinement: walking it would climb from
    DDD-X sideways into ARCH-B and REQ-B, inflating REQ-A's chain (P-11 blocker)."""
    from specflow.lib import artifacts as art_lib

    base = project_root / "_specflow"
    _write(base / "specs/requirements/REQ-020.md", """---
id: REQ-020
title: REQ-A
type: requirement
status: approved
created: '2026-01-01'
---
Body.
""")
    _write(base / "specs/requirements/REQ-021.md", """---
id: REQ-021
title: REQ-B
type: requirement
status: approved
created: '2026-01-01'
---
Body.
""")
    _write(base / "specs/architecture/ARCH-020.md", """---
id: ARCH-020
title: ARCH-A
type: architecture
status: approved
created: '2026-01-01'
links:
- target: REQ-020
  role: derives_from
---
Body.
""")
    _write(base / "specs/architecture/ARCH-021.md", """---
id: ARCH-021
title: ARCH-B
type: architecture
status: approved
created: '2026-01-01'
links:
- target: REQ-021
  role: derives_from
---
Body.
""")
    _write(base / "specs/detailed-design/DDD-020.md", """---
id: DDD-020
title: DDD-X (legacy child-held refined_by)
type: detailed-design
status: approved
created: '2026-01-01'
links:
- target: ARCH-020
  role: refined_by
- target: ARCH-021
  role: refined_by
---
Body.
""")
    artifacts = art_lib.discover_artifacts(project_root)
    path = art_lib.compute_chain_depth("REQ-020", art_lib.build_id_index(artifacts))
    assert path[:2] == ["REQ-020", "ARCH-020"]
    assert "ARCH-021" not in path
    assert "REQ-021" not in path
    # The legacy child-held edge still counts downstream (ARCH-020 -> DDD-020).
    assert "DDD-020" in path


def test_cli_parses_rtm_gaps_include_terminal():
    """The `--gaps` footer advertises `--include-terminal`; the parser must accept it."""
    from specflow.cli import build_parser

    ns = build_parser().parse_args(["rtm", "--gaps", "--include-terminal"])
    assert ns.gaps is True
    assert ns.include_terminal is True
