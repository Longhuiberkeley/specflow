"""Shared best-practice anatomy and applicability primitives."""

from __future__ import annotations

import re
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


def status_resolves_approved(status: str) -> bool:
    """Treat legacy ``active`` as approved through the transitional BP map."""
    if status == "approved":
        return True
    approved_predecessors = _bundled_bp_schema().get("allowed_status", {}).get("approved", [])
    return status == "active" and status in approved_predecessors


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
    bp_dir = root / "_specflow" / "specs" / "best-practices"
    if not bp_dir.is_dir():
        return []

    artifact_tags = set(artifact.tags)
    applicable: list[art_lib.Artifact] = []
    for bp_file in sorted(bp_dir.glob("*.md")):
        if bp_file.name.startswith("_"):
            continue
        bp = art_lib.parse_artifact(bp_file)
        if not bp:
            continue
        if "applicability" in bp.frontmatter:
            matched = applicability_matches(bp.frontmatter.get("applicability"), artifact, root)
        else:
            applies_to_ids = {link.target for link in bp.links if link.role == "applies_to"}
            matched = artifact.id in applies_to_ids or bool(artifact_tags & set(bp.tags))
        if matched:
            applicable.append(bp)

    # Status is deliberately the final filter, after predicate/tag matching.
    return [bp for bp in applicable if status_resolves_approved(bp.status)]


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
        for problem in validate_anatomy(bp.body):
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

        provenance = bp.frontmatter.get("provenance")
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
        fields: dict[str, Any] = {"provenance": "bundled"}
        if not bp.frontmatter.get("source"):
            fields["source"] = seed.seed_id
        return fields, None
    if validate_anatomy(bp.body):
        return (
            {"provenance": "synthesized"},
            "legacy anatomy is incomplete; provenance stamped synthesized",
        )
    return {"provenance": "learned"}, None


def migrate_practices(root: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Stamp provenance on unstamped BPs; dry-run builds the same plan write-free."""
    plan: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []
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
            result = art_lib.update_artifact(root, item["id"], **item["fields"])
            if result.get("ok"):
                stamped.append(item["id"])
            else:
                errors.append(f"{item['path']}: {result.get('error', 'update failed')}")
    return {
        "dry_run": dry_run,
        "would_stamp": plan,
        "stamped": stamped,
        "warnings": warnings,
        "errors": errors,
    }
