"""Exhaustive legality table for cascade-status over the REAL schemas (STORY-697 AC1, AC3).

For every story status x ``--include-req`` x sibling state, the STORY links
one REQ, ARCH and DDD in EVERY status its schema allows. Each status write
the cascade performs is recorded as (type, from, to) and must be an edge of
that type's ``allowed_status`` in ``.specflow/schema``. Which links cascade
is one function (``cascade_targets``) shared with the status-cascade lint,
and every row also runs the real lint check and requires it to nudge exactly
the approved specs the cascade moves (AC3).
"""

from __future__ import annotations

import itertools
import re

import pytest
import yaml

from specflow.commands import artifact_lint as lint_cmd
from specflow.commands import cascade_status as cascade_cmd
from specflow.lib import artifacts as art_lib
from test_cascade_support import (
    PREFIX_TYPE, REAL_SCHEMAS, allowed, project, put, run_cli, spy_updates,
)

_ROLE = {"REQ": "implements", "ARCH": "guided_by", "DDD": "specified_by"}


def _schema(art_type: str) -> dict:
    return yaml.safe_load((REAL_SCHEMAS / f"{art_type}.yaml").read_text(encoding="utf-8"))


STORY_STATUSES = list(_schema("story")["allowed_status"])

_NUDGE = re.compile(r"\[(STORY-\d+)\] is '\w+' but linked (\S+) \(\w+\) is still 'approved'")


def _lint_nudged(root, story_id: str) -> set[str]:
    """Spec ids the real status-cascade lint check nudges for ``story_id``."""
    result = lint_cmd._run_check(art_lib.discover_artifacts(root), root, "status-cascade")
    return {m.group(2) for m in _NUDGE.finditer(result["detail"]) if m.group(1) == story_id}


@pytest.mark.parametrize(
    "story_status,include_req,unverified_sibling",
    list(itertools.product(STORY_STATUSES, [False, True], [False, True])),
)
def test_every_status_write_is_an_edge_of_the_real_schema(
    tmp_path, monkeypatch, story_status, include_req, unverified_sibling,
):
    root = project(tmp_path)
    links: list[tuple[str, str]] = []
    for prefix, role in _ROLE.items():
        for n, status in enumerate(_schema(PREFIX_TYPE[prefix])["allowed_status"], start=1):
            art_id = f"{prefix}-{n:03d}"
            put(root, art_id, status)
            links.append((art_id, role))
    put(root, "STORY-001", story_status, links)
    if unverified_sibling:
        put(root, "STORY-002", "implemented", links)
    art_lib.rebuild_index(root)
    lint_nudged = _lint_nudged(root, "STORY-001")
    calls = spy_updates(monkeypatch)

    argv = ["cascade-status", "STORY-001"] + (["--include-req"] if include_req else [])
    code, out = run_cli(root, monkeypatch, *argv)

    illegal = [(i, t, f, s) for i, t, f, s in calls if f not in allowed(root, t).get(s, [])]
    assert illegal == [], out
    # AC3: the status-cascade lint nudges exactly the approved specs this
    # cascade moves. The lint's REQ nudge applies to a verified STORY and
    # names --include-req, so REQ rows are compared on those runs only.
    moved_from_approved = {i for i, _t, f, _s in calls if f == "approved"}
    compare = {p for p in _ROLE if p != "REQ" or (include_req and story_status == "verified")}
    nudged = {i for i in lint_nudged if art_lib.get_prefix_from_id(i) in compare}
    moved = {i for i in moved_from_approved if art_lib.get_prefix_from_id(i) in compare}
    assert nudged == moved, (story_status, include_req, sorted(nudged), sorted(moved), out)
    assert not (code == 0 and "✗" in out), out
    if not include_req:
        assert not [c for c in calls if c[1] == "requirement"], out
    if unverified_sibling:
        assert not [c for c in calls if c[3] == "verified"], out


def test_status_cascade_lint_shares_the_cascade_decision():
    """The lint nudges through cascade_targets, the function plan_cascade
    acts on; no role set or prefix list of its own (STORY-697 AC3)."""
    import inspect

    src = inspect.getsource(lint_cmd._check_status_cascade)
    assert "cascade_targets(" in src
    assert "CASCADE_ROLES" not in src and '("ARCH", "DDD")' not in src
    assert "cascade_targets(" in inspect.getsource(cascade_cmd.plan_cascade)


@pytest.mark.parametrize("prefix", sorted(_ROLE))
@pytest.mark.parametrize("role", sorted(_schema("story")["allowed_link_roles"]))
def test_lint_nudge_agrees_with_cascade_for_every_story_link_role(tmp_path, monkeypatch,
                                                                  prefix, role):
    """Every story link role x spec prefix: an approved spec is nudged by the
    lint iff cascade-status (with --include-req, STORY verified) moves it."""
    root = project(tmp_path)
    target = f"{prefix}-001"
    put(root, target, "approved")
    put(root, "STORY-001", "verified", [(target, role)])
    art_lib.rebuild_index(root)
    nudged = _lint_nudged(root, "STORY-001")
    calls = spy_updates(monkeypatch)

    run_cli(root, monkeypatch, "cascade-status", "STORY-001", "--include-req")

    moved = {i for i, _t, f, _s in calls if f == "approved"}
    assert nudged == moved, (prefix, role, nudged, moved)
    assert (target in moved) == cascade_cmd.cascades_through(prefix, role)


@pytest.mark.parametrize("prefix", ["REQ", "ARCH", "DDD"])
def test_cascade_roles_are_legal_story_link_roles(prefix):
    story_roles = set(_schema("story")["allowed_link_roles"])
    roles = cascade_cmd.CASCADE_ROLES[prefix]
    assert roles and set(roles) <= story_roles


def test_planned_steps_are_legal_for_every_real_schema_pair():
    # Pure planner over (type, from, goal) for every status pair the schema knows.
    for prefix in ("REQ", "ARCH", "DDD"):
        amap = _schema(PREFIX_TYPE[prefix])["allowed_status"]
        for frm, goal in itertools.product(amap, ["implemented", "verified"]):
            steps = cascade_cmd.legal_walk(amap, frm, goal)
            if steps is None:
                continue
            prev = frm
            for step in steps:
                assert prev in amap[step], (prefix, frm, goal, steps)
                prev = step
