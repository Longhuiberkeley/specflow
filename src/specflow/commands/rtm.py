"""specflow rtm — bidirectional requirements-traceability matrix.

SpecFlow already computes traceability two ways: `commands/trace.py` walks a
single artifact's chain, and `commands/status.py` aggregates coverage
percentages. Neither renders the full REQ -> ARCH/STORY -> tests matrix. This
reuses the same link-walking convention already established there (and in
`lib/artifacts.py`'s `find_missing_v_pairs`): the artifact that *holds* the edge
(the decomposed child, or the verifying test) carries the link, pointing back
at its target — so finding "what verifies/decomposes X" means scanning every
other artifact for a link whose `target` is X.

No new link-role vocabulary is invented here (frozen per D-18). Decomposition
uses the schema-allowed roles `derives_from`/`refined_by` (DEC-032 made
`derives_from` canonical for ARCH, but older DDD links still use `refined_by`
in the wild — both are accepted rather than silently "fixed"). Verification
uses `verified_by` (test -> spec) and STORY implementation uses `implements`
(STORY -> REQ), exactly as `status.py`'s coverage math already assumes.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from specflow.lib import artifacts as art_lib
from specflow.lib.display import RED, GREEN, YELLOW, BOLD, DIM, NC

_DECOMPOSE_ROLES = {"derives_from", "refined_by"}


def _children_of(
    parent_id: str,
    child_type: str,
    roles: set[str],
    artifacts: list[art_lib.Artifact],
) -> list[art_lib.Artifact]:
    """Artifacts of `child_type` holding a link {target: parent_id, role in roles}."""
    out: list[art_lib.Artifact] = []
    for art in artifacts:
        if art.type != child_type:
            continue
        for link in art.links:
            if link.target == parent_id and link.role in roles:
                out.append(art)
                break
    return out


def _dedupe(arts: list[art_lib.Artifact]) -> list[art_lib.Artifact]:
    seen: set[str] = set()
    out: list[art_lib.Artifact] = []
    for a in arts:
        if a.id not in seen:
            seen.add(a.id)
            out.append(a)
    return out


def _row_for_req(req: art_lib.Artifact, artifacts: list[art_lib.Artifact]) -> dict[str, Any]:
    archs = _children_of(req.id, "architecture", _DECOMPOSE_ROLES, artifacts)
    stories = _children_of(req.id, "story", {"implements", "derives_from"}, artifacts)
    qts = _children_of(req.id, "qualification-test", {"verified_by"}, artifacts)

    tests = list(qts)
    for arch in archs:
        tests.extend(_children_of(arch.id, "integration-test", {"verified_by"}, artifacts))
        for ddd in _children_of(arch.id, "detailed-design", _DECOMPOSE_ROLES, artifacts):
            tests.extend(_children_of(ddd.id, "unit-test", {"verified_by"}, artifacts))
    tests = _dedupe(tests)

    gaps: list[str] = []
    if not archs:
        gaps.append("ARCH")
    if not stories:
        gaps.append("STORY")
    if not tests:
        gaps.append("tests")

    return {"req": req, "archs": archs, "stories": stories, "tests": tests, "gaps": gaps}


def _orphan_tests(artifacts: list[art_lib.Artifact]) -> list[art_lib.Artifact]:
    """Tests (UT/IT/QT) with no verified_by link to an existing artifact."""
    id_index = art_lib.build_id_index(artifacts)
    test_types = {"unit-test", "integration-test", "qualification-test"}
    orphans: list[art_lib.Artifact] = []
    for art in artifacts:
        if art.type not in test_types:
            continue
        verifies_something = any(
            link.role == "verified_by" and link.target in id_index
            for link in art.links
        )
        if not verifies_something:
            orphans.append(art)
    return orphans


def _ids(arts: list[art_lib.Artifact]) -> str:
    return ", ".join(a.id for a in arts)


def _render_table(rows: list[dict[str, Any]], orphans: list[art_lib.Artifact]) -> None:
    print(f"\n{BOLD}Requirements Traceability Matrix{NC}")

    if not rows:
        print(f"  {DIM}(no requirements matched){NC}\n")
    else:
        req_col = [f"{r['req'].id} ({r['req'].status})" for r in rows]
        arch_col = [_ids(r["archs"]) or "—" for r in rows]
        story_col = [_ids(r["stories"]) or "—" for r in rows]
        tests_col = [_ids(r["tests"]) or "—" for r in rows]

        w_req = max([len("REQ (status)")] + [len(s) for s in req_col])
        w_arch = max([len("ARCH")] + [len(s) for s in arch_col])
        w_story = max([len("STORY")] + [len(s) for s in story_col])
        w_tests = max([len("Tests")] + [len(s) for s in tests_col])

        header = (
            f"  {'REQ (status)':<{w_req}}  {'ARCH':<{w_arch}}  "
            f"{'STORY':<{w_story}}  {'Tests':<{w_tests}}  Gap"
        )
        print(header)
        print(f"  {'-' * (len(header) - 2)}")
        for i, r in enumerate(rows):
            gaps = r["gaps"]
            gap_str = ", ".join(gaps) if gaps else "OK"
            gap_color = YELLOW if gaps else GREEN
            print(
                f"  {req_col[i]:<{w_req}}  {arch_col[i]:<{w_arch}}  "
                f"{story_col[i]:<{w_story}}  {tests_col[i]:<{w_tests}}  "
                f"{gap_color}{gap_str}{NC}"
            )
        print()

    print(f"{BOLD}Orphan tests{NC} (verify nothing): {len(orphans)}")
    if orphans:
        print(f"  {_ids(orphans)}")
    print()


def _render_markdown(rows: list[dict[str, Any]], orphans: list[art_lib.Artifact]) -> None:
    print("| REQ | Status | ARCH | STORY | Tests | Gap |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        gaps = r["gaps"]
        gap_str = ", ".join(gaps) if gaps else "OK"
        print(
            f"| {r['req'].id} | {r['req'].status} | {_ids(r['archs']) or '—'} | "
            f"{_ids(r['stories']) or '—'} | {_ids(r['tests']) or '—'} | {gap_str} |"
        )
    print()
    print(f"**Orphan tests** (verify nothing): {len(orphans)}")
    if orphans:
        print(_ids(orphans))


def _render_csv(rows: list[dict[str, Any]], orphans: list[art_lib.Artifact]) -> None:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["req", "status", "arch", "story", "tests", "gap"])
    for r in rows:
        gaps = r["gaps"]
        writer.writerow(
            [
                r["req"].id,
                r["req"].status,
                _ids(r["archs"]),
                _ids(r["stories"]),
                _ids(r["tests"]),
                ", ".join(gaps) if gaps else "OK",
            ]
        )
    print(buf.getvalue().rstrip("\n"))
    print()
    print(f"orphan_tests,{len(orphans)}")
    if orphans:
        print(_ids(orphans))


def run(root: Path, args: dict[str, Any]) -> int:
    root = root.resolve()
    artifacts = art_lib.discover_artifacts(root)
    reqs = sorted((a for a in artifacts if a.type == "requirement"), key=lambda a: a.id)

    req_filter = (args.get("req") or "").strip()
    if req_filter:
        reqs = [r for r in reqs if r.id == req_filter]
        if not reqs:
            print(f"{RED}✗ REQ '{req_filter}' not found among discovered artifacts.{NC}")
            return 0

    rows = [_row_for_req(r, artifacts) for r in reqs]

    if args.get("gaps"):
        rows = [r for r in rows if r["gaps"]]

    orphans = _orphan_tests(artifacts)

    fmt = args.get("format") or "table"
    if fmt == "markdown":
        _render_markdown(rows, orphans)
    elif fmt == "csv":
        _render_csv(rows, orphans)
    else:
        _render_table(rows, orphans)

    return 0
