"""Qualification: parallel `specflow` CLI processes keep I1-I4 (STORY-696).

N concurrent `specflow create` processes race `specflow update` and
`specflow rebuild-index` processes on the same artifact type, as parallel
agents in an execute wave do. Afterwards: every reported create owns a
distinct id whose file carries its title (I1, I2), and the index equals the
ids on disk with next_id above every id handed out (I3, I4).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from specflow.lib import artifacts as art_lib

from index_store_support import invariant_violations, scaffold

N_CREATORS = 8


def _cli(root: Path, *args: str) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "specflow", *args],
        cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
    )


def test_I4_parallel_cli_creates_updates_rebuilds_keep_invariants(tmp_path: Path):
    root = scaffold(tmp_path)
    assert art_lib.create_artifact(root, "requirement", title="seed", body="s")["ok"]
    procs = [
        (f"Parallel requirement number {i} of the wave",
         _cli(root, "create", "--type", "requirement", "--skip-dedup-check",
              "--title", f"Parallel requirement number {i} of the wave",
              "--body", f"body {i}"))
        for i in range(N_CREATORS)
    ]
    others = [
        _cli(root, "update", "REQ-001", "--tags", "a,b"),
        _cli(root, "rebuild-index"),
        _cli(root, "update", "REQ-001", "--tags", "c"),
        _cli(root, "rebuild-index"),
    ]
    created: dict[str, str] = {}
    for title, p in procs:
        out, err = p.communicate(timeout=180)
        assert p.returncode == 0, f"create failed: {out}{err}"
        m = re.search(r"\b(REQ-\d{3,})\b", out)
        assert m, out
        created[m.group(1)] = title
    for p in others:
        out, err = p.communicate(timeout=180)
        assert p.returncode == 0, f"{p.args}: {out}{err}"

    assert len(created) == N_CREATORS, "two creates reported the same id"
    for art_id, title in created.items():
        art = art_lib.parse_artifact(art_lib.resolve_link_target(root, art_id))
        assert art is not None and art.title == title, f"{art_id} lost its content"
    allocated = {"requirement": set(created) | {"REQ-001"}}
    assert invariant_violations(root, allocated) == []
