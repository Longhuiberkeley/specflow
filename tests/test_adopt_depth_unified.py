"""SPIKE-008 R2-010: `adopt status` and `brief` share one ARCH depth rule.

full = parent REQ and child DDD; skeleton = anything less, including the
bare skeleton-sweep ARCH (no REQ, no DDD). There is no `isolated` ARCH depth.
"""

from __future__ import annotations

from specflow.commands import adopt as adopt_cmd
from specflow.commands import brief as brief_cmd
from specflow.lib import artifacts as art_lib

from test_adoption_mechanics import (  # noqa: F401 — reuse scaffold fixture
    _make_backfilled_project,
    _write_artifact,
    project_root,
)


def _arts(root):
    return [
        art_lib.parse_artifact(p)
        for p in sorted((root / "_specflow").rglob("*.md"))
        if not p.name.startswith("_")
    ]


def _add_req_arch_without_ddd(root):
    # REQ + ARCH, no DDD: brief used to call this `full`.
    _write_artifact(root, "REQ-002", "requirement", title="Inventory",
                    status="approved", tags=["backfilled"])
    _write_artifact(root, "ARCH-003", "architecture", title="Inventory",
                    status="implemented", tags=["backfilled"],
                    output_files=["src/main/inventory/**/*.py"],
                    extra_fm={"links": [{"target": "REQ-002", "role": "derives_from"}]})


def test_depth_label_has_no_isolated():
    # SPIKE-008 R2-010
    assert adopt_cmd._depth_label(False, False) == "skeleton"
    assert adopt_cmd._depth_label(True, False) == "skeleton"
    assert adopt_cmd._depth_label(False, True) == "skeleton"
    assert adopt_cmd._depth_label(True, True) == "full"


def test_arch_depth_per_shape(project_root):
    # SPIKE-008 R2-010
    _make_backfilled_project(project_root)
    _add_req_arch_without_ddd(project_root)
    arts = _arts(project_root)
    by_id = {a.id: a for a in arts}
    assert adopt_cmd.arch_depth(arts, by_id["ARCH-001"]) == "skeleton"  # bare sweep
    assert adopt_cmd.arch_depth(arts, by_id["ARCH-002"]) == "full"      # REQ + DDD
    assert adopt_cmd.arch_depth(arts, by_id["ARCH-003"]) == "skeleton"  # REQ, no DDD


def test_brief_and_adopt_status_agree(project_root, capsys):
    # SPIKE-008 R2-010
    _make_backfilled_project(project_root)
    _add_req_arch_without_ddd(project_root)
    arts = _arts(project_root)
    summary = brief_cmd._adoption_summary(project_root, arts)
    assert summary["full_archs"] == 1
    assert summary["skeleton_archs"] == 2

    adopt_cmd.run(project_root, {})
    out = capsys.readouterr().out
    assert "isolated" not in out

    adopt_cmd.run(project_root, {"target": "ARCH-001"})
    out = capsys.readouterr().out
    assert "skeleton" in out
    assert "missing parent REQ and child detail (DDD)" in out
    assert "isolated" not in out
