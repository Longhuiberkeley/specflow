"""Shared best-practice anatomy and applicability primitives."""

from __future__ import annotations

import re
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from specflow.lib import artifacts as art_lib

PRACTICE_SECTIONS = (
    "Practice",
    "Applies when",
    "Work products",
    "Verification",
    "Rationale",
)

PROVENANCE_VALUES = frozenset({"bundled", "standard", "synthesized", "learned"})
STRENGTH_VALUES = frozenset({"mandatory", "recommended", "neutral", "informal"})
VERIFICATION_METHODS = frozenset({"test", "inspection", "analysis", "demonstration"})

_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_LEGACY_BP_STATUS_MAP = {
    "draft": [],
    "approved": ["draft"],
    "active": ["approved"],
    "superseded": ["active"],
}


def render_practice_body(
    practice: str,
    applies_when: str,
    work_products: str,
    verification: str,
    rationale: str,
) -> str:
    """Render the normative five-section BP body in its canonical order."""
    values = (practice, applies_when, work_products, verification, rationale)
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("all five best-practice sections need non-empty text")
    return "\n\n".join(
        f"## {heading}\n\n{value.strip()}"
        for heading, value in zip(PRACTICE_SECTIONS, values)
    ) + "\n"


def validate_anatomy(body: str) -> list[str]:
    """Return deterministic anatomy problems, in canonical section order."""
    headings = [match.group(1).strip() for match in _SECTION_RE.finditer(body or "")]
    positions: list[int] = []
    problems: list[str] = []
    for section in PRACTICE_SECTIONS:
        matches = [index for index, heading in enumerate(headings) if heading == section]
        if not matches:
            problems.append(f"missing section '{section}'")
        elif len(matches) > 1:
            problems.append(f"duplicate section '{section}'")
        else:
            positions.append(matches[0])
    if len(positions) == len(PRACTICE_SECTIONS) and positions != sorted(positions):
        problems.append("sections are not in canonical order")

    # A required heading with no body text is structurally present but unusable.
    for match in _SECTION_RE.finditer(body or ""):
        heading = match.group(1).strip()
        if heading not in PRACTICE_SECTIONS:
            continue
        content_start = match.end()
        next_heading = _SECTION_RE.search(body, content_start)
        content_end = next_heading.start() if next_heading else len(body)
        if not body[content_start:content_end].strip():
            problems.append(f"section '{heading}' is empty")
    return problems


def status_is_valid(schema: dict[str, Any], status: str) -> bool:
    """Accept active BP records as transition-only legacy statuses.

    The lifecycle no longer has an ``active`` node. The approved transition
    retains ``active`` as a predecessor so pre-migration artifacts and their
    supersession edges remain lintable while they are migrated.
    """
    allowed = schema.get("allowed_status", {})
    if status in allowed:
        return True
    if schema.get("type") != "best-practice" or not isinstance(allowed, dict):
        return False
    return status in {
        predecessor
        for values in allowed.values()
        for predecessor in (values or [])
    }


