"""reconcile propagates a refused or failed cascade (STORY-697, DEF-011 follow-up).

DEF-011 fixed cascade-status to exit non-zero when a transition is refused or
fails. reconcile called cascade_status.run() and ignored its return code, so
the same symptom moved one caller up: a failure mark and exit 0.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from specflow.lib import artifacts as art_lib
from test_cascade_support import project, put, run_cli, status_of


def _story_with_output_files(root: Path, links: list[tuple[str, str]]) -> None:
    put(root, "STORY-001", "approved", links)
    (root / "src").mkdir(exist_ok=True)
    (root / "src" / "impl.py").write_text("x = 1\n", encoding="utf-8")
    path = root / "_specflow" / art_lib.TYPE_TO_DIR["story"] / "STORY-001.md"
    text = path.read_text(encoding="utf-8")
    _, fm, body = text.split("---\n", 2)
    data = yaml.safe_load(fm)
    data["output_files"] = ["src/impl.py"]
    path.write_text("---\n" + yaml.dump(data, sort_keys=False) + "---\n" + body,
                    encoding="utf-8")


def test_reconcile_exits_nonzero_when_the_cascade_refuses(tmp_path, monkeypatch):
    root = project(tmp_path)
    put(root, "REQ-001", "approved")
    put(root, "ARCH-001", "draft")
    _story_with_output_files(root, [("REQ-001", "implements"), ("ARCH-001", "guided_by")])
    art_lib.rebuild_index(root)

    code, out = run_cli(root, monkeypatch, "reconcile")

    assert status_of(root, "STORY-001") == "implemented", out
    assert "ARCH-001" in out
    assert not (code == 0 and "✗" in out), out
    assert code == 1, out


def test_reconcile_exits_zero_when_every_cascade_succeeds(tmp_path, monkeypatch):
    root = project(tmp_path)
    put(root, "REQ-001", "approved")
    put(root, "ARCH-001", "approved")
    _story_with_output_files(root, [("REQ-001", "implements"), ("ARCH-001", "guided_by")])
    art_lib.rebuild_index(root)

    code, out = run_cli(root, monkeypatch, "reconcile")

    assert code == 0, out
    assert "✗" not in out, out
    assert status_of(root, "STORY-001") == "implemented", out
