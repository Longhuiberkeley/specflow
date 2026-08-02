"""Deterministic risk-tier computation for a change set (v1.13.1).

Accounting, not policing: :func:`compute_risk_tier` derives a *minimum* risk
tier from the intrinsic properties of a change set and returns it together with
machine-readable ``reasons``. The tier is RECORDED (onto a DEC ``risk_profile``
and shown by ``specflow risk-tier``); it GATES NOTHING in code. No transition,
status change, commit hook, or release path imports or consults this module —
the host agent (or a human) may freely escalate above the floor; downgrading
below it requires a recorded justification on the DEC.

Deterministic only, zero external LLM calls. ``confidence`` is deliberately NOT
computed here — confidence is the host agent's own judgment, which SpecFlow
never calls an LLM to produce. The deterministic subset (tier / reversibility /
blast_radius_count) is what auto change-records populate; ``confidence`` is left
empty for a human-authored DEC to fill via ``--set``.

Reversibility floor (IRREVERSIBLE) — fires when ANY of these intrinsic
properties is present in the change set (the irreversibility lexicon):

  - ``status-verified``: a changed artifact sits in ``verified``/``released``
    (a one-way door — the verification claim is now part of the record).
  - ``supersedes-link``: a changed artifact carries a ``supersedes`` link role
    (it retires another artifact — retiring is not locally undoable).
  - ``deletion``: a change id is no longer in the artifact graph.
  - ``tag-destructive`` / ``tag-data-migration``: a changed artifact carries a
    ``destructive`` or ``data-migration`` tag.
  - ``baseline-or-release``: the commit context indicates a baseline create /
    tag / release action (only knowable when ``commit_subject`` is passed, e.g.
    from ``document-changes``; a standalone ``risk-tier`` query is honest about
    not seeing this).

Blast radius reuses the existing deterministic cone idiom — the same in-memory
``id_index`` link walk that ``artifacts.compute_chain_depth`` and
``impact._find_all_downstream_recursive`` traverse (link.target == current).
``query_reverse_impact`` solves a different question (source-file → governing
artifact via ``output_files``) and is not reimplemented here; for artifact-ID
change sets the link-graph BFS below is the correct cone. ``blast_radius_count``
is the number of distinct downstream artifacts (the change set itself excluded).
``LARGE_CONE_THRESHOLD`` (≥ 8) → "large".

Tier assignment (defaults UP when uncertain — over-flooring costs one human
glance, under-flooring is the expensive mistake):

  - Tier 2 — ``irreversible`` OR ``large`` blast radius.
  - Tier 1 — classifiable but moderate (reversible, small non-zero cone), AND
    the default-up tier for an unclassifiable change set.
  - Tier 0 — reversible, small, AND zero downstream cone (genuinely isolated).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from specflow.lib import artifacts as art_lib


__all__ = ["compute_risk_tier", "LARGE_CONE_THRESHOLD"]


# Cone size at which blast radius is "large". Picked at 8: below this a change
# touches a bounded local cluster; at/above it the impact spans multiple
# components and warrants Tier 2 attention. Documented, not tuned per project.
LARGE_CONE_THRESHOLD = 8

# Statuses that mark a one-way door: the artifact has crossed into a verified /
# released state, which is not locally reversible (the claim is now on record).
_IRREVERSIBLE_STATUSES = {"verified", "released"}

# Tags that mark an intrinsically destructive / one-way-door change.
_IRREVERSIBLE_TAGS = {"destructive", "data-migration"}

# Commit-subject patterns that indicate a baseline create / tag / release
# action. Only consulted when document-changes passes ``commit_subject`` — a
# standalone ``risk-tier`` query honestly does not see the commit context.
_RELEASE_SUBJECT_RE = re.compile(
    r"(?:^|[\s:])(release|baseline|tag|ship)\b|v\d+\.\d+\.\d+",
    re.IGNORECASE,
)


def _downstream_cone(
    change_ids: list[str],
    id_index: dict[str, art_lib.Artifact],
) -> set[str]:
    """Transitive downstream cone of *change_ids* over the link graph.

    Reuses the ``id_index`` + ``link.target == current`` walk idiom shared with
    ``artifacts.compute_chain_depth`` (same graph; here we collect the full
    closure rather than only the deepest single path). The change set itself is
    excluded — blast radius counts *other* affected artifacts.
    """
    visited: set[str] = set(change_ids)
    queue: list[str] = list(change_ids)
    cone: set[str] = set()
    while queue:
        current = queue.pop(0)
        for art_id, art in id_index.items():
            if art_id in visited:
                continue
            for link in art.links:
                if link.target == current:
                    visited.add(art_id)
                    cone.add(art_id)
                    queue.append(art_id)
                    break
    return cone


def compute_risk_tier(
    change_ids: list[str],
    artifacts: list[art_lib.Artifact],
    root: Path,
    *,
    commit_subject: str | None = None,
) -> dict[str, Any]:
    """Compute the deterministic minimum risk tier for a change set.

    Args:
        change_ids: Artifact IDs in the change set.
        artifacts: All project artifacts (already discovered).
        root: Project root (reserved for future filesystem signals; currently
            unused so the function is a pure graph query).
        commit_subject: Optional commit subject (e.g. from ``document-changes``)
            used to detect a baseline/tag/release action. A standalone
            ``risk-tier`` query omits this and is honest about not seeing it.

    Returns:
        ``{tier, reversibility, blast_radius_count, reasons}`` where:
          - ``tier``: int 0 (light) / 1 (normal) / 2 (stop).
          - ``reversibility``: ``"irreversible"`` or ``"reversible"``.
          - ``blast_radius_count``: int (distinct downstream artifacts).
          - ``reasons``: list[str], each naming a trigger that fired.
    """
    id_index = art_lib.build_id_index(artifacts)
    reasons: list[str] = []

    resolved = [id_index[cid] for cid in change_ids if cid in id_index]
    missing = [cid for cid in change_ids if cid not in id_index]

    # ── Reversibility floor ───────────────────────────────────────
    irreversible = False

    for art in resolved:
        if art.status in _IRREVERSIBLE_STATUSES:
            irreversible = True
            reasons.append(
                f"status-{art.status} ({art.id} is {art.status} — one-way door)"
            )
        for link in art.links:
            if link.role == "supersedes":
                irreversible = True
                reasons.append(
                    f"supersedes-link ({art.id} supersedes {link.target})"
                )
        for tag in (art.tags or []):
            if tag in _IRREVERSIBLE_TAGS:
                irreversible = True
                reasons.append(f"tag-{tag} ({art.id} tagged {tag})")

    for cid in missing:
        irreversible = True
        reasons.append(f"deletion ({cid} no longer in the artifact graph)")

    if commit_subject and _RELEASE_SUBJECT_RE.search(commit_subject):
        irreversible = True
        reasons.append(
            f"baseline-or-release (commit subject indicates a release/baseline: "
            f"{commit_subject.strip()[:60]!r})"
        )

    # ── Blast radius (downstream cone) ────────────────────────────
    cone = _downstream_cone(list(change_ids), id_index)
    blast_radius_count = len(cone)
    large = blast_radius_count >= LARGE_CONE_THRESHOLD
    if large:
        reasons.append(
            f"large-blast-radius (cone={blast_radius_count} "
            f">= {LARGE_CONE_THRESHOLD})"
        )

    # ── Tier assignment (defaults UP when unclassifiable) ─────────
    classifiable = bool(resolved) or bool(missing)
    if not classifiable:
        # No artifacts resolved and nothing flagged as deleted — we honestly
        # cannot classify. Default UP to Tier 1 so a glance happens.
        tier = 1
        reversibility = "reversible"
        reasons.append(
            "unclassifiable (no artifacts resolved for the change set; "
            "defaulted up to Tier 1)"
        )
        return {
            "tier": tier,
            "reversibility": reversibility,
            "blast_radius_count": blast_radius_count,
            "reasons": reasons,
        }

    if irreversible or large:
        tier = 2
    elif blast_radius_count == 0:
        tier = 0
    else:
        tier = 1

    reversibility = "irreversible" if irreversible else "reversible"

    return {
        "tier": tier,
        "reversibility": reversibility,
        "blast_radius_count": blast_radius_count,
        "reasons": reasons,
    }


def verification_evidence(
    change_ids: list[str],
    artifacts: list[art_lib.Artifact],
) -> str:
    """Aggregate verification-contract evidence across a change set's tests.

    For the change set, gather linked UT/IT/QT (tests in the set, plus tests
    that link to any set member via ``verified_by``), then summarize the
    ``verify_run_*`` evidence (shipped v1.13.0) as one honest line:

      - ``ran (N green)`` — at least one contract ran and matched its expected
        exit code; N is the green count.
      - ``not-run`` — contracts are declared but none have recorded a green run.
      - ``unknown (no contracts declared)`` — no contracts in scope (the honest
        pre-adoption state). Never fabricated.
    """
    id_index = art_lib.build_id_index(artifacts)
    change_set = set(change_ids)

    # Tests in the change set itself, plus tests linking to any change-set
    # member via verified_by (the V-model verification wire).
    test_types = {"unit-test", "integration-test", "qualification-test"}
    linked_tests: list[art_lib.Artifact] = []
    seen_test_ids: set[str] = set()
    for art in artifacts:
        is_test = art.type in test_types
        in_set = art.id in change_set
        links_to_set = any(
            lk.role == "verified_by" and lk.target in change_set
            for lk in art.links
        )
        if (is_test and in_set) or links_to_set:
            if art.id not in seen_test_ids:
                seen_test_ids.add(art.id)
                linked_tests.append(art)

    contracts = [t for t in linked_tests if t.frontmatter.get("verify_command")]
    if not contracts:
        return "unknown (no contracts declared)"

    def _is_green(art: art_lib.Artifact) -> bool:
        ran_at = art.frontmatter.get("verify_run_at")
        if not ran_at:
            return False
        expected = art.frontmatter.get("verify_exit_code", 0)
        recorded = art.frontmatter.get("verify_run_exit_code")
        if recorded is None:
            return False
        return str(expected) == str(recorded)

    green = sum(1 for t in contracts if _is_green(t))
    if green > 0:
        return f"ran ({green} green)"
    return "not-run"
