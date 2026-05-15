"""Fixture tests for trace.py research-chain renderers (STORY-067).

Locks in the link-role contract from ARCH-023 §40:

    LOOP --[operates_on]--> COMP
    EXPT --[belongs_to]--> LOOP
    FIND --[belongs_to]--> COMP   (via required `competition` field)
    FIND --[condenses]--> LOOP    (via optional `source_loop` field)

The renderers were patched after STORY-067 first shipped with the wrong
roles (everything was `derives_from`). These tests trap the regression.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specflow.commands import trace as trace_cmd
from specflow.lib import artifacts as art_lib


def _art(art_id: str, art_type: str, status: str = "active",
         links: list[tuple[str, str]] | None = None,
         **extra_frontmatter) -> art_lib.Artifact:
    fm = {"id": art_id, "title": f"Test {art_id}", "type": art_type, "status": status}
    fm.update(extra_frontmatter)
    return art_lib.Artifact(
        path=Path(f"{art_id}.md"),
        frontmatter=fm,
        body="body",
        links=[art_lib.Link(target=t, role=r) for t, r in (links or [])],
    )


@pytest.fixture
def research_index() -> dict[str, art_lib.Artifact]:
    """One COMP, two LOOPs, three EXPTs, two FINDs — wired per ARCH-023 §40."""
    arts = [
        _art("COMP-001", "competition", status="active"),
        _art("LOOP-001", "loop", status="completed",
             links=[("COMP-001", "operates_on")],
             mode="explore", iteration_count=2, best_metric=1.83),
        _art("LOOP-002", "loop", status="running",
             links=[("COMP-001", "operates_on")],
             mode="exploit", iteration_count=1, best_metric=0.0),
        _art("EXPT-001", "experiment", status="kept",
             links=[("LOOP-001", "belongs_to")]),
        _art("EXPT-002", "experiment", status="discarded",
             links=[("LOOP-001", "belongs_to")]),
        _art("EXPT-003", "experiment", status="kept",
             links=[("LOOP-002", "belongs_to")]),
        # FIND-001: belongs to COMP-001, condenses LOOP-001
        _art("FIND-001", "finding", status="confirmed",
             links=[("COMP-001", "belongs_to"), ("LOOP-001", "condenses")]),
        # FIND-002: belongs to COMP-001, no source_loop (cross-loop synthesis)
        _art("FIND-002", "finding", status="draft",
             links=[("COMP-001", "belongs_to")]),
    ]
    return art_lib.build_id_index(arts)


class TestRenderComp:
    def test_lists_both_loops(self, research_index, capsys):
        comp = research_index["COMP-001"]
        rc = trace_cmd._render_comp(comp, research_index)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Experimentation Loops (2)" in out
        assert "LOOP-001" in out
        assert "LOOP-002" in out

    def test_nests_expts_under_their_loops(self, research_index, capsys):
        comp = research_index["COMP-001"]
        trace_cmd._render_comp(comp, research_index)
        out = capsys.readouterr().out
        # Both EXPTs from LOOP-001 should appear after LOOP-001 header
        loop1_pos = out.find("LOOP-001")
        loop2_pos = out.find("LOOP-002")
        expt1_pos = out.find("EXPT-001")
        expt2_pos = out.find("EXPT-002")
        expt3_pos = out.find("EXPT-003")
        assert loop1_pos < expt1_pos < loop2_pos, "EXPT-001 should nest under LOOP-001"
        assert loop1_pos < expt2_pos < loop2_pos, "EXPT-002 should nest under LOOP-001"
        assert loop2_pos < expt3_pos, "EXPT-003 should nest under LOOP-002"

    def test_lists_both_findings(self, research_index, capsys):
        comp = research_index["COMP-001"]
        trace_cmd._render_comp(comp, research_index)
        out = capsys.readouterr().out
        assert "Findings (2)" in out
        assert "FIND-001" in out
        assert "FIND-002" in out

    def test_no_findings_when_comp_has_none(self, capsys):
        arts = [_art("COMP-002", "competition")]
        idx = art_lib.build_id_index(arts)
        trace_cmd._render_comp(idx["COMP-002"], idx)
        out = capsys.readouterr().out
        assert "Findings (0)" in out


class TestRenderLoop:
    def test_parent_comp_via_operates_on(self, research_index, capsys):
        loop = research_index["LOOP-001"]
        rc = trace_cmd._render_loop(loop, research_index)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Parent Competition" in out
        assert "COMP-001" in out

    def test_lists_expts_belonging_to_this_loop(self, research_index, capsys):
        loop = research_index["LOOP-001"]
        trace_cmd._render_loop(loop, research_index)
        out = capsys.readouterr().out
        assert "Experiments (2)" in out
        assert "EXPT-001" in out
        assert "EXPT-002" in out
        # EXPT-003 belongs to LOOP-002 and must NOT appear
        assert "EXPT-003" not in out

    def test_lists_findings_via_condenses_role(self, research_index, capsys):
        # FIND-001 condenses LOOP-001; FIND-002 does not — only FIND-001 should show.
        loop = research_index["LOOP-001"]
        trace_cmd._render_loop(loop, research_index)
        out = capsys.readouterr().out
        assert "Findings (1)" in out
        assert "FIND-001" in out
        assert "FIND-002" not in out


class TestRenderExpt:
    def test_walks_up_to_loop_and_comp(self, research_index, capsys):
        expt = research_index["EXPT-001"]
        rc = trace_cmd._render_expt(expt, research_index)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Parent Loop" in out
        assert "LOOP-001" in out
        assert "Competition" in out
        assert "COMP-001" in out


class TestRoleSpecificity:
    """Renderers must check link role, not just link target — otherwise the
    pre-fix `derives_from` everywhere bug class can silently reappear."""

    def test_wrong_role_does_not_match_loops_under_comp(self, capsys):
        # LOOP with role `derives_from` instead of `operates_on` should NOT show.
        arts = [
            _art("COMP-003", "competition"),
            _art("LOOP-009", "loop", links=[("COMP-003", "derives_from")]),
        ]
        idx = art_lib.build_id_index(arts)
        trace_cmd._render_comp(idx["COMP-003"], idx)
        out = capsys.readouterr().out
        assert "Experimentation Loops (0)" in out
        assert "LOOP-009" not in out

    def test_wrong_role_does_not_match_expts_under_loop(self, capsys):
        # EXPT with role `derives_from` instead of `belongs_to` should NOT show.
        arts = [
            _art("COMP-004", "competition"),
            _art("LOOP-010", "loop", links=[("COMP-004", "operates_on")]),
            _art("EXPT-099", "experiment", links=[("LOOP-010", "derives_from")]),
        ]
        idx = art_lib.build_id_index(arts)
        trace_cmd._render_loop(idx["LOOP-010"], idx)
        out = capsys.readouterr().out
        assert "Experiments (0)" in out
        assert "EXPT-099" not in out

    def test_wrong_role_does_not_match_findings_under_comp(self, capsys):
        # FIND with role `derives_from` instead of `belongs_to` should NOT show.
        arts = [
            _art("COMP-005", "competition"),
            _art("FIND-099", "finding", links=[("COMP-005", "derives_from")]),
        ]
        idx = art_lib.build_id_index(arts)
        trace_cmd._render_comp(idx["COMP-005"], idx)
        out = capsys.readouterr().out
        assert "Findings (0)" in out
        assert "FIND-099" not in out
