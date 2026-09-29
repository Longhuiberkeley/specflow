"""cascade-status as a real process: exit status and legal walk (STORY-697 AC1, AC2, AC4).

Runs ``python -m specflow cascade-status`` in a subprocess against a project
scaffolded from the real schemas, so the exit status a shell, hook or CI job
sees is the one pinned here.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from specflow.lib import artifacts as art_lib
from test_cascade_support import project, put, status_of


def _sf(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "specflow", *args], cwd=str(root),
                          capture_output=True, text=True, stdin=subprocess.DEVNULL, check=False)


def test_process_walks_legally_then_holds_and_refuses_with_exit_1(tmp_path: Path):
    root = project(tmp_path)
    put(root, "REQ-001", "approved")    # only implementing STORY verified -> verified
    put(root, "REQ-002", "approved")    # sibling STORY-002 unverified -> held at implemented
    put(root, "ARCH-001", "approved")
    put(root, "DDD-001", "draft")       # refused: not approved
    put(root, "STORY-001", "verified", [("REQ-001", "implements"), ("REQ-002", "implements"),
                                         ("ARCH-001", "guided_by"), ("DDD-001", "specified_by")])
    put(root, "STORY-002", "implemented", [("REQ-002", "implements")])
    art_lib.rebuild_index(root)

    proc = _sf(root, "cascade-status", "STORY-001", "--include-req")

    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert status_of(root, "REQ-001") == "verified"
    assert status_of(root, "REQ-002") == "implemented"
    assert status_of(root, "ARCH-001") == "verified"
    assert status_of(root, "DDD-001") == "draft"
    assert "STORY-002" in proc.stdout and "DDD-001" in proc.stdout


def test_process_exits_0_when_every_transition_succeeds(tmp_path: Path):
    root = project(tmp_path)
    put(root, "ARCH-001", "approved")
    put(root, "STORY-001", "implemented", [("ARCH-001", "guided_by")])
    art_lib.rebuild_index(root)

    proc = _sf(root, "cascade-status", "STORY-001")

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert status_of(root, "ARCH-001") == "implemented"
