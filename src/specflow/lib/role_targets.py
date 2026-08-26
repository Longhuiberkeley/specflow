"""Role→target-type semantic matrix (accounting, not policing).

Schemas list allowed link *roles* per SOURCE type but never say anything
about the TARGET's type, so a structurally valid nonsense link (``implements``
→ a unit test, ``belongs_to`` → a REQ) is accepted silently. This module
supplies the missing target-type half, derived from the same frozen
type-pair semantics ``specflow.lib.artifacts`` uses for trace direction
(``_SPEC_LEVEL`` / ``_TEST_TYPES`` / ``_WORK_TO_SPEC_ROLES`` /
``_RESEARCH_PARENT_ROLES``) — one source of truth, the declared cousin of
the deferred chain-depth unification (v1.15.0 backlog).

Doctrine:

- **Accounting, never policing.** Findings are warnings surfaced by the
  dedicated ``artifact-lint --type role-target`` check; they are NOT part of
  ``check_schema`` and therefore never feed ``project-audit``'s consistency
  lens (which escalates unregistered warns to exit 2 and would break
  consumer release gates on upgrade). Opt-in ``lint.role_target_strict``
  escalates to blocking, mirroring ``compliance_evidence_strict``.
- **No cry-wolf.** Only direction-bearing roles with defensible semantics
  get rows. Annotation-ish roles (``refers_to``, ``informs``,
  ``addresses``, ``applies_to``, ``review_of``, ``exposes``…) and unknown
  source types emit nothing. Unresolvable targets (unknown prefix,
  standard-clause IDs like ``ISO-14971-4.2``) are exempt.
- Warnings collapse per artifact per role.
"""

from __future__ import annotations

from typing import Any

from specflow.lib.artifacts import Artifact, PREFIX_TO_TYPE

_TEST_TYPES = {"unit-test", "integration-test", "qualification-test"}
_SPEC_TYPES = {"requirement", "architecture", "detailed-design"}

# source_type -> role -> allowed target types. Roles/combos without a row are
# intentionally unjudged (see module docstring).
ROLE_TARGET_MATRIX: dict[str, dict[str, frozenset[str]]] = {
    # --- specs ---------------------------------------------------------
    "requirement": {
        # Canonical: the refining ARCH is downstream of the REQ (v1.14.2).
        "refined_by": frozenset({"architecture"}),
        # A spec naming its own verifiers (renders downstream).
        "verified_by": frozenset(_TEST_TYPES),
        "validated_by": frozenset(_TEST_TYPES | {"experiment"}),
        # complies_with targets standard clause IDs — exempt via _target_type,
        # never warned; artifact-shaped targets fall through to the row.
        "complies_with": frozenset(_SPEC_TYPES),
        "supersedes": frozenset(_SPEC_TYPES | {"best-practice", "finding"}),
        "derives_from": frozenset(
            _SPEC_TYPES
            | {"decision", "audit", "best-practice", "finding", "competition"}
        ),
    },
    "architecture": {
        # ARCH→ARCH refinement is a real decomposition shape in dogfood
        # (ARCH-025 refined_by ARCH-023); equal-level targets render
        # not-downstream but the link itself is legal.
        "refined_by": frozenset({"detailed-design", "architecture"}),
        "verified_by": frozenset(_TEST_TYPES),
        "complies_with": frozenset(_SPEC_TYPES),
        "supersedes": frozenset(_SPEC_TYPES | {"best-practice", "finding"}),
        "derives_from": frozenset(
            _SPEC_TYPES
            | {"decision", "audit", "best-practice", "finding", "competition"}
        ),
        # guided_by on a spec points at a decision that shaped it.
        "guided_by": frozenset({"decision", "best-practice"}),
    },
    "detailed-design": {
        # Legacy concrete→abstract shape stays legal (v1.14.2 direction fix).
        "refined_by": frozenset({"architecture"}),
        "verified_by": frozenset(_TEST_TYPES),
        "complies_with": frozenset(_SPEC_TYPES),
        "supersedes": frozenset(_SPEC_TYPES | {"best-practice", "finding"}),
        "derives_from": frozenset(
            _SPEC_TYPES
            | {"decision", "audit", "best-practice", "finding", "competition"}
        ),
        "specified_by": frozenset({"architecture", "requirement"}),
        "guided_by": frozenset({"decision", "best-practice"}),
    },
    # --- work ------------------------------------------------------------
    "story": {
        "implements": frozenset(_SPEC_TYPES),
        "specified_by": frozenset({"architecture", "detailed-design"}),
        "guided_by": frozenset(
            {"decision", "best-practice"} | _SPEC_TYPES | {"competition"}
        ),
        "verified_by": frozenset(_TEST_TYPES),
        "depends_on": frozenset({"story", "spike", "experiment"}),
        "derives_from": frozenset(
            _SPEC_TYPES
            | {"decision", "spike", "finding", "competition", "audit"}
        ),
    },
    "spike": {
        "guided_by": frozenset({"decision", "best-practice"} | _SPEC_TYPES),
        "derives_from": frozenset(_SPEC_TYPES | {"decision", "finding", "audit"}),
    },
    "decision": {
        "derives_from": frozenset(
            _SPEC_TYPES | {"audit", "review", "decision", "finding", "challenge"}
        ),
    },
    "defect": {
        "fails_to_meet": frozenset(_SPEC_TYPES),
        "derives_from": frozenset(_SPEC_TYPES | {"decision", "finding", "audit"}),
    },
    # --- tests (both legal verified_by shapes) -----------------------------
    "unit-test": {
        "verified_by": frozenset({"story"} | _SPEC_TYPES),
        "derives_from": frozenset(_SPEC_TYPES | {"detailed-design"}),
    },
    "integration-test": {
        "verified_by": frozenset({"story"} | _SPEC_TYPES),
        "derives_from": frozenset(_SPEC_TYPES),
    },
    "qualification-test": {
        "verified_by": frozenset({"story"} | _SPEC_TYPES),
        "derives_from": frozenset(_SPEC_TYPES),
    },
    # --- research hierarchy -------------------------------------------------
    "competition": {
        "operates_on": frozenset({"competition"}),
        "guided_by": frozenset({"decision", "best-practice"} | _SPEC_TYPES),
        "derives_from": frozenset(_SPEC_TYPES | {"decision", "finding", "audit"}),
    },
    "loop": {
        "derives_from": frozenset({"competition", "finding", "decision", "audit"}),
    },
    "experiment": {
        "belongs_to": frozenset({"loop", "competition", "experiment"}),
        "derives_from": frozenset({"finding", "loop", "decision"}),
    },
    "finding": {
        "belongs_to": frozenset({"loop", "competition", "experiment"}),
        "condenses": frozenset({"loop", "experiment"}),
        "validated_by": frozenset({"experiment"} | _TEST_TYPES),
        "supersedes": frozenset({"finding", "best-practice"} | _SPEC_TYPES),
        "derives_from": frozenset(
            _SPEC_TYPES | {"decision", "experiment", "loop", "competition", "audit"}
        ),
    },
    # --- ops ------------------------------------------------------------------
    "run": {
        "implements": frozenset(_SPEC_TYPES),
        "complies_with": frozenset(_SPEC_TYPES),
        "guided_by": frozenset({"decision", "best-practice"} | _SPEC_TYPES),
        "derives_from": frozenset(
            _SPEC_TYPES | {"experiment", "finding", "decision", "run"}
        ),
    },
    "monitor": {
        "belongs_to": frozenset({"run", "monitor"}),
        "derives_from": frozenset({"run", "finding", "decision"}),
    },
}

