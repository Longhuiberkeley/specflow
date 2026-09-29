"""CLI handler for 'specflow cascade-status' — cascade STORY status to linked specs.

Every write is a single edge of the target type's ``allowed_status`` map
(DEC-093, STORY-697): a spec moves approved → implemented → verified one
legal step at a time, or the cascade refuses it with the reason. A REQ/ARCH/
DDD is promoted to ``verified`` only when every non-terminal STORY linked to
it through a cascade role is verified (closure rule). The command exits
non-zero when any proposed transition is refused or fails.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from specflow.lib import artifacts as art_lib
from specflow.lib.display import GREEN, RED, YELLOW, NC

# The link roles through which a STORY's status cascades to a spec, keyed by
# the spec's id prefix. Shared with artifact-lint's status-cascade check so
# the lint nudges exactly the links this command acts on (STORY-697 AC3).
CASCADE_ROLES: dict[str, frozenset[str]] = {
    "ARCH": frozenset({"guided_by"}),
    "DDD": frozenset({"specified_by"}),
    "REQ": frozenset({"implements", "derives_from"}),
}

# The forward lifecycle a cascade may walk. draft → approved is an approval
# gate, so a cascade never starts below ``approved``.
FORWARD_CHAIN: tuple[str, ...] = ("approved", "implemented", "verified")

# Statuses that take an artifact out of the lifecycle: never cascaded, and a
# STORY in one of them does not block a sibling's closure.
TERMINAL_STATUSES = frozenset({"deprecated", "superseded", "cancelled"})


def cascades_through(prefix: str, role: str) -> bool:
    """True when a STORY link with ``role`` to a ``prefix`` spec cascades status."""
    return role in CASCADE_ROLES.get(prefix, frozenset())


def cascade_targets(
    story: art_lib.Artifact,
    id_index: dict[str, art_lib.Artifact],
    include_req: bool,
) -> list[tuple[art_lib.Artifact, str]]:
    """The specs ``story``'s status cascades to, as (target, prefix), deduplicated.

    THE decision of which links cascade: plan_cascade acts on exactly these
    and artifact-lint's status-cascade check nudges exactly these (STORY-697
    AC3, tests/test_cascade_legality_table.py). REQ targets are included only
    with ``include_req``.
    """
    out: list[tuple[art_lib.Artifact, str]] = []
    seen: set[str] = set()
    for link in story.links:
        target = id_index.get(link.target)
        if target is None or target.id in seen:
            continue
        prefix = art_lib.get_prefix_from_id(target.id)
        if not cascades_through(prefix, link.role):
            continue
        if prefix == "REQ" and not include_req:
            continue
        seen.add(target.id)
        out.append((target, prefix))
    return out


def legal_walk(allowed_status: dict[str, list[str]], current: str, goal: str) -> list[str] | None:
    """The schema-legal steps from ``current`` to ``goal`` along FORWARD_CHAIN.

    ``[]`` when ``current`` is already at or beyond ``goal``; ``None`` when no
    legal walk exists (``current`` or ``goal`` is off the forward chain, or a
    step is not an edge of ``allowed_status``).
    """
    if current not in FORWARD_CHAIN or goal not in FORWARD_CHAIN:
        return None
    i, j = FORWARD_CHAIN.index(current), FORWARD_CHAIN.index(goal)
    if i >= j:
        return []
    steps: list[str] = []
    prev = current
    for status in FORWARD_CHAIN[i + 1:j + 1]:
        if prev not in (allowed_status.get(status) or []):
            return None
        steps.append(status)
        prev = status
    return steps


@dataclass
class Proposal:
    target_id: str
    prefix: str
    current: str
    steps: list[str] = field(default_factory=list)
    note: str = ""        # hold/skip explanation
    refused: str = ""     # non-empty → the cascade refuses this target


def _schema_map(root: Path, prefix: str) -> dict[str, list[str]] | None:
    art_type = art_lib.PREFIX_TO_TYPE.get(prefix, "")
    schema = art_lib._read_schema(root / ".specflow" / "schema", art_type)
    if not schema:
        return None
    amap = schema.get("allowed_status")
    return amap if isinstance(amap, dict) else None


def _unverified_siblings(target_id: str, prefix: str, stories: list[art_lib.Artifact]) -> list[art_lib.Artifact]:
    out = []
    for s in stories:
        if s.status == "verified" or s.status in TERMINAL_STATUSES:
            continue
        if any(ln.target == target_id and cascades_through(prefix, ln.role) for ln in s.links):
            out.append(s)
    return out


def plan_cascade(
    root: Path,
    story: art_lib.Artifact,
    all_artifacts: list[art_lib.Artifact],
    include_req: bool,
) -> list[Proposal]:
    """Propose, per linked spec, the legal walk the cascade will perform."""
    id_index = art_lib.build_id_index(all_artifacts)
    stories = [a for a in all_artifacts if art_lib.get_prefix_from_id(a.id) == "STORY"]
    wants_verified = story.status == "verified" and include_req

    proposals: list[Proposal] = []
    for target, prefix in cascade_targets(story, id_index, include_req):
        p = Proposal(target.id, prefix, target.status)
        proposals.append(p)

        goal = "verified" if wants_verified else "implemented"
        if goal == "verified":
            blockers = _unverified_siblings(target.id, prefix, stories)
            if blockers:
                goal = "implemented"
                names = ", ".join(f"{s.id} is '{s.status}'" for s in blockers)
                p.note = f"held (not verified): {names}; verified needs every linked STORY verified"

        if target.status in TERMINAL_STATUSES:
            p.note = f"'{target.status}' is terminal; not cascaded"
            continue
        if target.status not in FORWARD_CHAIN:
            p.refused = (f"'{target.status}' is not approved; approve it before cascading "
                         f"(run `specflow transitions {target.id}`)")
            continue
        amap = _schema_map(root, prefix)
        if amap is None:
            p.refused = f"no allowed_status map for type '{target.type}'; legality cannot be checked"
            continue
        steps = legal_walk(amap, target.status, goal)
        if steps is None:
            p.refused = (f"no legal walk from '{target.status}' to '{goal}' in the "
                         f"{target.type} schema (run `specflow transitions {target.id}`)")
            continue
        p.steps = steps
        if not steps and not p.note:
            p.note = f"already at or beyond {goal}"
    return proposals


def run(root: Path, args: dict[str, Any]) -> int:
    """Cascade STORY status to linked ARCH/DDD (and optionally REQ) artifacts."""
    artifact_id = args.get("artifact_id", "")
    include_req = args.get("include_req", False)
    dry_run = args.get("dry_run", False)

    if not artifact_id:
        print(f"{YELLOW}No artifact ID provided{NC}")
        return 1

    prefix = art_lib.get_prefix_from_id(artifact_id)
    if prefix != "STORY":
        print(f"{YELLOW}cascade-status only applies to STORY artifacts (got {artifact_id}){NC}")
        return 1

    file_path = art_lib.resolve_link_target(root, artifact_id)
    if file_path is None:
        print(f"{YELLOW}Artifact not found: {artifact_id}{NC}")
        return 1

    story = art_lib.parse_artifact(file_path)
    if story is None:
        print(f"{YELLOW}Cannot parse artifact: {artifact_id}{NC}")
        return 1

    if story.status not in ("implemented", "verified"):
        print(f"{YELLOW}{artifact_id} is '{story.status}' (cascade only applies to implemented/verified){NC}")
        return 0

    proposals = plan_cascade(root, story, art_lib.discover_artifacts(root), include_req)
    if not proposals:
        scope = "ARCH/DDD/REQ" if include_req else "ARCH/DDD"
        print(f"{GREEN}{artifact_id}: no linked {scope} specs found to cascade{NC}")
        return 0

    failed = 0
    print(f"\n{GREEN}Cascade from {artifact_id} ({story.status}):{NC}")
    for p in proposals:
        label = f"{p.target_id} ({p.prefix})"
        if p.refused:
            failed += 1
            print(f"  {RED}✗{NC} {label}: refused: {p.refused}")
            continue
        if p.steps:
            walk = " → ".join([p.current] + p.steps)
            if dry_run:
                print(f"  {label}: {walk} [dry-run]")
            else:
                reached = p.current
                for step in p.steps:
                    result = art_lib.update_artifact(root, p.target_id, status=step)
                    if not result.get("ok"):
                        failed += 1
                        print(f"  {RED}✗{NC} {label}: {reached} → {step} failed — "
                              f"{result.get('error', 'update failed')}")
                        break
                    reached = step
                else:
                    print(f"  {GREEN}✓{NC} {label}: {walk}")
        if p.note:
            mark = YELLOW + "⚠" + NC if p.note.startswith("held") else "·"
            print(f"  {mark} {label}: {p.current if not p.steps else p.steps[-1]} — {p.note}")

    if failed:
        print(f"{RED}{failed} cascade transition(s) refused or failed{NC}")
        return 1
    return 0
