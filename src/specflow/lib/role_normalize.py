"""Canonical link-role normalization.

SpecFlow keeps its link-role vocabulary deliberately small and behavior-paired
(see docs/decisions.md, "frozen relationship vocabulary"). When an artifact uses
a role outside its schema's ``allowed_link_roles``, the linter does **not** reject
it — unknown roles are a warning, never a blocker (accounting, not policing). This
module turns that bare warning into an actionable, direction-aware suggestion so
drift gets *named and corrected* instead of silently accumulating.

Three kinds of near-miss are recognized:

- ``synonym``   — a differently-worded role that maps to a canonical one in the
  same direction (e.g. ``validates`` -> ``validated_by``).
- ``inverse``   — the reverse of a canonical role. SpecFlow stores each edge once
  and queries it both ways via ``specflow trace``, so the fix is to author the
  canonical role on the *other* artifact, not to invent an inverse role
  (e.g. ``superseded_by`` -> author ``supersedes`` on the successor).
- ``lifecycle`` — a state change masquerading as a relationship. Termination and
  deprecation are statuses, not links (e.g. ``cancels`` -> set ``status: cancelled``).

Adding a new *canonical* role is a deliberate, behavior-paired decision — this
module only maps near-misses onto roles that already exist in the schemas. Not
every canonical role has a bespoke consumer: roles are also normalization targets
and remain traversable by ``specflow trace``'s generic walk, so a role with no
dedicated query is not automatically "dead vocabulary" (``executes`` is the one
known-inert role — a cleanup candidate, not a design flaw).
"""

from __future__ import annotations

from dataclasses import dataclass


__all__ = ["Suggestion", "suggest_canonical"]


@dataclass(frozen=True)
class Suggestion:
    """A normalization hint for a non-canonical link role.

    Attributes:
        target: the canonical role (synonym/inverse) or status value (lifecycle).
        kind: one of ``"synonym"``, ``"inverse"``, ``"lifecycle"``.
        hint: human-readable guidance, ready to append to a lint message.
    """

    target: str
    kind: str
    hint: str


# Same-direction synonyms: alias -> canonical role.
_SYNONYMS: dict[str, str] = {
    "validates": "validated_by",
    "tests": "verified_by",
    "verifies": "verified_by",
    "feeds": "informs",
    "evidence_for": "derives_from",
    "findings_for": "derives_from",
    "informed_by": "derives_from",
    "amends": "refined_by",
    "revises": "refined_by",
    "extends": "refined_by",
    "requires": "depends_on",
    "mandates": "derives_from",
    "mandated_by": "derives_from",
    "guides": "guided_by",
    "specifies": "specified_by",
    "applies": "applies_to",
    "replaces": "supersedes",
    "supersede": "supersedes",
}

# Inverse roles: alias -> canonical role to author on the OTHER artifact.
_INVERSES: dict[str, str] = {
    "superseded_by": "supersedes",
    "superceded_by": "supersedes",
    "derives": "derives_from",
    "derived_into": "derives_from",
    "produces": "derives_from",
    "refines": "refined_by",
    "implemented_by": "implements",
}

# Lifecycle "roles" that are really status transitions: alias -> status value.
_LIFECYCLE: dict[str, str] = {
    "cancels": "cancelled",
    "cancelled_by": "cancelled",
    "withdraws": "cancelled",
    "deprecates": "deprecated",
    "deprecated_by": "deprecated",
    "obsoletes": "deprecated",
}


def suggest_canonical(role: str) -> Suggestion | None:
    """Return a normalization Suggestion for a non-canonical role, or None.

    The lookup is case-insensitive and tolerant of surrounding whitespace. Buckets
    are checked lifecycle -> inverse -> synonym so the most consequential
    correction (a status change) is surfaced first.
    """
    if not role:
        return None
    key = role.strip().lower()
    if not key:
        return None

    if key in _LIFECYCLE:
        status = _LIFECYCLE[key]
        return Suggestion(
            target=status,
            kind="lifecycle",
            hint=(
                f'this is a lifecycle change, not a link — set "status: {status}" '
                "on the artifact instead of a relationship role"
            ),
        )

    if key in _INVERSES:
        canonical = _INVERSES[key]
        return Suggestion(
            target=canonical,
            kind="inverse",
            hint=(
                f'"{canonical}" is the inverse — author it on the target artifact, '
                "or just query backlinks with `specflow trace <ID>` (links are "
                "stored once and traversed both ways)"
            ),
        )

    if key in _SYNONYMS:
        canonical = _SYNONYMS[key]
        return Suggestion(
            target=canonical,
            kind="synonym",
            hint=f'did you mean "{canonical}"?',
        )

    return None
