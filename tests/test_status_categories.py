"""STORY-748 / DEF-021: status and brief render every schema category.

Pre-fix, ``status._load_categories`` kept only spec/work/review/research, so a
pack category (the ops pack's RUN/MONITOR) vanished from the dashboard. The
core four still render first, in lifecycle order; extras follow, sorted.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from specflow.commands import brief as brief_cmd
from specflow.commands import init as init_cmd
from specflow.commands import status as status_cmd

_PACKS = Path(__file__).resolve().parents[1] / "src" / "specflow" / "packs"


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    assert init_cmd.run(root, {"platform": "claude-code", "no_ci": True}) == 0
    req = root / "_specflow" / "specs" / "requirements" / "REQ-001.md"
    req.parent.mkdir(parents=True, exist_ok=True)
    req.write_text(
        "---\nid: REQ-001\ntitle: Lockout\ntype: requirement\nstatus: draft\n"
        "created: '2026-10-18'\n---\n\n# Lockout\n\nThe system shall lock out.\n",
        encoding="utf-8",
    )
    return root


def _add_run(root: Path) -> None:
    shutil.copy(_PACKS / "ops" / "schemas" / "run.yaml", root / ".specflow" / "schema" / "run.yaml")
    run = root / "_specflow" / "ops" / "runs" / "RUN-001.md"
    run.parent.mkdir(parents=True, exist_ok=True)
    run.write_text(
        "---\nid: RUN-001\ntitle: Prod deploy\ntype: run\nstatus: live\n"
        "created: '2026-10-18'\nenvironment: prod\ndeployed_ref: v1.0.0\n---\n\n"
        "# Prod deploy\n",
        encoding="utf-8",
    )


def _category_rows(out: str) -> list[str]:
    labels = ("Specs:", "Work:", "Reviews:", "Research:", "Ops:")
    return [ln.strip().split()[0] for ln in out.splitlines() if ln.strip().startswith(labels)]


def test_load_categories_keeps_extra_category(tmp_path: Path):
    root = _project(tmp_path)
    _add_run(root)
    cats = status_cmd._load_categories(root)
    assert "RUN" in cats["ops"]
    assert list(cats)[:4] == ["spec", "work", "review", "research"]


def test_status_shows_ops_row_after_core_rows(tmp_path: Path, capsys):
    root = _project(tmp_path)
    _add_run(root)
    assert status_cmd.run(root, {}) == 0
    out = capsys.readouterr().out
    assert "Ops:" in out and "1 RUN" in out
    rows = _category_rows(out)
    assert rows[-1] == "Ops:"
    assert rows.index("Specs:") < rows.index("Ops:")


def test_status_layout_unchanged_without_extras(tmp_path: Path, capsys):
    root = _project(tmp_path)
    assert status_cmd.run(root, {}) == 0
    out = capsys.readouterr().out
    assert "Ops:" not in out
    assert _category_rows(out)[0] == "Specs:"


def test_empty_category_falls_back_to_spec(tmp_path: Path, capsys):
    # `category:` with no value must not crash brief's sorted() or print a
    # "None:" row on the dashboard.
    root = _project(tmp_path)
    _add_run(root)
    schema = root / ".specflow" / "schema" / "run.yaml"
    schema.write_text(schema.read_text(encoding="utf-8").replace("category: ops", "category:"),
                      encoding="utf-8")
    assert "RUN" in status_cmd._load_categories(root)["spec"]
    assert status_cmd.run(root, {}) == 0
    assert brief_cmd.run(root, {}) == 0
    assert "None" not in capsys.readouterr().out


def test_status_complete_phase_routes_to_next_cycle(tmp_path: Path):
    # DEF-022 on the dashboard: a released project is pointed at the next
    # cycle, not back at ship.
    s = status_cmd._suggest_action(tmp_path, "complete", {"REQ": 1})
    assert "/specflow-discover" in s
    assert "/specflow-ship" not in s


def test_brief_inventory_lists_ops_category(tmp_path: Path, capsys):
    root = _project(tmp_path)
    _add_run(root)
    assert brief_cmd.run(root, {}) == 0
    out = capsys.readouterr().out
    inv = out.split("Inventory", 1)[1]
    lines = [ln.split()[0] for ln in inv.splitlines() if ln.strip() and ln.startswith("    ") and not ln.startswith("     ")]
    assert "ops" in lines
    assert lines.index("spec") < lines.index("ops")