# Roles that legally target standard-clause IDs (not artifacts). When the
# target is clause-shaped (unregistered prefix), these never warn.
_CLAUSE_EXEMPT_ROLES = {"complies_with", "addresses", "applies_to"}


def _target_type(target: str, id_types: dict[str, str]) -> str | None:
    """Resolve a link target to a canonical type; None when unresolvable.

    Clause-shaped targets (``ISO-14971-4.2`` — token before '-'/'.' is not a
    registered artifact prefix) and unknown prefixes return None so they can
    never cry-wolf.
    """
    if not target:
        return None
    hit = id_types.get(target)
    if hit:
        return hit
    head = target.split("-")[0].split(".")[0].upper()
    if head not in PREFIX_TO_TYPE:
        return None
    return PREFIX_TO_TYPE[head]


def check_role_targets(
    artifacts: list[Artifact],
    strict: bool = False,
) -> list[dict[str, str]]:
    """Warn when a direction-bearing link points at a semantically wrong type.

    Returns a list of issues (``severity`` warning, or blocking under strict)
    collapsed per artifact per role. Purely a read pass; never mutates.
    """
    id_types: dict[str, str] = {a.id: a.type for a in artifacts if a.id and a.type}
    issues: list[dict[str, str]] = []

    for art in artifacts:
        rows = ROLE_TARGET_MATRIX.get(art.type)
        if not rows:
            continue
        bad: dict[str, list[str]] = {}
        for link in art.links:
            allowed = rows.get(link.role)
            if allowed is None:
                continue
            ttype = _target_type(link.target, id_types)
            if ttype is None:
                # Clause-shaped / unresolvable: exempt (never cry-wolf).
                continue
            if ttype not in allowed:
                bad.setdefault(link.role, []).append(link.target)
        for role, targets in sorted(bad.items()):
            allowed = rows[role]
            issues.append(
                {
                    "severity": "blocking" if strict else "warning",
                    "message": (
                        f'[{art.id}] role "{role}" points at '
                        f"{', '.join(targets[:3])}"
                        f"{' …' if len(targets) > 3 else ''} "
                        f"(allowed target types: {', '.join(sorted(allowed))})"
                    ),
                    "code": "role_target",
                    "role": role,
                }
            )
    return issues


def advisory_for_links(
    artifact_type: str,
    links: list[dict[str, Any]] | None,
    id_types: dict[str, str],
) -> list[str]:
    """Human-facing advisory lines for freshly written links (create/update).

    Same semantics as :func:`check_role_targets` but returns printable hints
    instead of issue dicts — advisory, never blocks the write.
    """
    rows = ROLE_TARGET_MATRIX.get(artifact_type)
    if not rows or not links:
        return []
    hints: list[str] = []
    for link in links:
        role = link.get("role", "")
        target = link.get("target", "")
        allowed = rows.get(role)
        if allowed is None:
            continue
        ttype = _target_type(target, id_types)
        if ttype is None or ttype in allowed:
            continue
        hints.append(
            f'⚠ link "{target}:{role}" is unusual for type "{artifact_type}" '
            f"(role \"{role}\" expects target types: {', '.join(sorted(allowed))}); "
            f"kept as written — see `specflow artifact-lint --type role-target`"
        )
    return hints


def advisory_for_entries(
    artifact_type: str,
    entries: list[dict[str, Any]],
) -> list[str]:
    """Advisory shortcut: prefix-resolved targets, no artifact inventory."""
    return advisory_for_links(artifact_type, entries, {})