@lru_cache(maxsize=1)
def _bundled_bp_schema() -> dict[str, Any]:
    schema_path = (
        Path(__file__).parents[1] / "templates" / "schemas" / "best-practice.yaml"
    )
    data = yaml.safe_load(schema_path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _repair_legacy_bp_status_map(
    root: Path, *, dry_run: bool,
) -> tuple[bool, bool, str | None]:
    """Repair only the migration-owned legacy BP lifecycle map, if present.

    Returns ``(would_repair, repaired, error)``. Other schema customizations are
    preserved; only the exact pre-collapse status map is replaced.
    """
    schema_path = root / ".specflow" / "schema" / "best-practice.yaml"
    if not schema_path.is_file():
        return False, False, None
    try:
        original = schema_path.read_text(encoding="utf-8")
        schema = yaml.safe_load(original) or {}
    except (OSError, yaml.YAMLError) as exc:
        return False, False, f"{schema_path.relative_to(root)}: {exc}"
    if not isinstance(schema, dict) or schema.get("type") != "best-practice":
        return False, False, None
    if schema.get("allowed_status") != _LEGACY_BP_STATUS_MAP:
        return False, False, None

    target_map = _bundled_bp_schema().get("allowed_status", {})
    if not isinstance(target_map, dict):
        return False, False, "bundled best-practice schema has no status map"
    try:
        document = yaml.compose(original)
    except yaml.YAMLError as exc:
        return False, False, f"{schema_path.relative_to(root)}: {exc}"
    if not isinstance(document, yaml.MappingNode):
        return (
            False,
            False,
            f"{schema_path.relative_to(root)}: schema root is not a mapping",
        )

    status_node = next(
        (
            (key_node, value_node)
            for key_node, value_node in document.value
            if isinstance(key_node, yaml.ScalarNode)
            and key_node.value == "allowed_status"
        ),
        None,
    )
    if status_node is None:
        return False, False, f"{schema_path.relative_to(root)}: allowed_status is missing"

    rendered_map = "allowed_status:\n"
    for status, predecessors in target_map.items():
        values = ", ".join(str(value) for value in (predecessors or []))
        rendered_map += (
            f"  {status}: [{values}]\n" if values else f"  {status}: []\n"
        )
    key_node, value_node = status_node
    repaired_text = (
        original[:key_node.start_mark.index]
        + rendered_map
        + original[value_node.end_mark.index:]
    )
    if not dry_run:
        try:
            schema_path.write_text(repaired_text, encoding="utf-8")
        except OSError as exc:
            return True, False, f"{schema_path.relative_to(root)}: {exc}"
    return True, not dry_run, None


def status_resolves_approved(status: str) -> bool:
    """Treat legacy ``active`` as approved through the transitional BP map."""
    if status == "approved":
        return True
    approved_predecessors = _bundled_bp_schema().get("allowed_status", {}).get("approved", [])
    return status == "active" and status in approved_predecessors


def tailoring_drop_problem(
    practice: art_lib.Artifact,
    id_index: dict[str, art_lib.Artifact],
) -> str | None:
    """Explain why a dropped-practice tailoring record is not authorized.

    A valid drop is explicit and auditable: it has a rationale and cites an
    existing approved DEC. Other tailoring statuses are not drop exemptions.
    """
    record = practice.frontmatter.get("tailoring")
    if record is None:
        return None
    if not isinstance(record, dict):
        return "tailoring must be a mapping with status, rationale, and dec"
    if record.get("status") != "dropped":
        return None
    if not str(record.get("rationale") or "").strip():
        return "dropped tailoring needs a non-empty rationale"
    dec_id = str(record.get("dec") or "").strip()
    decision = id_index.get(dec_id)
    if decision is None or decision.type != "decision":
        return f"dropped tailoring cites missing DEC '{dec_id or '(missing)'}'"
    if decision.status != "approved":
        return f"dropped tailoring DEC '{dec_id}' is '{decision.status}', not approved"
    return None


def is_tailoring_dropped(
    practice: art_lib.Artifact,
    id_index: dict[str, art_lib.Artifact],
) -> bool:
    """Return whether an approved DEC authorizes this BP's dropped status."""
    record = practice.frontmatter.get("tailoring")
    return (
        isinstance(record, dict)
        and record.get("status") == "dropped"
        and tailoring_drop_problem(practice, id_index) is None
    )


def applicability_matches(
    applicability: Any,
    artifact: art_lib.Artifact,
    root: Path | None = None,
) -> bool:
    """Evaluate a BP applicability predicate against artifact context.

    Mapping predicates support ``domains``, ``tags``, ``artifact_types``, and
    ``moments`` (matched against lifecycle_moment, phase, or status). Specified
    dimensions are conjunctive; values within a dimension are alternatives.
    ``always: true`` is the explicit universal predicate. A callable is
    supported for in-memory seed entries.
    """
    if callable(applicability):
        return bool(applicability(artifact))
    if not isinstance(applicability, dict) or not applicability:
        return False
    if applicability.get("always") is True:
        return True

    frontmatter = artifact.frontmatter
    artifact_tags = set(artifact.tags)
    domains = {str(value) for value in (frontmatter.get("domain"),) if value}
    domains.update(artifact_tags)
    if root is not None:
        from specflow.lib.config import get_domain

        project_domain, project_tags = get_domain(root)
        if project_domain:
            domains.add(project_domain)
        domains.update(project_tags)

    predicates: list[bool] = []
    if "domains" in applicability:
        values = _as_string_set(applicability.get("domains"))
        predicates.append(bool(values & domains))
    if "tags" in applicability:
        values = _as_string_set(applicability.get("tags"))
        predicates.append(bool(values & artifact_tags))
    if "artifact_types" in applicability:
        values = _as_string_set(applicability.get("artifact_types"))
        predicates.append(
            artifact.type in values or art_lib.get_prefix_from_id(artifact.id) in values
        )
    if "moments" in applicability:
        values = _as_string_set(applicability.get("moments"))
        current_moments = {
            str(frontmatter.get(key)) for key in ("lifecycle_moment", "phase", "status")
            if frontmatter.get(key)
        }
        predicates.append(bool(values & current_moments))
    recognized = {"always", "domains", "tags", "artifact_types", "moments"}
    if not predicates or set(applicability) - recognized:
        return False
    return all(predicates)


def _as_string_set(value: Any) -> set[str]:
    if isinstance(value, str):
        return {item.strip() for item in value.split(",") if item.strip()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return {str(item).strip() for item in value if item is not None and str(item).strip()}
    return set()


def load_active_best_practices(
    root: Path,
    artifact: art_lib.Artifact,
) -> list[art_lib.Artifact]:
    """Load applicable approved BPs; applicability precedes legacy tag fallback.

    The lifecycle check intentionally runs after applicability resolution. BPs
    with an ``applicability`` field use it as the authoritative predicate;
    only legacy BPs without that field fall back to applies_to links and tag
    intersection.
    """
    return applicable_best_practices(_load_best_practices(root), artifact, root)


def applicable_best_practices(
    practices: list[art_lib.Artifact],
    artifact: art_lib.Artifact,
    root: Path | None = None,
) -> list[art_lib.Artifact]:
    """Filter already-loaded BPs to those applicable and approved for ``artifact``.

    Pure counterpart of :func:`load_active_best_practices` so callers that
    evaluate many targets parse the practice files once. Semantics are
    identical: applicability predicate first, legacy applies_to/tag fallback
    for BPs without one, and approved status as the final filter.
    """
    artifact_tags = set(artifact.tags)
    applicable: list[art_lib.Artifact] = []
    for bp in practices:
        if "applicability" in bp.frontmatter:
            matched = applicability_matches(bp.frontmatter.get("applicability"), artifact, root)
        else:
            applies_to_ids = {link.target for link in bp.links if link.role == "applies_to"}
            matched = artifact.id in applies_to_ids or bool(artifact_tags & set(bp.tags))
        if matched:
            applicable.append(bp)

    # Status is deliberately the final filter, after predicate/tag matching.
    return [bp for bp in applicable if status_resolves_approved(bp.status)]


def _load_best_practices(root: Path) -> list[art_lib.Artifact]:
    """Parse every non-underscore BP file under ``_specflow/specs/best-practices``."""
    practices: list[art_lib.Artifact] = []
    for bp_file in _best_practice_files(root):
        bp = art_lib.parse_artifact(bp_file)
        if bp:
            practices.append(bp)
    return practices


def lifecycle_date(
    artifact: art_lib.Artifact,
    fields: tuple[str, ...] = ("created", "modified"),
) -> date | None:
    """Return the first parseable frontmatter date among ``fields``.

    Keyed on git-tracked frontmatter, never on filesystem mtime: git does not
    preserve mtimes, so a fresh clone stamps every file with checkout time and
    identical committed content would lint differently per environment.
    Accepts both quoted (``str``) and bare YAML dates (``date``/``datetime``);
    a bare ``created: 2026-04-10`` is a real date, not a missing one.
    """
    for field in fields:
        raw = artifact.frontmatter.get(field)
        if isinstance(raw, datetime):
            return raw.date()
        if isinstance(raw, date):
            return raw
        if not isinstance(raw, str) or not raw.strip():
            continue
        try:
            return date.fromisoformat(raw.strip()[:10])
        except ValueError:
            continue
    return None


BINDING_TARGET_TYPES: tuple[str, ...] = ("requirement", "architecture", "story")
EXEMPT_UNSTAMPED = "unstamped"
EXEMPT_GRACE = "grace"


def in_scope_bindings(
    root: Path,
    artifacts: list[art_lib.Artifact],
) -> list[tuple[art_lib.Artifact, art_lib.Artifact, bool, str | None]]:
    """Enumerate every applicable (target, practice) pair with its scope verdict.

    The single applicability predicate shared by ``artifact-lint``
    bp-application and ``brief`` Practice bindings, so both report the same
    counts. Each row is ``(target, bp, bound, exempt_reason)`` where ``bound``
    is whether ``target`` links ``bp`` via ``guided_by`` and ``exempt_reason``
    is ``None`` (in scope, accountable), :data:`EXEMPT_UNSTAMPED`, or
    :data:`EXEMPT_GRACE`. Targets are REQ/ARCH/STORY; practices are the
    approved BPs applicable to each target (:func:`applicable_best_practices`).

    Exclusions and exemptions, in order:

    * A BP whose dropped tailoring is authorized by an approved DEC is out of
      scope entirely and produces no rows (``is_tailoring_dropped``); a drop
      with a problem stays in scope — reporting the problem is the caller's job.
      This applies to stamped and unstamped BPs alike: an authorized drop is
      the strongest exclusion, so an unstamped-but-dropped BP yields no rows
      rather than ``unstamped`` exempt rows (lint is unaffected because it
      skips exempt rows; only brief's exempt tally sees the difference).
    * ``unstamped``: a BP without a provenance migration stamp. The stamp is
      the release boundary (DEC-089): legacy practices are never accounted.
    * ``grace``: backfill grace for a legacy target. Keyed on the target's
      ``created`` date (``modified`` only when ``created`` is absent) against
      the BP's latest ``modified``/``created`` date: a target that predates the
      practice is exempt. Deliberately NOT keyed on the target's ``modified``
      date — a body-only wording edit or a CLI frontmatter write bumps
      ``modified`` and would silently pull an old artifact into scope, firing
      one accounting line per applicable BP (cry-wolf). Re-binding a legacy
      artifact is an explicit act: a ``guided_by`` link. Hence a **bound**
      pair is never grace-exempt — the link is the author's declaration that
      the artifact was written against the practice, so it is counted and its
      verification evidence is checked. When either side has no parseable
      date the pair is in scope (conservative: accounting beats a silent skip).

      The horizon is asymmetric by design: the target side is fixed for life
      (``created``) while the BP side moves with ``modified``. Any CLI write
      to a BP (status, tags, a wording edit) therefore moves the grace horizon
      forward permanently for every unbound legacy target created before that
      write — those targets no longer re-enter scope when they are next
      edited. That is silent under-accounting, never a false alarm. Follow-up
      (v1.18): key the BP side on an approval or provenance-stamp date rather
      than ``modified`` so routine BP edits do not widen the grace window.
    """
    id_index = art_lib.build_id_index(artifacts)
    practices = [
        bp for bp in _load_best_practices(root)
        if not is_tailoring_dropped(bp, id_index)
    ]
    rows: list[tuple[art_lib.Artifact, art_lib.Artifact, bool, str | None]] = []
    for target in artifacts:
        if target.type not in BINDING_TARGET_TYPES:
            continue
        target_date = lifecycle_date(target, ("created", "modified"))
        for bp in applicable_best_practices(practices, target, root):
            bound = any(
                link.role == "guided_by" and link.target == bp.id
                for link in target.links
            )
            exempt: str | None = None
            if not bp.frontmatter.get("provenance"):
                exempt = EXEMPT_UNSTAMPED
            elif not bound:
                bp_date = lifecycle_date(bp, ("modified", "created"))
                if (
                    target_date is not None
                    and bp_date is not None
                    and target_date <= bp_date
                ):
                    exempt = EXEMPT_GRACE
            rows.append((target, bp, bound, exempt))
    return rows


def _best_practice_files(root: Path) -> list[Path]:
    bp_dir = root / "_specflow" / "specs" / "best-practices"
    if not bp_dir.is_dir():
        return []
    return sorted(path for path in bp_dir.glob("*.md") if not path.name.startswith("_"))


def _source_resolves(root: Path, source: str, artifacts: list[art_lib.Artifact]) -> bool:
    """Resolve a provenance source to a local artifact, seed, standard, or path."""
    source = source.strip()
    if not source:
        return False
    if source.startswith("seed:"):
        source = source[len("seed:"):]
    if source.startswith("SEED-"):
        from specflow.lib.practices_seed import get_seed_practices

        return source in {practice.seed_id for practice in get_seed_practices()}
    if source.startswith("artifact:"):
        source = source[len("artifact:"):]
    if any(artifact.id == source for artifact in artifacts):
        return True

    if source.startswith("path:"):
        source = source[len("path:"):]
    candidate = Path(source)
    if not candidate.is_absolute() and ".." not in candidate.parts:
        if (root / candidate).is_file():
            return True

    # Imported standard clauses are local YAML records; no network resolution.
    if source.startswith("standard:"):
        source = source[len("standard:"):]
    standards_dir = root / ".specflow" / "standards"
    if standards_dir.is_dir():
        for standard_file in sorted(standards_dir.glob("*.yaml")):
            try:
                data = yaml.safe_load(standard_file.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                continue
            for clause in data.get("clauses", []) if isinstance(data, dict) else []:
                if isinstance(clause, dict) and clause.get("id") == source:
                    return True
    return False


def validate_practices(root: Path) -> list[dict[str, str]]:
    """Return deterministic file-and-reason validation failures for all BPs."""
    files = _best_practice_files(root)
    artifacts = art_lib.discover_artifacts(root)
    by_id = {artifact.id: artifact for artifact in artifacts}
    best_practices: list[art_lib.Artifact] = []
    issues: list[dict[str, str]] = []

    def add(path: Path, reason: str) -> None:
        issues.append({"path": str(path.relative_to(root)), "reason": reason})

    for path in files:
        bp = art_lib.parse_artifact(path)
        if bp is None:
            add(path, "could not parse artifact frontmatter")
            continue
        best_practices.append(bp)
        provenance = bp.frontmatter.get("provenance")
        # DEC-089 legacy allowance: `practices migrate` stamps `synthesized`
        # provenance WITHOUT rewriting the authored body (_restore_original_body),
        # so a migrated legacy BP can never reach the five-section anatomy
        # retroactively. Five-part enforcement is the create/edit boundary for
        # post-migration records; failing migrated ones forever would make the
        # flagship repo red on its own check. Only the migration's own
        # `synthesized` marker is tolerated — authoring provenance (bundled /
        # standard / learned) still enforces the anatomy.
        legacy_anatomy = provenance == "synthesized"
        for problem in validate_anatomy(bp.body):
            if legacy_anatomy:
                continue
            add(path, problem)

        method = bp.frontmatter.get("verification_method")
        if method is not None and (
            not isinstance(method, str) or method not in VERIFICATION_METHODS
        ):
            add(
                path,
                f"verification_method '{method}' is not one of "
                f"{', '.join(sorted(VERIFICATION_METHODS))}",
            )

        if provenance is not None:
            if not isinstance(provenance, str) or provenance not in PROVENANCE_VALUES:
                add(
                    path,
                    f"provenance '{provenance}' is not one of "
                    f"{', '.join(sorted(PROVENANCE_VALUES))}",
                )
        source = bp.frontmatter.get("source")
        if provenance in ("bundled", "standard") and not source:
            add(path, f"provenance '{provenance}' requires a resolvable source")
        if source is not None:
            if not isinstance(source, str) or not _source_resolves(root, source, artifacts):
                add(path, f"source '{source}' does not resolve locally")

        strength = bp.frontmatter.get("strength")
        if strength is not None and (
            not isinstance(strength, str) or strength not in STRENGTH_VALUES
        ):
            add(
                path,
                f"strength '{strength}' is not one of "
                f"{', '.join(sorted(STRENGTH_VALUES))}",
            )

    superseders: dict[str, set[str]] = {}
    edges: dict[str, set[str]] = {}
    for bp in best_practices:
        targets: set[str] = set()
        for link in bp.links:
            if link.role != "supersedes":
                continue
            target = by_id.get(link.target)
            if target is None or target.type != "best-practice":
                add(
                    bp.path,
                    f"supersedes target '{link.target}' does not resolve to a best-practice",
                )
                continue
            if link.target == bp.id:
                add(bp.path, f"supersession lineage cannot self-reference '{bp.id}'")
                continue
            targets.add(link.target)
            superseders.setdefault(link.target, set()).add(bp.id)
        edges[bp.id] = targets

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(artifact_id: str) -> bool:
        if artifact_id in visiting:
            return True
        if artifact_id in visited:
            return False
        visiting.add(artifact_id)
        cyclic = any(visit(target) for target in sorted(edges.get(artifact_id, set())))
        visiting.remove(artifact_id)
        visited.add(artifact_id)
        return cyclic

    for bp in best_practices:
        if visit(bp.id):
            add(bp.path, "supersession lineage contains a cycle")
            break
        if bp.status == "superseded" and not superseders.get(bp.id):
            add(bp.path, "superseded best-practice has no successor lineage")
    return issues


def _migration_fields(bp: art_lib.Artifact) -> tuple[dict[str, Any], str | None]:
    from specflow.lib.practices_seed import get_seed_practices

    matching_seeds = [
        practice for practice in get_seed_practices() if practice.title == bp.title
    ]
    if len(matching_seeds) == 1:
        seed = matching_seeds[0]
        if _normalize_body_text(bp.body) == _normalize_body_text(seed.to_body()):
            fields: dict[str, Any] = {"provenance": "bundled"}
            if not bp.frontmatter.get("source"):
                fields["source"] = seed.seed_id
            return fields, None
        return (
            {"provenance": "synthesized"},
            f"title matches bundled seed '{seed.seed_id}' but body differs; "
            "provenance stamped synthesized",
        )
    if validate_anatomy(bp.body):
        return (
            {"provenance": "synthesized"},
            "legacy anatomy is incomplete; provenance stamped synthesized",
        )
    return {"provenance": "learned"}, None


def _normalize_body_text(body: str) -> str:
    return re.sub(r"\s+", " ", body or "").strip()


def _restore_original_body(path: Path, original: bytes) -> None:
    """Keep migration metadata edits from normalizing the authored BP body."""
    opening = original.find(b"---")
    if opening < 0:
        return
    original_separator = original.find(b"---", opening + 3)
    if original_separator < 0:
        return
    updated = path.read_bytes()
    updated_opening = updated.find(b"---")
    if updated_opening < 0:
        return
    updated_separator = updated.find(b"---", updated_opening + 3)
    if updated_separator < 0:
        return
    # Atomic, under the mutation lock (STORY-696): a crash leaves the whole
    # old or the whole new file.
    art_lib.write_artifact_text(
        art_lib._project_root_of(path) or path.parent, path,
        updated[:updated_separator + 3] + original[original_separator + 3:],
    )


def migrate_practices(root: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Stamp provenance on unstamped BPs; dry-run builds the same plan write-free."""
    plan: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []
    would_repair_status_map, status_map_repaired, map_error = (
        _repair_legacy_bp_status_map(root, dry_run=dry_run)
    )
    if map_error:
        errors.append(map_error)
    for path in _best_practice_files(root):
        bp = art_lib.parse_artifact(path)
        if bp is None:
            errors.append(f"{path.relative_to(root)}: could not parse artifact frontmatter")
            continue
        if bp.frontmatter.get("provenance"):
            continue
        fields, warning = _migration_fields(bp)
        plan.append({"id": bp.id, "path": str(path.relative_to(root)), "fields": fields})
        if warning:
            warnings.append(f"{path.relative_to(root)}: {warning}")

    stamped: list[str] = []
    if not dry_run:
        for item in plan:
            artifact_path = root / item["path"]
            original = artifact_path.read_bytes()
            result = art_lib.update_artifact(root, item["id"], **item["fields"])
            if result.get("ok"):
                stamped.append(item["id"])
                _restore_original_body(artifact_path, original)
            else:
                errors.append(f"{item['path']}: {result.get('error', 'update failed')}")
    return {
        "dry_run": dry_run,
        "would_stamp": plan,
        "stamped": stamped,
        "would_repair_status_map": would_repair_status_map,
        "status_map_repaired": status_map_repaired,
        "warnings": warnings,
        "errors": errors,
    }
