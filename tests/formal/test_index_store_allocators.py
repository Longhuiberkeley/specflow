"""Exclusive-create allocators outside the artifact index (STORY-696 AC3).

PREV patterns, baselines and impact-log events each allocate a file name.
A writer that computed the same name concurrently must never replace the
other's file (DDD-034 I2). Each test forces the collision deterministically
by placing the competing file between the allocator's decision and its write.
"""

from __future__ import annotations

from datetime import datetime as real_datetime
from pathlib import Path

import yaml

from specflow.lib import baselines as baselines_lib
from specflow.lib import impact as impact_lib
from specflow.lib import learning as learning_lib

from index_store_support import scaffold


def test_I2_prev_allocator_never_replaces_a_pattern(tmp_path: Path, monkeypatch):
    root = scaffold(tmp_path)
    learned = root / ".specflow" / "checklists" / "learned"
    learned.mkdir(parents=True)
    # A racing writer already took PREV-001 after this one chose it.
    monkeypatch.setattr(learning_lib, "_next_prev_number", lambda _root: 1)
    (learned / "PREV-001.yaml").write_text("id: PREV-001\nname: other\n", encoding="utf-8")
    path = learning_lib.persist_prevention_pattern(
        root, {"name": "mine", "items": [{"check": "c"}]}
    )
    assert path.name == "PREV-002.yaml"
    assert yaml.safe_load((learned / "PREV-001.yaml").read_text())["name"] == "other"
    assert yaml.safe_load(path.read_text())["items"][0]["id"] == "PREV-002-01"


def test_I2_baseline_create_is_exclusive(tmp_path: Path, monkeypatch):
    root = scaffold(tmp_path)
    target = baselines_lib._baseline_path(root, "v1.0.0")

    def racing_ref(_root, _name):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("name: v1.0.0\nartifacts: {}\nwriter: other\n", encoding="utf-8")
        return "abc123"

    monkeypatch.setattr(baselines_lib, "_resolve_git_ref", racing_ref)
    res = baselines_lib.create_baseline(root, "v1.0.0")
    assert res["ok"] is False and "immutable" in res["error"]
    assert yaml.safe_load(target.read_text())["writer"] == "other"


def test_I2_impact_events_in_one_second_are_both_kept(tmp_path: Path, monkeypatch):
    root = scaffold(tmp_path)

    class Frozen(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime(2026, 9, 30, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr(impact_lib, "datetime", Frozen)
    ev = lambda kind: impact_lib.ImpactEvent(  # noqa: E731
        changed="REQ-001", change_type=kind, fingerprint_old="a",
        fingerprint_new="b", update_type="semantic", flagged_suspects=[],
    )
    first = impact_lib.create_impact_event(root, ev("content_modified"))
    second = impact_lib.create_impact_event(root, ev("status_changed"))
    assert first != second
    kinds = sorted(e.change_type for e in impact_lib.load_impact_events(root))
    assert kinds == ["content_modified", "status_changed"]
